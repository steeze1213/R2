/*
 * ============================================================
 *  BOARD2 — 위험 감지 시스템
 *
 *  [사용 센서 & 실제 핀 구성]
 *   DHT11 모듈     : VCC / DATA / GND  (모듈형, 3핀)
 *   Sound 센서 모듈: +   / G   / A0 / D0
 *   포토센서(LDR)  : 단독 소자, 10kΩ 분압 회로 구성
 *   ESP8266 ESP-01 : VCC / GND / CH_PD / RST / IO0 / IO2 / TXD / RXD
 *
 *  [Arduino 핀 할당]
 *   D2  ← ESP TXD   (직결, 3.3V→5V 허용)
 *   D3  → ESP RXD   (10kΩ+10kΩ 분압 경유, 5V→2.5V)
 *   D4  ← DHT11 DATA
 *   A0  ← LDR 신호  (10kΩ 분압 회로)
 *   A1  ← Sound AO
 *
 *  [임계값 초과 시에만 UDP WiFi 전송]
 * ============================================================
 */

#include <SoftwareSerial.h>
#include <DHT.h>

// ── WiFi 설정 ──────────────────────────────────────────
const char* WIFI_SSID = "3F_302";
const char* WIFI_PASS = "0424719222!!";
const char* DEST_IP   = "192.168.0.133";
const int   DEST_PORT = 5000;

// ── 핀 정의 ───────────────────────────────────────────
#define DHT_PIN    4
#define DHT_TYPE   DHT11

#define LDR_PIN    A0
#define SOUND_PIN  A1

// ESP8266 SoftwareSerial (RX=D2 ← ESP TXD, TX=D3 → ESP RXD)
SoftwareSerial espSerial(2, 3);

// ── 임계값 ────────────────────────────────────────────
#define THRESH_TEMP    30.0f
#define THRESH_HUMID   70.0f
#define THRESH_DARK    300
#define THRESH_SOUND   550

// ── 전역 변수 ─────────────────────────────────────────
DHT dht(DHT_PIN, DHT_TYPE);
bool wifiReady = false;
unsigned long lastMs = 0;
const unsigned long INTERVAL = 2000;

// ── 함수 선언 ─────────────────────────────────────────
bool  atCmd(const char* cmd, const char* expect, unsigned long timeout = 3000);
void  espFlush();
bool  wifiInit();
bool  udpSend(const char* data);
void  printSerial(float t, float h, int ldr, int snd, bool* alr);

// ══════════════════════════════════════════════════════
void setup() {
  Serial.begin(9600);
  espSerial.begin(9600);
  dht.begin();

  Serial.println(F("================================"));
  Serial.println(F("  BOARD2  위험 감지 시스템 v1.0 "));
  Serial.println(F("================================"));
  Serial.println(F("[INIT] 센서 초기화 완료"));

  // Board1과 동일한 WiFi 초기화 함수 호출
  wifiReady = wifiInit();

  if (wifiReady) {
    Serial.println(F("[WiFi] Connected!"));
  } else {
    Serial.println(F("[WiFi] FAILED — check wiring/SSID/PW"));
  }

  Serial.println(F("--- 임계값 ---"));
  Serial.print(F(" 온도  > ")); Serial.print(THRESH_TEMP);  Serial.println(F(" C"));
  Serial.print(F(" 습도  > ")); Serial.print(THRESH_HUMID); Serial.println(F(" %"));
  Serial.print(F(" 조도  < ")); Serial.print(THRESH_DARK);  Serial.println(F(" /1023"));
  Serial.print(F(" 소음  > ")); Serial.print(THRESH_SOUND); Serial.println(F(" /1023"));
  Serial.println(F("================================\n"));
}

// ══════════════════════════════════════════════════════
void loop() {
  if (millis() - lastMs < INTERVAL) return;
  lastMs = millis();

  float temp  = dht.readTemperature();
  float humid = dht.readHumidity();
  int   ldr   = analogRead(LDR_PIN);
  int   snd   = analogRead(SOUND_PIN);

  if (isnan(temp) || isnan(humid)) {
    Serial.println(F("[ERR] DHT11 읽기 실패"));
    return;
  }

  bool alert =
      (temp  > THRESH_TEMP) ||
      (humid > THRESH_HUMID) ||
      (ldr   < THRESH_DARK) ||
      (snd   > THRESH_SOUND);

  // 한 줄 출력
  Serial.print("B2,");
  Serial.print("T:");
  Serial.print(temp, 1);
  Serial.print(" H:");
  Serial.print(humid, 1);
  Serial.print(" L:");
  Serial.print(ldr);
  Serial.print(" S:");
  Serial.print(snd);
  Serial.print(" LV:");
  Serial.println(alert ? "ALERT" : "SAFE");

  // UDP로 항상 전송
  if (wifiReady) {
    char buf[80];
    snprintf(buf, sizeof(buf),
      "B2,T:%.1f H:%.1f L:%d S:%d LV:%s", //Temp온도 Humid습도 ldr포토센서 snd사운드
      temp, humid, ldr, snd,
      alert ? "ALERT" : "SAFE"
    );

    udpSend(buf);
  }
}

// ══════════════════════════════════════════════════════
//  ESP8266 AT 명령 처리 — Board1과 완전 동일
// ══════════════════════════════════════════════════════

void espFlush() {
  unsigned long t = millis();
  while (millis() - t < 200) {
    while (espSerial.available()) espSerial.read();
  }
}

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

  // 5) UDP 소켓 열기
  char udpCmd[80];
  snprintf(udpCmd, sizeof(udpCmd),
    "AT+CIPSTART=\"UDP\",\"%s\",%d", DEST_IP, DEST_PORT);
  if (!atCmd(udpCmd, "OK", 5000) &&
    !atCmd(udpCmd, "ALREADY CONNECT", 2000) &&
    !atCmd(udpCmd, "CONNECT", 2000)) return false;

  return true;
}

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
      if (c == '>') {
        gotPrompt = true;
        break;
      }
    }
    if (gotPrompt) break;
  }

  if (!gotPrompt) {
    Serial.println("[AT] No '>' prompt");
    return false;
  }

  // 데이터 전송
  espSerial.println(data);

  // SEND OK 대기 (추가 AT 명령 보내지 않음)
  resp = "";
  start = millis();
  while (millis() - start < 3000) {
    while (espSerial.available()) {
      char c = espSerial.read();
      resp += c;
    }
    if (resp.indexOf("SEND OK") != -1) {
      Serial.println("[AT] SEND OK");
      return true;
    }
    if (resp.indexOf("ERROR") != -1) {
      Serial.println("[AT] SEND ERROR");
      return false;
    }
  }

  Serial.print("[AT] SEND TIMEOUT — got: ");
  Serial.println(resp);
  return false;
}

// ══════════════════════════════════════════════════════
//  시리얼 모니터 출력
// ══════════════════════════════════════════════════════
void printSerial(float t, float h, int ldr, int snd, bool* alr) {

  // 전체 위험 여부 판단
  bool anyAlert = alr[0] || alr[1] || alr[2] || alr[3];

  Serial.print(F("T:"));
  Serial.print(t, 1);
  Serial.print(F("  H:"));
  Serial.print(h, 1);
  Serial.print(F("  L:"));
  Serial.print(ldr);
  Serial.print(F("  S:"));
  Serial.print(snd);
  Serial.print(F("  |  LV: "));

  if (anyAlert) {
    Serial.println(F("ALERT"));
  } else {
    Serial.println(F("SAFE"));
  }
}
