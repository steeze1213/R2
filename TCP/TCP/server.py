from __future__ import annotations

import asyncio
import random
import socket
import threading
import time
from collections import Counter
from dataclasses import dataclass
from typing import Dict, List, Optional, Set, Tuple


ANIMALS = ["토끼", "고양이", "사자", "강아지", "악어", "코끼리", "호랑이", "개미"]
JOBS = (["마피아"] * 2 + ["경찰"] * 1 + ["의사"] * 1 + ["기자"] * 1 + ["시민"] * 3)

MANUAL = (
    "메뉴얼:\n"
    "  /help                도움말\n"
    "  /vote 닉             (낮 투표)\n"
    "  /kill 닉             (마피아) 살인 대상(밤)\n"
    "  /heal 닉             (의사) 살릴 대상(밤)\n"
    "  /check 닉            (경찰) 조사(밤) -> 즉시 본인에게만 직업 공개\n"
    "  /peek 닉             (기자) 2번째 밤부터 조사(다음날 아침 전체 공개)\n"
    "  /m 메시지            (마피아) 밤 전용 채팅\n"
    "  exit                 종료\n"
    "\n"
)


@dataclass(frozen=True)
class ServerConfig:
    host: str = "0.0.0.0"
    port: int = 50007
    backlog: int = 50
    buf: int = 1024
    encoding: str = "utf-8"

    capacity: int = 8
    start_delay: int = 5

    day_chat: int = 40
    day_chat_warn_after: int = 30  # 30초 경과(=남은 10초)에 투표 예고

    day_vote: int = 30
    vote_warn_remaining: int = 10  # 마감 10초 전 공지
    revote: int = 20              # 동점 시 재투표 1회

    night: int = 30

    monitor_interval: float = 0.5  # 모니터링 루프 주기


class GlobalState:
    """
    전역 공유상태는 state 하나로 묶고, 수정은 lock 안에서만.
    """

    def __init__(self, capacity: int):
        self.lock = threading.RLock()

        # 서버/게임 상태
        self.capacity = capacity
        self.started = False
        self.phase = "lobby"   # lobby/day_chat/day_vote/night/ended
        self.night_count = 0
        self.shutdown = False

        # 세션/플레이어 정보
        self.conn_by_nick: Dict[str, socket.socket] = {}
        self.nick_by_conn: Dict[socket.socket, str] = {}

        # 설계 요구 딕셔너리
        self.ip_by_nick: Dict[str, str] = {}                 # {닉네임: IP}
        self.ips_by_job: Dict[str, Set[str]] = {}            # {직업: {IP...}}  (내부용)
        self.job_by_nick: Dict[str, str] = {}                # {닉네임: 직업}   (내부용)
        self.alive: Set[str] = set()                          # 생존 닉네임

        # 투표
        self.vote_token: Dict[str, bool] = {}
        self.day_votes: Dict[str, str] = {}

        # 밤 행동(다수결 반영)
        self.night_kill_votes: Dict[str, str] = {}           # {mafia_nick: target}
        self.night_heal: Dict[str, str] = {}                 # {doctor_nick: target}

        # 기자: 밤에 타겟 예약 -> 다음날 아침 전체 공개
        self.reporter_peek_target: Optional[str] = None
        self.pending_report_reveal: Optional[str] = None     # "다음날 아침 공개 문구"

    def player_count(self) -> int:
        return len(self.conn_by_nick)

    def alive_list(self) -> List[str]:
        return sorted(self.alive)


class SessionHub:
    """
    sendall은 lock 밖에서.
    socket 목록은 state.lock으로 스냅샷만 잡고, 실제 send는 lock 밖에서 실행.
    """

    def __init__(self, state: GlobalState, cfg: ServerConfig):
        self.state = state
        self.cfg = cfg

    def _safe_send(self, conn: socket.socket, text: str) -> None:
        try:
            conn.sendall(text.encode(self.cfg.encoding))
        except OSError:
            pass

    def send_to(self, nick: str, text: str) -> None:
        with self.state.lock:
            conn = self.state.conn_by_nick.get(nick)
        if conn:
            self._safe_send(conn, text)

    def broadcast(self, text: str) -> None:
        with self.state.lock:
            conns = list(self.state.nick_by_conn.keys())
        for c in conns:
            self._safe_send(c, text)

    def mafia_broadcast(self, text: str) -> None:
        with self.state.lock:
            mafia_nicks = [n for n in self.state.alive if self.state.job_by_nick.get(n) == "마피아"]
            conns = [self.state.conn_by_nick.get(n) for n in mafia_nicks]
        for c in conns:
            if c:
                self._safe_send(c, text)

    def close_all_clients(self) -> None:
        with self.state.lock:
            conns = list(self.state.nick_by_conn.keys())
        for c in conns:
            try:
                c.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            try:
                c.close()
            except OSError:
                pass


