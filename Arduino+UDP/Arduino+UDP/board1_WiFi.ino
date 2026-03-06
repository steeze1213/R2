/*  BOARD 1 — 사물 인식 모듈 (WiFi 버전)
 *  Arduino Uno R3 + ESP8266 (AT 펌웨어)
 *
 * ─────────────────────────────────────────────────────
 *  핀 배치
 * ─────────────────────────────────────────────────────
 *  HC-SR04 전방   TRIG=A0  ECHO=A1
 *  HC-SR04 후방   TRIG=A2  ECHO=A3
 *  HC-SR04 좌측   TRIG=2   ECHO=4
 *  HC-SR04 우측   TRIG=7   ECHO=8
 *
 *  RGB LED R      D11  (PWM~)
 *  RGB LED G      D10  (PWM~)
 *  RGB LED B      D6   (PWM~)
 *  RGB LED GND    GND
 *
 *  ESP8266 TX     D3   (SoftSerial RX ← ESP8266 TXD)
 *  ESP8266 RX     D5   (SoftSerial TX → ESP8266 RXD)=
 *  ESP8266 VCC    3.3V
 *  ESP8266 GND    GND
 *  ESP8266 CH_PD  3.3V
 *  ESP8266 RST    3.3V (또는 미연결)
 *
 * ─────────────────────────────────────────────────────
 *  동작
 *  - 4방향 거리 100ms마다 측정
 *  - RGB LED : 최솟값 기준 색상+밝기 변화
 *      < 10cm  : 빨강 깜빡임 (DANGER)
 *      10~30cm : 주황        (CLOSE)
 *      30~60cm : 파랑 dim    (MID)
 *      >  60cm : 초록 희미  (SAFE)
 *  - 500ms마다 (또는 등급 변화 시 즉시) UDP로 전송
 *    형식: B1,F:23,B:45,L:12,R:67,MIN:12,LV:CLOSE
 *
 *  전송 방식: UDP (목적지 IP: DEST_IP, 포트: DEST_PORT)
 *  라이브러리: SoftwareSerial (내장)
 * ─────────────────────────────────────────────────────
 */

#include <SoftwareSerial.h>

// ── WiFi 설정 ──────────────────────────────────────────
const char* WIFI_SSID = "3F_302"; // ESP8266이 접속할 WiFi 정보
const char* WIFI_PASS = "0424719222!!";
const char* DEST_IP   = "192.168.0.204";        // UDP 목적지 (Python이 실행 중인 PC의 IPv4 주소)
const int   DEST_PORT = 5000;                  // UDP 수신 포트(Python에서 bind한 포트와 동일해야 함)
// 윈도우 방화벽 -> 고급 설정 -> 인바운드 규칙(새규칙) -> 포트 -> UDP -> 5000 -> 연결 허용 -> 모든 프로필 허용
// 제어판에서 윈도우 방화벽 끄기

// ── 핀 정의 ───────────────────────────────────────────
// 4방향 초음파 센서 TRIG / ECHO 핀 배열
// 인덱스 0=Front, 1=Back, 2=Left, 3=Right
const int TRIG[4]      = {A0, A2,  2,  7};
const int ECHO[4]      = {A1, A3,  4,  8};

// 방향 표시용 문자열 배열
const char* DIR[4]     = {"F", "B", "L", "R"};

// RGB LED 핀 (PWM 출력 가능 핀)
const int RGB_R = 11;
const int RGB_G = 10;
const int RGB_B =  6;

// ESP8266 SoftwareSerial (RX, TX)
// D3 <- ESP TX
// D5 -> ESP RX
SoftwareSerial espSerial(3, 5);

// ── 거리 임계값 정의 (단위: cm) ─────────────────────────
const float D_DANGER = 10.0;   // 10cm 미만 -> 위험
const float D_CLOSE  = 30.0;   // 10~30cm -> 근접
const float D_MID    = 60.0;   // 30~60cm -> 중간

// ── 위험 등급 열거형(enum) ──────────────────────────────
enum Level {
  SAFE,        // 안전
  MID_LV,      // 중간
  CLOSE_LV,    // 근접
  DANGER_LV    // 위험
};

Level currentLevel = SAFE;   // 현재 등급 저장

// ── 전역 변수 ──────────────────────────────────────────
float dist[4]         = {999, 999, 999, 999}; // 각 방향 거리 저장 배열
unsigned long lastSend = 0; // UDP 전송 주기 관리용
const unsigned long SEND_MS = 500; // 500ms마다 전송
bool wifiReady = false; // WiFi 연결 성공 여부

