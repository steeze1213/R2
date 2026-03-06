#include <LiquidCrystal_I2C.h>
#include <SoftwareSerial.h>

LiquidCrystal_I2C lcd(0x27, 16, 2);

const char* WIFI_SSID = "3F_302";
const char* WIFI_PASS = "0424719222!!";
const char* PC_IP     = "192.168.0.133";
const int   PC_PORT   = 5000;
const int   BUZZER    = 12;
const int   led_red   = 9;
const int   led_yellow = 10;
const int   led_green = 11;

SoftwareSerial espSerial(2, 3);

bool wifiReady = false;
int lastState7 = LOW;
int lastState8 = LOW;
String httpBuf = "";

// ─────────────────────────────────────────────
void showLcd(const char* msg) {
  lcd.clear(); lcd.backlight();
  lcd.setCursor(0, 0); lcd.print(msg);
}

void beep(int freq = 1000, int ms = 150) {
  tone(BUZZER, freq, ms); delay(ms); noTone(BUZZER);
}

// ─────────────────────────────────────────────
bool atCmd(const char* cmd, const char* expect, unsigned long timeout) {
  unsigned long t = millis();
  while (millis() - t < 20) while (espSerial.available()) espSerial.read();

  if (strlen(cmd) > 0) {
    espSerial.println(cmd);
    Serial.print("[>>] "); Serial.println(cmd);
  }

  String resp = "";
  unsigned long start = millis();
  while (millis() - start < timeout) {
    while (espSerial.available()) resp += (char)espSerial.read();
    if (resp.indexOf(expect) != -1) {
      Serial.print("[<<] "); Serial.println(resp);
      return true;
    }
  }
  Serial.print("[TO] "); Serial.println(resp);
  return false;
}

// ─────────────────────────────────────────────
bool wifiInit() {
  delay(3000);
  if (!atCmd("AT",          "OK",        3000)) return false;
  atCmd("ATE0",             "OK",        2000);
  if (!atCmd("AT+CWMODE=1", "OK",        2000) &&
      !atCmd("AT+CWMODE=1", "no change", 2000)) return false;

  char buf[96];
  snprintf(buf, sizeof(buf), "AT+CWJAP=\"%s\",\"%s\"", WIFI_SSID, WIFI_PASS);
  if (!atCmd(buf, "OK", 40000)) return false;

  atCmd("AT+CIFSR",               "OK", 5000);
  if (!atCmd("AT+CIPMUX=1",       "OK", 2000)) return false;
  atCmd("AT+CIPSERVER=0",         "OK", 2000);
  //if (!atCmd("AT+CIPSERVER=1,80", "OK", 3000)) return false;
  if (!atCmd("AT+CIPSERVER=1,80", "OK",        3000) && //no change도 성공으로 인정
      !atCmd("AT+CIPSERVER=1,80", "no change", 2000)) return false;

  snprintf(buf, sizeof(buf), "AT+CIPSTART=0,\"UDP\",\"%s\",%d", PC_IP, PC_PORT);
  if (!atCmd(buf, "OK", 8000) && !atCmd(buf, "ALREADY CONNECT", 2000)) return false;

  // ESP baudrate를 38400으로 변경 (다음 업로드부터는 espSerial.begin(38400) 으로 바꿀 것)
  atCmd("AT+UART_DEF=38400,8,1,0,0", "OK", 2000);

  return true;
}

// ─────────────────────────────────────────────
void udpSend(const char* data) {
  char cmd[32];
  snprintf(cmd, sizeof(cmd), "AT+CIPSEND=0,%d", strlen(data) + 2);
  espSerial.println(cmd);

  unsigned long t = millis();
  while (millis() - t < 1000) {
    while (espSerial.available()) if (espSerial.read() == '>') goto send;
  }
  return;

send:
  espSerial.println(data);
  // SEND OK 기다리지 않음
}

// ─────────────────────────────────────────────
void httpReply(int id, const char* body) {
  String payload = String("HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\nConnection: close\r\n\r\n") + body;
  String cmd = String("AT+CIPSEND=") + id + "," + payload.length();
  if (atCmd(cmd.c_str(), ">", 2000)) {
    espSerial.print(payload);
    atCmd("", "SEND OK", 2000);
  }
  cmd = String("AT+CIPCLOSE=") + id;
  atCmd(cmd.c_str(), "OK", 1000);
}