class AsyncLoopThread:
    """
    asyncio loop를 별도 스레드에서 구동.
    - 엔진 코루틴
    - 모니터링 코루틴
    """

    def __init__(self):
        self.loop = asyncio.new_event_loop()
        self.thread = threading.Thread(target=self._run, daemon=True)

    def _run(self):
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()

    def start(self):
        self.thread.start()

    def create_task(self, coro):
        self.loop.call_soon_threadsafe(lambda: asyncio.create_task(coro))


class MafiaEngine:
    """
    타이머/페이즈 전환은 코루틴 1개에서만 수행.
    """

    def __init__(self, cfg: ServerConfig, state: GlobalState, hub: SessionHub, server_shutdown_cb):
        self.cfg = cfg
        self.state = state
        self.hub = hub
        self._rng = random.Random()
        self._started_once = False
        self._shutdown_cb = server_shutdown_cb

    def start_once(self, async_thread: AsyncLoopThread):
        if self._started_once:
            return
        self._started_once = True
        async_thread.create_task(self.run())

    async def run(self):
        self.hub.broadcast(f"[시스템] 정원 충족. {self.cfg.start_delay}초 뒤 게임 시작.\n")
        await asyncio.sleep(self.cfg.start_delay)

        with self.state.lock:
            # 시작 시점에 인원이 부족해졌으면(이탈) 시작 취소
            if self.state.player_count() < self.state.capacity:
                self._started_once = False
                self.hub.broadcast("[시스템] 인원 부족으로 게임 시작이 취소되었습니다. 다시 8명 모이면 시작합니다.\n")
                return

            self.state.started = True
            self.state.phase = "day_chat"

        self.hub.broadcast("[시스템] 게임 시작!\n")
        self._send_private_jobs()

        while True:
            winner = self._check_winner()
            if winner:
                with self.state.lock:
                    self.state.phase = "ended"
                self.hub.broadcast(f"[게임 종료] 승리: {winner}\n")
                self._shutdown_cb()
                return

            # 밤에 기자 공개가 예약되어 있으면 “아침(낮 시작)”에 먼저 공개
            self._broadcast_pending_report_if_any()

            await self._day_chat()
            if self._check_winner():
                continue

            eliminated = await self._day_vote()
            if eliminated:
                self.hub.broadcast(f"[결과] 낮 투표로 {eliminated} 탈락\n")
            else:
                self.hub.broadcast("[결과] 낮 투표 패스(처형 없음)\n")

            if self._check_winner():
                continue

            killed, saved = await self._night()
            if saved:
                self.hub.broadcast(f"[결과] 의사가 {saved}를 살렸습니다.\n")
            if killed:
                self.hub.broadcast(f"[결과] 밤에 {killed} 사망\n")
            if not killed and not saved:
                self.hub.broadcast("[결과] 밤 사망자 없음\n")

    def _send_private_jobs(self):
        with self.state.lock:
            items = list(self.state.job_by_nick.items())
        for nick, job in items:
            self.hub.send_to(nick, f"[개인] 당신의 직업은 {job} 입니다.\n")

    def _broadcast_pending_report_if_any(self) -> None:
        with self.state.lock:
            msg = self.state.pending_report_reveal
            self.state.pending_report_reveal = None
        if msg:
            self.hub.broadcast(msg)

    async def _day_chat(self):
        with self.state.lock:
            self.state.phase = "day_chat"
        self.hub.broadcast(f"[페이즈] 낮 채팅 시작 ({self.cfg.day_chat}초)\n")

        start = time.time()
        warned = False
        while time.time() - start < self.cfg.day_chat:
            if self._should_stop():
                return
            if not warned and (time.time() - start) >= self.cfg.day_chat_warn_after:
                self.hub.broadcast("[시스템] 10초 뒤 투표 시간입니다.\n")
                warned = True
            await asyncio.sleep(0.2)

    async def _day_vote(self) -> Optional[str]:
        with self.state.lock:
            self.state.phase = "day_vote"
            self.state.day_votes.clear()
            self.state.vote_token = {n: True for n in self.state.alive}

            alive = ", ".join(self.state.alive_list())

        self.hub.broadcast(f"[페이즈] 낮 투표 시작 ({self.cfg.day_vote}초) /vote 닉\n")
        self.hub.broadcast(f"[생존자] {alive}\n")

        start = time.time()
        warned = False
        while time.time() - start < self.cfg.day_vote:
            if self._should_stop():
                return None
            remaining = self.cfg.day_vote - (time.time() - start)
            if not warned and remaining <= self.cfg.vote_warn_remaining:
                self.hub.broadcast("[시스템] 투표 마감 10초 전입니다.\n")
                warned = True
            await asyncio.sleep(0.2)

        tied = self._tally_top()
        if not tied:
            return None

        if len(tied) == 1:
            target = tied[0]
            with self.state.lock:
                self.state.alive.discard(target)
            return target

        # 재투표 1회
        self.hub.broadcast(f"[시스템] 동점 발생: {', '.join(tied)} (재투표 1회)\n")
        with self.state.lock:
            self.state.day_votes.clear()
            self.state.vote_token = {n: True for n in self.state.alive}

        start2 = time.time()
        warned2 = False
        while time.time() - start2 < self.cfg.revote:
            if self._should_stop():
                return None
            remaining = self.cfg.revote - (time.time() - start2)
            if not warned2 and remaining <= self.cfg.vote_warn_remaining:
                self.hub.broadcast("[시스템] 재투표 마감 10초 전입니다.\n")
                warned2 = True
            await asyncio.sleep(0.2)

        tied2 = self._tally_top(allow_only=set(tied))
        if not tied2:
            return None

        target = tied2[0] if len(tied2) == 1 else self._rng.choice(tied2)
        if len(tied2) > 1:
            self.hub.broadcast(f"[시스템] 재투표도 동점 -> 랜덤 처형: {target}\n")
        with self.state.lock:
            self.state.alive.discard(target)
        return target

    def _tally_top(self, allow_only: Optional[Set[str]] = None) -> List[str]:
        with self.state.lock:
            counts = Counter()
            for voter, target in self.state.day_votes.items():
                if voter not in self.state.alive:
                    continue
                if target not in self.state.alive:
                    continue
                if allow_only is not None and target not in allow_only:
                    continue
                counts[target] += 1

        if not counts:
            return []
        top = counts.most_common()
        best = top[0][1]
        return [n for n, c in top if c == best]

    async def _night(self) -> Tuple[Optional[str], Optional[str]]:
        with self.state.lock:
            self.state.phase = "night"
            self.state.night_count += 1
            self.state.night_kill_votes.clear()
            self.state.night_heal.clear()
            self.state.reporter_peek_target = None

            night_no = self.state.night_count
            alive = ", ".join(self.state.alive_list())

        self.hub.broadcast(f"[페이즈] 밤 {night_no} 시작 ({self.cfg.night}초)\n")
        self.hub.broadcast(f"[생존자] {alive}\n")
        self.hub.broadcast("[시스템] 마피아:/kill, 의사:/heal, 경찰:/check, 기자(2번째 밤부터):/peek, 마피아채팅:/m\n")

        start = time.time()
        while time.time() - start < self.cfg.night:
            if self._should_stop():
                return None, None
            await asyncio.sleep(0.2)

        killed, saved = self._resolve_night()

        # 기자 결과는 “다음날 아침” 전체공개로 예약 (기자가 죽어도 공개됨)
        with self.state.lock:
            target = self.state.reporter_peek_target
            if target:
                role = self.state.job_by_nick.get(target, "알수없음")
                self.state.pending_report_reveal = f"[특보] 기자 조사 결과: {target}의 직업은 {role} 입니다.\n"
                self.state.reporter_peek_target = None

        return killed, saved

    def _resolve_night(self) -> Tuple[Optional[str], Optional[str]]:
        with self.state.lock:
            kill_choices = list(self.state.night_kill_votes.values())
            heal_choices = list(self.state.night_heal.values())

            kill_target = self._pick_majority_or_random(kill_choices)
            heal_target = self._pick_majority_or_random(heal_choices)

            if not kill_target:
                return None, None
            if heal_target and heal_target == kill_target:
                return None, heal_target

            self.state.alive.discard(kill_target)
            return kill_target, None

    def _pick_majority_or_random(self, choices: List[str]) -> Optional[str]:
        if not choices:
            return None
        c = Counter(choices)
        top = c.most_common()
        best = top[0][1]
        tied = [n for n, cnt in top if cnt == best]
        return tied[0] if len(tied) == 1 else self._rng.choice(tied)

    def _check_winner(self) -> Optional[str]:
        with self.state.lock:
            alive = set(self.state.alive)
            mafia = {n for n in alive if self.state.job_by_nick.get(n) == "마피아"}
            citizens = alive - mafia

            if self.state.job_by_nick and not mafia:
                return "시민"
            if mafia and len(mafia) >= len(citizens):
                return "마피아"
            return None

    def _should_stop(self) -> bool:
        with self.state.lock:
            return self.state.shutdown or self.state.phase == "ended"


