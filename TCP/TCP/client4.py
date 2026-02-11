from __future__ import annotations

import socket
import threading


HOST = "192.168.0.204"
PORT = 50007
ENCODING = "utf-8"


def recv_loop(sock: socket.socket, stop: threading.Event) -> None:
    try:
        while not stop.is_set():
            data = sock.recv(4096)
            if not data:
                print("Server: (연결 종료)")
                stop.set()
                return
            msg = data.decode(ENCODING, errors="replace")
            print(msg, end="" if msg.endswith("\n") else "\n")
    except OSError:
        stop.set()


def main() -> None:
    stop = threading.Event()

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((HOST, PORT))
            print("종료: exit")

            t = threading.Thread(target=recv_loop, args=(s, stop), daemon=True)
            t.start()

            while not stop.is_set():
                try:
                    message = input("Client: ").strip()
                except (EOFError, KeyboardInterrupt):
                    message = "exit"

                if not message:
                    continue

                try:
                    s.sendall(message.encode(ENCODING))
                except OSError:
                    print("Server: (전송 실패/연결 종료)")
                    stop.set()
                    break

                if message == "exit":
                    stop.set()
                    break

    except ConnectionRefusedError:
        print("Server: 접속 실패(서버가 꺼져있거나 주소/포트가 틀림)")
    except OSError as e:
        print(f"Server: 네트워크 오류({e})")


if __name__ == "__main__":
    main()