// ── 함수 선언 ──────────────────────────────────────────
float      measureDist(int trig, int echo); // 거리 측정
Level      classify(float d); // 거리 -> 등급
void       setRGB(int r, int g, int b); // RGB 직접 설정
void       updateRGB(float d); // 거리 기반 RGB 제어
void       sendUDP(float minD, Level lv); // UDP 전송
const char* lvStr(Level lv); // enum -> 문자열

// ESP8266 AT 명령 관련
bool       atCmd(const char* cmd, const char* expect, unsigned long timeout = 3000);
void       espFlush();
bool       wifiInit();
bool       udpSend(const char* data);

// ══════════════════════════════════════════════════════
void setup() {
  // USB 시리얼 모니터용
  Serial.begin(9600);
  // ESP8266 통신용 시리얼
  espSerial.begin(9600);

  // 초음파 핀 설정
  for (int i = 0; i < 4; i++) {
    pinMode(TRIG[i], OUTPUT);
    pinMode(ECHO[i], INPUT);
  }

  // RGB 핀 설정
  pinMode(RGB_R, OUTPUT);
  pinMode(RGB_G, OUTPUT);
  pinMode(RGB_B, OUTPUT);

  // 시작 점등 확인 (R->G->B)
  setRGB(255, 0, 0); delay(300);
  setRGB(0, 255, 0); delay(300);
  setRGB(0, 0, 255); delay(300);
  setRGB(0, 0, 0);

  Serial.println("[BOARD1] Setup start");

  // WiFi 초기화
  wifiReady = wifiInit();

  if (wifiReady) {
    Serial.println("[WiFi] Connected!");
    setRGB(0, 50, 0);   // 초록 — 연결 성공 표시
    delay(500);
    setRGB(0, 0, 0);
  } else {
    Serial.println("[WiFi] FAILED — check wiring/SSID/PW");
    // 빨강 천천히 점멸 -> 연결 실패 표시
    for (int i = 0; i < 5; i++) {
      setRGB(200, 0, 0); delay(400);
      setRGB(0, 0, 0);   delay(400);
    }
  }

  Serial.println("[BOARD1] Ready");
}

// ══════════════════════════════════════════════════════
void loop() {
  unsigned long now = millis();

  // 4방향 거리 측정
  for (int i = 0; i < 4; i++) {
    dist[i] = measureDist(TRIG[i], ECHO[i]);
  }

  // 최솟 거리 계산
  float minD = dist[0];
  for (int i = 1; i < 4; i++) {
    if (dist[i] < minD) minD = dist[i];
  }

  // 등급 판별
  Level prev  = currentLevel;
  currentLevel = classify(minD);

  // RGB 업데이트
  updateRGB(minD);

  // 등급 변화 시 즉시 전송
  if (currentLevel != prev) {
    sendUDP(minD, currentLevel);
    lastSend = now;
  }

  // 정기 전송 500ms
  if (now - lastSend >= SEND_MS) {
    lastSend = now;
    sendUDP(minD, currentLevel);
  }

  // 시리얼 디버그
  for (int i = 0; i < 4; i++) {
    Serial.print(DIR[i]); Serial.print(":"); Serial.print((int)dist[i]); Serial.print(" ");
  }
  Serial.print("LV:"); Serial.println(lvStr(currentLevel));

  delay(100);
}

// ══════════════════════════════════════════════════════
//  초음파 거리 측정 (cm)
float measureDist(int trig, int echo) {
  // 트리거 신호 생성
  digitalWrite(trig, LOW);
  delayMicroseconds(2);
  digitalWrite(trig, HIGH);
  delayMicroseconds(10);
  digitalWrite(trig, LOW);

  //echo가 HIGH인 시간 측정
  long dur = pulseIn(echo, HIGH, 30000UL);
  if (dur == 0) return 999.0;
  // 음속 0.034cm/us 이용
  return dur * 0.034f / 2.0f;
}

// ── 거리 -> 등급 ────────────────────────────────────────
Level classify(float d) {
  if (d < D_DANGER) return DANGER_LV;
  if (d < D_CLOSE)  return CLOSE_LV;
  if (d < D_MID)    return MID_LV;
  return SAFE;
}

// ── RGB 직접 출력 ──────────────────────────────────────
void setRGB(int r, int g, int b) {
  analogWrite(RGB_R, r);
  analogWrite(RGB_G, g);
  analogWrite(RGB_B, b);
}