class MafiaServer:
    def __init__(self, cfg: ServerConfig):
        self.cfg = cfg
        self.state = GlobalState(cfg.capacity)
        self.hub = SessionHub(self.state, cfg)

        self.nick_pool = ANIMALS[:]
        self.job_pool = JOBS[:]
        random.shuffle(self.nick_pool)
        random.shuffle(self.job_pool)

        self.server_sock: Optional[socket.socket] = None
        self.stop_event = threading.Event()

        self.async_thread = AsyncLoopThread()
        self.engine = MafiaEngine(cfg, self.state, self.hub, server_shutdown_cb=self.shutdown)

        self.monitor_started = False

    def shutdown(self) -> None:
        """
        - shutdown 플래그 set
        - 모든 conn close
        - accept 루프 종료(서버 소켓 close)
        """
        if self.stop_event.is_set():
            return

        self.stop_event.set()
        with self.state.lock:
            self.state.shutdown = True

        # 클라 종료
        self.hub.close_all_clients()

        # 서버 소켓 close
        if self.server_sock is not None:
            try:
                self.server_sock.close()
            except OSError:
                pass

    def serve_forever(self) -> None:
        self.async_thread.start()
        # 모니터링 루프는 서버 시작과 동시에 1회만 시작
        if not self.monitor_started:
            self.monitor_started = True
            self.async_thread.create_task(self.monitor_loop())

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
            self.server_sock = server
            server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server.bind((self.cfg.host, self.cfg.port))
            server.listen(self.cfg.backlog)
            server.settimeout(1.0)
            print(f"서버 실행: {self.cfg.host}:{self.cfg.port}")

            while not self.stop_event.is_set():
                try:
                    conn, addr = server.accept()
                except socket.timeout:
                    continue
                except OSError:
                    break

                threading.Thread(target=self.handle_client, args=(conn, addr), daemon=True).start()

            self.shutdown()

    async def monitor_loop(self) -> None:
        """
        설계 요구: 별도 비동기 루프(async while True)로
        - 클라 수
        - 이탈자
        - 종료 조건
        등을 지속 체크하며 상태 동기화.
        """
        while not self.stop_event.is_set():
            await asyncio.sleep(self.cfg.monitor_interval)

            with self.state.lock:
                count = self.state.player_count()
                started = self.state.started
                phase = self.state.phase
                shutdown = self.state.shutdown

            if shutdown:
                return

            # lobby 상태에서 인원이 8명이 되면(그리고 게임이 시작 안 됐으면) 엔진 시작
            if (not started) and phase == "lobby" and count >= self.cfg.capacity:
                self.engine.start_once(self.async_thread)

            # started인데 접속자가 너무 줄어도(이탈) 게임은 계속 진행(이미 alive에서 제거되므로 승리 판정 안정)
            # ended는 엔진이 처리

    def _register_player(self, conn: socket.socket, addr: Tuple[str, int]) -> Optional[str]:
        with self.state.lock:
            if self.state.player_count() >= self.state.capacity or not self.nick_pool:
                return None

            nick = self.nick_pool.pop()
            job = self.job_pool.pop()
            ip = addr[0]

            self.state.conn_by_nick[nick] = conn
            self.state.nick_by_conn[conn] = nick

            self.state.ip_by_nick[nick] = ip
            self.state.job_by_nick[nick] = job
            self.state.alive.add(nick)

            self.state.ips_by_job.setdefault(job, set()).add(ip)

            return nick

    def _unregister_player_dead(self, conn: socket.socket, nick: str) -> None:
        """
        설계 요구: 이탈자 발생 시 즉시 사망 처리 + 승리 판정 안정화
        - alive에서 제거(죽음 처리)
        - 세션/conn 매핑 제거
        - (직업/닉/IP 기록은 남겨도 되지만, 여기선 최소한 ips_by_job 정리까지 수행)
        """
        with self.state.lock:
            self.state.alive.discard(nick)

            job = self.state.job_by_nick.get(nick)
            ip = self.state.ip_by_nick.get(nick)

            self.state.conn_by_nick.pop(nick, None)
            self.state.nick_by_conn.pop(conn, None)

            if job and ip:
                s = self.state.ips_by_job.get(job)
                if s:
                    s.discard(ip)

    def handle_client(self, conn: socket.socket, addr: Tuple[str, int]) -> None:
        nick: Optional[str] = None
        try:
            # 접속 즉시 등록(클라이언트 입력 트리거 필요 없음)
            nick = self._register_player(conn, addr)
            if nick is None:
                try:
                    conn.sendall("정원(8명) 초과\n".encode(self.cfg.encoding))
                except OSError:
                    pass
                return

            # 안내는 즉시 push(클라가 recv thread면 자동으로 보임)
            with self.state.lock:
                ip = self.state.ip_by_nick.get(nick, addr[0])
            self.hub.send_to(nick, MANUAL)
            self.hub.send_to(nick, f"[시스템] 당신의 닉네임: {nick} / IP: {ip}\n")
            self.hub.broadcast(f"[입장] {nick} ({addr[0]})\n")

            # lobby 상태 유지
            with self.state.lock:
                if not self.state.started and self.state.phase == "lobby":
                    self.hub.broadcast(f"[대기실] 현재 인원: {self.state.player_count()}/{self.state.capacity}\n")

            while not self.stop_event.is_set():
                data = conn.recv(self.cfg.buf)
                if not data:
                    return

                msg = data.decode(self.cfg.encoding, errors="replace").strip()
                if not msg:
                    continue

                if msg == "exit":
                    self.hub.send_to(nick, "bye\n")
                    return

                if msg == "/help":
                    self.hub.send_to(nick, MANUAL)
                    continue

                with self.state.lock:
                    phase = self.state.phase
                    my_job = self.state.job_by_nick.get(nick)
                    alive = (nick in self.state.alive)
                    night_no = self.state.night_count
                    alive_set = set(self.state.alive)

                # 죽은 사람 제한 강화
                if not alive:
                    self.hub.send_to(nick, "당신은 사망했습니다. 관전만 가능합니다.\n")
                    continue

                # ====== 낮 채팅 ======
                if phase == "day_chat" and not msg.startswith("/"):
                    # 설계: IP-닉 매칭도 가능. 여기서는 (닉/IP) 형태로 송출.
                    with self.state.lock:
                        ip = self.state.ip_by_nick.get(nick, "?")
                    self.hub.broadcast(f"{nick}({ip}): {msg}\n")
                    continue

                # ====== 낮 투표 ======
                if msg.startswith("/vote "):
                    if phase != "day_vote":
                        self.hub.send_to(nick, "지금은 투표 시간이 아닙니다.\n")
                        continue

                    target = msg.replace("/vote", "", 1).strip()
                    with self.state.lock:
                        if target not in self.state.alive:
                            self.hub.send_to(nick, "대상이 생존자가 아닙니다.\n")
                            continue
                        if not self.state.vote_token.get(nick, False):
                            self.hub.send_to(nick, "이미 투표했습니다.\n")
                            continue
                        self.state.day_votes[nick] = target
                        self.state.vote_token[nick] = False

                    self.hub.send_to(nick, f"투표 완료: {target}\n")
                    continue

                # 밤 전용 명령이 아닌데 밤/투표/로비 등 페이즈에 맞지 않으면 안내
                if phase != "night":
                    self.hub.send_to(nick, "명령을 확인하세요. /help\n")
                    continue

                # ====== 밤 단계 ======
                if my_job == "시민":
                    self.hub.send_to(nick, "시민은 밤에 행동이 없습니다.\n")
                    continue

                # 마피아 채팅
                if msg.startswith("/m "):
                    if my_job != "마피아":
                        self.hub.send_to(nick, "마피아만 사용할 수 있습니다.\n")
                        continue
                    text = msg.replace("/m", "", 1).strip()
                    if text:
                        self.hub.mafia_broadcast(f"[마피아] {nick}: {text}\n")
                    continue

                # 마피아 kill(다수결 반영)
                if msg.startswith("/kill "):
                    if my_job != "마피아":
                        self.hub.send_to(nick, "마피아만 가능합니다.\n")
                        continue
                    target = msg.replace("/kill", "", 1).strip()
                    with self.state.lock:
                        if target not in self.state.alive:
                            self.hub.send_to(nick, "대상이 생존자가 아닙니다.\n")
                            continue
                        self.state.night_kill_votes[nick] = target
                    self.hub.send_to(nick, f"살인 투표 등록: {target}\n")
                    continue

                # 의사 heal
                if msg.startswith("/heal "):
                    if my_job != "의사":
                        self.hub.send_to(nick, "의사만 가능합니다.\n")
                        continue
                    target = msg.replace("/heal", "", 1).strip()
                    with self.state.lock:
                        if target not in self.state.alive:
                            self.hub.send_to(nick, "대상이 생존자가 아닙니다.\n")
                            continue
                        self.state.night_heal[nick] = target
                    self.hub.send_to(nick, f"치료 대상 지정: {target}\n")
                    continue

                # 경찰 check: 즉시 경찰에게만 대상 직업 공개
                if msg.startswith("/check "):
                    if my_job != "경찰":
                        self.hub.send_to(nick, "경찰만 가능합니다.\n")
                        continue
                    target = msg.replace("/check", "", 1).strip()
                    with self.state.lock:
                        if target not in self.state.alive:
                            self.hub.send_to(nick, "대상이 생존자가 아닙니다.\n")
                            continue
                        role = self.state.job_by_nick.get(target, "알수없음")
                    self.hub.send_to(nick, f"[개인] 조사 결과: {target}의 직업은 {role} 입니다.\n")
                    continue

                # 기자 peek: 2번째 밤부터 가능, 다음날 아침 전체공개(기자가 죽어도 공개)
                if msg.startswith("/peek "):
                    if my_job != "기자":
                        self.hub.send_to(nick, "기자만 가능합니다.\n")
                        continue
                    if night_no < 2:
                        self.hub.send_to(nick, "기자는 2번째 밤부터 조사 가능합니다.\n")
                        continue
                    target = msg.replace("/peek", "", 1).strip()
                    with self.state.lock:
                        if target not in self.state.alive:
                            self.hub.send_to(nick, "대상이 생존자가 아닙니다.\n")
                            continue
                        self.state.reporter_peek_target = target
                    self.hub.send_to(nick, f"기자 조사 예약 완료: {target} (다음날 아침 전체 공개)\n")
                    continue

                self.hub.send_to(nick, "명령을 확인하세요. /help\n")

        except (ConnectionResetError, BrokenPipeError, OSError):
            return
        finally:
            if nick is not None:
                # 이탈자는 즉시 사망 처리 + 매핑 제거
                self._unregister_player_dead(conn, nick)
                self.hub.broadcast(f"[퇴장] {nick} (이탈로 사망 처리)\n")

            try:
                conn.close()
            except OSError:
                pass


def main():
    MafiaServer(ServerConfig()).serve_forever()


if __name__ == "__main__":
    main()