// ─────────────────────────────────────────────
void processHttp() {
  while (espSerial.available()) {
    httpBuf += (char)espSerial.read();
    if (httpBuf.length() > 512) httpBuf = httpBuf.substring(256);
  }

  int ipdIdx = httpBuf.indexOf("+IPD,");
  if (ipdIdx == -1) return;

  int id = httpBuf.charAt(ipdIdx + 5) - '0';
  if (id < 0 || id > 4) { httpBuf = ""; return; }

  int ci = httpBuf.indexOf("code=", ipdIdx);
  if (ci == -1 || ci + 6 >= (int)httpBuf.length()) return;

  char d1 = httpBuf.charAt(ci + 5);
  char d2 = httpBuf.charAt(ci + 6);
  if (d1 < '0' || d1 > '9' || d2 < '0' || d2 > '9') { httpBuf = ""; return; }

  int code = (d1 - '0') * 10 + (d2 - '0');
  httpBuf = "";

  Serial.print("[HTTP] code="); Serial.println(code);
  showLcd(("CODE " + String(code)).c_str());

  if(code == 17)
    showLcd("left pressed");
  else if(code == 18)
    showLcd("right pressed");
  else if(code == 20)
  {
    showLcd("SAFE");
    digitalWrite(led_green, HIGH);   
    digitalWrite(led_yellow, LOW);     
    digitalWrite(led_red, LOW);         
  }
    
  else if(code == 21)
  {
    showLcd("WARN");
    digitalWrite(led_green, LOW);      
    digitalWrite(led_yellow, HIGH);      
    digitalWrite(led_red, LOW);         
  }
    
  else if(code == 22)
  {
    showLcd("DANGER");
    digitalWrite(led_green, LOW);      
    digitalWrite(led_yellow, HIGH);      
    digitalWrite(led_red, LOW);   
  }
    
  else if(code == 23)
  {
    showLcd("GOOD BYE");
    digitalWrite(led_green, LOW);      
    digitalWrite(led_yellow, LOW);      
    digitalWrite(led_red, HIGH);   
  }
  // 기존 마지막 else if(code == 23) 블록 바로 아래에 추가

else if (code == 34)
{
    // LCD는 16칸 2줄 — 줄 나눔 필요
    lcd.clear(); lcd.backlight();
    lcd.setCursor(0, 0); lcd.print("Tunnel expected");
    lcd.setCursor(0, 1); lcd.print("Close windows!");
    digitalWrite(led_green, LOW);
    digitalWrite(led_yellow, HIGH);   // 주의 색상
    digitalWrite(led_red, LOW);
}
else if (code == 35)
{
    lcd.clear(); lcd.backlight();
    lcd.setCursor(0, 0); lcd.print("Outdoor! You can");
    lcd.setCursor(0, 1); lcd.print("open windows.");
    digitalWrite(led_green, HIGH);    // 안전 색상
    digitalWrite(led_yellow, LOW);
    digitalWrite(led_red, LOW);
}  

  beep(1000, 150);
  httpReply(id, "OK");
}

// ─────────────────────────────────────────────
void setup() {
  Serial.begin(9600);
  espSerial.begin(9600);  // ← 지금은 9600, AT+UART_DEF 성공 후 38400으로 바꿀 것

  pinMode(7, INPUT); pinMode(8, INPUT);
  pinMode(led_red, OUTPUT); pinMode(led_yellow, OUTPUT); pinMode(led_green, OUTPUT);
  
  pinMode(BUZZER, OUTPUT);

  digitalWrite(led_green, LOW);   
  digitalWrite(led_yellow, LOW);     
  digitalWrite(led_red, LOW);      

  lcd.init();
  showLcd("Loading...");

  wifiReady = wifiInit();
  showLcd(wifiReady ? "READY" : "WiFi FAIL");
  if (wifiReady) udpSend("EVT,BOOT,OK");
}

// ─────────────────────────────────────────────
void loop() {
  if (wifiReady) processHttp();

  int s7 = digitalRead(7);
  int s8 = digitalRead(8);

  if (s7 != lastState7) {
    if (s7 == 1) { showLcd("BTN 7"); beep(); if (wifiReady) udpSend("EVT,BTN,7"); }
    lastState7 = s7; delay(50);
  }
  if (s8 != lastState8) {
    if (s8 == 1) { showLcd("BTN 8"); beep(); if (wifiReady) udpSend("EVT,BTN,8"); }
    lastState8 = s8; delay(50);
  }
}