// ── 거리에 따른 RGB 자동 제어 ──────────────────────────
void updateRGB(float d) {
  if (d >= 400) { setRGB(0, 3, 0); return; }

  if (d < D_DANGER) {
    bool on = (millis() % 300) < 150;
    setRGB(on ? 255 : 60, 0, 0);

  } else if (d < D_CLOSE) {
    float t = (d - D_DANGER) / (D_CLOSE - D_DANGER);
    setRGB(255, (int)(100 * t), 0);

  } else if (d < D_MID) {
    float t = 1.0 - (d - D_CLOSE) / (D_MID - D_CLOSE);
    setRGB(0, 0, (int)(30 + 150 * t));

  } else {
    float t = 1.0 - min((d - D_MID) / 100.0f, 1.0f);
    setRGB(0, (int)(5 + 35 * t), 0);
  }
}

// ── UDP 전송 (WiFi 준비 안 됐으면 Serial만 출력) ────────
void sendUDP(float minD, Level lv) {
  char buf[80];
  snprintf(buf, sizeof(buf),
    "B1,F:%d,B:%d,L:%d,R:%d,MIN:%d,LV:%s",
    (int)dist[0], (int)dist[1],
    (int)dist[2], (int)dist[3],
    (int)minD, lvStr(lv)
  );

  Serial.print("[UDP] "); Serial.println(buf);

  if (wifiReady) {
    if (!udpSend(buf)) {
      Serial.println("[UDP] Send failed");
    }
  }
}

// ── enum -> 문자열 ─────────────────────────────────────
const char* lvStr(Level lv) {
  switch (lv) {
    case DANGER_LV: return "DANGER";
    case CLOSE_LV:  return "CLOSE";
    case MID_LV:    return "MID";
    default:        return "SAFE";
  }
}

// ══════════════════════════════════════════════════════
//  ESP8266 AT 명령 처리
// ══════════════════════════════════════════════════════

// ESP8266 수신 버퍼 비우기
void espFlush() {
  unsigned long t = millis();
  while (millis() - t < 200) {
    while (espSerial.available()) espSerial.read();
  }
}

// AT 명령 전송 후 기대 문자열 포함 여부 확인
bool atCmd(const char* cmd, const char* expect, unsigned long timeout) {
  espFlush();
  espSerial.println(cmd);
  Serial.print("[AT] >> "); Serial.println(cmd);

  String resp = "";
  unsigned long start = millis();
  while (millis() - start < timeout) {
    while (espSerial.available()) {
      char c = espSerial.read();
      resp += c;
    }
    if (resp.indexOf(expect) != -1) {
      Serial.print("[AT] << "); Serial.println(resp);
      return true;
    }
  }
  Serial.print("[AT] TIMEOUT — got: "); Serial.println(resp);
  return false;
}

// WiFi 연결 + UDP 소켓 열기
bool wifiInit() {
  delay(3000);  // ESP8266 부팅 대기

  // 1) 모듈 응답 확인
  if (!atCmd("AT", "OK", 3000)) return false;

  // 2) Echo off
  atCmd("ATE0", "OK", 2000);

  // 3) Station 모드
  if (!atCmd("AT+CWMODE=1", "OK", 2000) &&
    !atCmd("AT+CWMODE=1", "no change", 2000))
  return false;

  // 4) WiFi 연결 (최대 15초)
  char joinCmd[80];
  snprintf(joinCmd, sizeof(joinCmd), "AT+CWJAP=\"%s\",\"%s\"", WIFI_SSID, WIFI_PASS);
  if (!atCmd(joinCmd, "OK", 15000)) return false;
  atCmd("AT+CIFSR", "OK", 3000);

  // 5) UDP 소켓 열기 (링크 ID=0, 로컬포트=임의)
  char udpCmd[80];
  snprintf(udpCmd, sizeof(udpCmd),
    "AT+CIPSTART=\"UDP\",\"%s\",%d", DEST_IP, DEST_PORT);
  if (!atCmd(udpCmd, "OK", 5000) && !atCmd(udpCmd, "ALREADY CONNECT", 2000)) return false;

  return true;
}

// UDP 데이터 전송 (AT+CIPSEND)
bool udpSend(const char* data) {
  int len = strlen(data) + 2;  // \r\n 포함

  char sendCmd[30];
  snprintf(sendCmd, sizeof(sendCmd), "AT+CIPSEND=%d", len);

  espSerial.println(sendCmd);
  Serial.print("[AT] >> "); Serial.println(sendCmd);

  // '>' 프롬프트 대기
  unsigned long start = millis();
  bool gotPrompt = false;
  String resp = "";
  while (millis() - start < 3000) {
    while (espSerial.available()) {
      char c = espSerial.read();
      resp += c;
      if (c == '>') { gotPrompt = true; break; }
    }
    if (gotPrompt) break;
  }

  if (!gotPrompt) {
    Serial.println("[AT] No '>' prompt");
    return false;
  }

  // 실제 데이터 전송
  espSerial.println(data);

  // SEND OK 대기
  return atCmd("", "SEND OK", 3000);
}