# 융합\_로보테크 AI 자율주행로봇 개발자 과정 2기
**미래융합교육원 주관(+트위니) (2025.12.30 ~ 2026.07.16)**

> 로봇 임베디드부터 ROS2, AI 센서퓨전, 자율주행까지 단계별로 학습하며 팀,개인 프로젝트 수행

---

## 과정 개요

| 항목 | 내용 |
|------|------|
| **기관** | 미래융합교육원(+트위니) |
| **기간** | 2025.12.30 ~ 2026.07.16 (진행 중) |
| **총 시간** | 908H |

### 커리큘럼

| STEP | 과목 | 시간 | 주요 내용 |
|------|------|------|-----------|
| 1 | 로봇 임베디드 프로그래밍 | 126H | Linux 환경 ROS2 개발 환경 구축, C++,Python 로봇 제어, 멀티스레딩,모듈화 |
| 2 | 로봇 알고리즘 디자인 | 72H | C++ 로봇 알고리즘 구현,최적화, 포인터,클래스,객체지향,템플릿 |
| 3 | ROS2 입문 | 80H | ROS2 기본,DDS,QoS, 노드,메시지(Topic/Service/Action), RQt,CLI,패키지 생성 |
| 4 | AI 센서퓨전 | 80H | OpenCV 영상처리 + LiDAR 융합, PCL 포인트 클라우드, YOLO 객체 탐지 |
| 5 | 자율주행 데이터랩 | 93H | pandas,numpy 데이터 분석, 머신러닝 경로 최적화, SLAM,실시간 위치추정 |
| 6 | ROS2 응용,심화 | 88H | Navigation Stack,MoveBase, 센서융합,비상정지, Gazebo,Rviz 시뮬레이션 |
| 7 | 현장실습 | 40H | 기업 배치 물류,자율주행 로봇 실습, 기업 멘토링 |
| 8 | 프로젝트 실전 | 329H | AGV 물류 자동화,자율주행 배달로봇,경로 최적화,사람추종 로봇 중 1개 선택 |

---

## 프로젝트 목록

| # | 프로젝트 | 유형 | 기간 |
|---|---------|------|------|
| 1 | [탑뷰 미로 탈출 게임](#1-탑뷰-미로-탈출-게임) | 팀 (5명) | 2026.01.07 ~ 01.09 |
| 2 | [지역별 교통사고 건수 분석 프로그램](#2-지역별-교통사고-건수-분석-프로그램) | 팀 (5명) | 2026.01.15 ~ 01.20 |
| 3 | [TCP 소켓 기반 마피아 게임](#3-tcp-소켓-기반-마피아-게임) | 팀 (5명) | 2026.01.23 ~ 01.27 |
| 4 | [로봇 경로 탐색 통합 관제 GUI](#4-로봇-경로-탐색-통합-관제-gui) | 팀 (5명) | 2026.01.29 ~ 02.05 |
| 5 | [삼성 스마트폰 재고관리 프로그램](#5-삼성-스마트폰-재고관리-프로그램) | 개인 | 2026.02.23 |
| 6 | [자율주행자동차 보조안전모듈](#6-자율주행자동차-보조안전모듈) | 팀 (3명) | 2026.02.26 ~ 03.06 |
| 7 | [YOLOv8 비상정지 기반 TurtleBot3 자율주행](#7-yolov8-비상정지-기반-turtlebot3-자율주행) | 개인 | 2026.04.24 |
| 8 | [공기질 연동 자율주행 공기청정 로봇](#8-공기질-연동-자율주행-공기청정-로봇) | 팀 (4명) | 2026.04.28 ~ 05.13 |
| 9 | [웹 개발 학습 및 ROS 웹 연동 실습](#9-웹-개발-학습-및-ros-웹-연동-실습) | 개인 | 2026.05.14 ~ 05.15 |

---

## 1. 탑뷰 미로 탈출 게임

### 프로젝트 주제

터미널 기반 탑뷰 시점의 미로 탈출 게임. MVC 구조로 설계하여 Map(메인루프), Monster, Player, Skill, Item 5개 모듈을 팀원 1인당 1모듈씩 분담해 구현했다. 기존 텍스트 기반 게임과 달리 아스키 아트를 활용한 시각적 표현과 아이템,스킬 시스템을 갖춘 것이 차별점이다.

### 팀 구성 및 본인 역할

5명 / **Player 클래스 담당 (View 파트)**
- 플레이어 상태 초기화 (좌표, 체력)
- 키 입력 처리: w/a/s/d 이동, r 공격, 그 외 무시
- 이동 스킬: 맵 모듈 판정 결과에 따라 이동 가능 여부 처리
- 공격 스킬: 인접 몬스터 존재 시 체력 1 감소 처리
- 피격/체력 갱신: 체력 0 시 게임오버 -> 스테이지 시작 상태로 초기화
- 스테이지 종료 조건 판정 및 상위 루프에 신호 반환
- 화면 표시: 플레이어를 'P'로 렌더링

### 기능적 요소

- txt 파일 기반 맵 데이터 로드 (20x20 2차원 리스트)
- 몬스터 랜덤 이동, 피격 시 데미지 표시
- 아이템 3종: 회복(H), 공격력(A), 방어막(B)
- 3개 스테이지 구성 (제너레이터 활용 단계별 호출)

### 활용 기술 및 도구

Python, MVC 패턴, 터미널 입출력, 파일 I/O

### 힘들었던 점 및 아쉬웠던 점

- 1인당 1모듈 분담 구조에서 Skill을 Player에서 분리하기 애매해 모듈 경계가 불명확해짐
- 기능 명세서 단계에서 중복,누락 항목이 많아 구현 시 코드가 꼬이는 문제 발생
- 전체 코드 중 50% 이상이 중복 함수이거나 미사용 코드로 최종 정리 시 버려짐

---

## 2. 지역별 교통사고 건수 분석 프로그램

### 프로젝트 주제

공공데이터 기반 지역별 교통사고 건수를 분석하고 PyQt5 GUI로 시각화하는 데스크탑 프로그램.

### 팀 구성 및 본인 역할

5명 / **데이터 전처리 및 GUI 구현 담당**
- CSV 데이터 로드 및 전처리
- PyQt5 기반 GUI 구현 (데이터 조회,수정 인터페이스)

### 기능적 요소

- CSV 파일 로드 및 지역별 데이터 파싱
- GUI에서 데이터 조회 및 값 수정
- 교통사고 건수 시각화

### 활용 기술 및 도구

Python, PyQt5, pandas, CSV

### 힘들었던 점 및 아쉬웠던 점

- GUI에서 CSV를 불러와 데이터 값을 수정하는 기능 구현 중 버그가 발생해 해결과정에서 시간이 오래 걸림

---

## 3. TCP 소켓 기반 마피아 게임

### 프로젝트 주제

서버/클라이언트 구조로 구현한 멀티플레이어 마피아 게임. 여러 클라이언트가 TCP 소켓으로 서버에 접속해 실시간으로 게임을 진행한다.

### 팀 구성 및 본인 역할

5명 / **설계 참여 및 게임 상태 관리,이벤트 처리 로직 주도 구현**
- 직업별 능력 구현 (마피아, 시민, 경찰 등 역할별 특수 행동 처리)
- 시간 흐름에 따른 게임 페이즈 전환 구현 (낮/밤 사이클, 투표, 처형 등)
- 전체 코드에 전반적 기여

### 기능적 요소

- TCP 소켓 서버/클라이언트 구조
- 다중 클라이언트 접속 처리
- 직업별 능력 시스템
- 페이즈별 시간 흐름 관리 (낮/밤 전환, 투표, 결과 처리)
- 터미널 입력 기반 채팅,행동 처리

### 활용 기술 및 도구

Python, TCP 소켓, 멀티스레딩, 서버/클라이언트 구조

### 힘들었던 점 및 아쉬웠던 점

- 시간 부족으로 일부 기능을 마무리하지 못함
- 터미널 입력 기반 대화 구현의 구조적 한계로 가독성,UI 개선에 제약이 있었음

---

## 4. 로봇 경로 탐색 통합 관제 GUI

### 프로젝트 주제

TurtleBot3를 HTTP REST API + Flask + MySQL + PyQt5 GUI로 연동한 로봇 경로 탐색 통합 관제 시스템. 맵 스캐닝, 경로 탐색, DB 저장, GUI 모니터링을 통합한 것이 특징이다.

### 팀 구성 및 본인 역할

5명 / **팀 전체 협업 + 독립 구현 파트 있음**
- ROI(관심 영역) 탐색 기능 - 팀 협업
- 센서 감지(맵 스캐너) - 팀 협업
- **DB 설계 및 구현** - 독립 구현
- **자체 시뮬레이션 구현** - 독립 구현

### 기능적 요소

- TurtleBot3 실시간 제어 및 경로 탐색
- ROI 기반 맵 스캐닝 및 장애물 감지
- Flask REST API 서버 구축
- MySQL 기반 경로,이벤트 데이터 저장
- PyQt5 GUI 통합 관제 화면
- 자체 시뮬레이션 환경 구현

### 활용 기술 및 도구

Python, Flask, HTTP REST API, MySQL, PyQt5, TurtleBot3(ROS), 소켓 통신

### 힘들었던 점 및 아쉬웠던 점

- 장애물 회피 알고리즘 완성도 부족 - 장애물 감지 후 회피가 제대로 되지 않아 충돌 발생
- 직진 및 회전 속도 개선을 시간 내에 하지 못함

---

## 5. 삼성 스마트폰 재고관리 프로그램

### 프로젝트 주제

PyQt5 + MySQL 기반 삼성 스마트폰 재고 관리 데스크탑 애플리케이션. 기획부터 DB 구성, GUI 구현까지 전 과정을 단독으로 수행한 개인 프로젝트.

### 팀 구성 및 본인 역할

**개인 프로젝트** / 전체 담당
- 시나리오 기획 및 DB 설계
- MySQL 서버 테이블 구성 (기종, 가격 등 데이터 직접 수작업 입력)
- PyQt5 + PyMySQL 연동 CRUD 기능 구현
- 로그인, 검색, 정렬, 중복 코드 방지 등 추가 기능 구현

### 기능적 요소

- 로그인 기능 (ID/PW 검증)
- 재고 목록 조회,추가,수정,삭제 (CRUD)
- 검색 (상품명,코드), 정렬 (열 헤더 클릭), 중복 코드 방지
- 가격 천단위 구분자 표시, 입력 폼 자동 초기화

### 활용 기술 및 도구

Python, PyQt5, PyMySQL, MySQL

### 힘들었던 점 및 아쉬웠던 점

- 삼성 스마트폰 데이터(기종, 가격 등)를 제공하는 공개 데이터 파일이 없어 DB 테이블에 직접 수작업으로 입력해야 했음

---

## 6. 자율주행자동차 보조안전모듈

### 프로젝트 주제

Arduino + ESP8266 기반 IoT 센서 모듈로 자율주행차 주변의 근접 거리와 복합 환경 데이터(온도,습도,조도,소음)를 실시간 감지하고, WiFi(UDP)로 PC에 전송해 PyQt5 GUI로 모니터링하는 보조 안전 시스템.

기존 ADAS가 거리 기반 충돌 회피에 집중한 것과 달리, **환경 데이터(조도 급변, 소음 급증, 온습도 이상)를 복합 감지**하여 위험 상황을 조기에 식별하는 것이 차별점이다.

### 팀 구성 및 본인 역할

3명 / **Board1 + 장애물 회피 로봇 + 보고서 작성 담당**

**Board1 - 4방향 근접 거리 측정 + WiFi UDP 전송**
- HC-SR04 초음파 센서 4개(전/후/좌/우) 배치 및 배선
- 100ms마다 4방향 거리 측정, 최솟값 기준 4단계 등급 분류 (SAFE / MID / CLOSE / DANGER)
- RGB LED PWM 제어: 거리에 비례한 밝기 조절, DANGER 등급 시 논블로킹 점멸 구현
- ESP8266 AT 명령 시퀀스 직접 구현 (외부 WiFi 라이브러리 미사용)
- 500ms 주기 또는 등급 변화 시 즉시 UDP 패킷 전송

**장애물 회피 로봇 - 자율 주행 + 장애물 회피**
- AF Motor Shield 기반 DC모터 4개 제어 (차동 방식 회전)
- 전방 HC-SR04 + 서보모터로 좌우 탐색 후 더 먼 방향으로 회전
- 좌우 거리 동일 시 후진 -> 좌회전 탈출 알고리즘 구현

### 시스템 구성

| 모듈 | 역할 | 담당 |
|------|------|------|
| Board1 | 4방향 근접 거리 측정 + WiFi UDP 전송 | 길민준 |
| Board2 | 환경 이상 감지 + WiFi 전송 | 김아영 |
| Board3 | 물리 경보 출력 + 버튼 입력 | 박선준 |
| Python GUI | 실시간 데이터 수신 및 시각화 | 박선준 |
| 장애물 회피 로봇 | 자율 주행 + 장애물 회피 | 길민준 |

### 기능적 요소

- 4방향 초음파 센서 실시간 거리 측정 및 4단계 위험 등급 분류
- 온도,습도,조도,소음 복합 환경 이상 감지 및 경보
- Arduino 3개 보드 + Python GUI를 UDP/HTTP로 실시간 연동
- PyQt5 Signal/Slot 패턴 멀티스레드 GUI
- LCD,LED,부저를 통한 물리 경보 출력
- 자율 주행 + 장애물 회피 로봇

### 활용 기술 및 도구

| 구분 | 내용 |
|------|------|
| **MCU** | Arduino Uno R3 |
| **WiFi** | ESP8266 ESP-01 (AT 명령 직접 구현) |
| **센서** | HC-SR04 x 5, DHT11, LDR, 사운드 센서 |
| **통신** | UDP (센서 데이터), HTTP GET (코드 수신) |
| **PC** | Python 3.14, PyQt5, requests, socket, threading |
| **기타** | AF Motor Shield, 서보모터, LCD I2C, RGB LED, 부저 |

### 프로젝트 주요 성과

- AT 명령만으로 ESP8266 WiFi 통신 완전 구현 (외부 WiFi 라이브러리 미사용)
- Arduino 3개 보드와 Python GUI를 UDP/HTTP로 실시간 연동 성공
- HTTP 서버 + UDP 클라이언트 동시 운용 (AT+CIPMUX=1 활용)

### 힘들었던 점 및 아쉬웠던 점

- 장애물 회피 알고리즘을 단순 좌우 거리 비교 수준에서 마무리한 것이 아쉬움 - 시간 여유가 있었다면 거리 차이 임계값 조건 추가 및 전방 외 다방향 감지로 확장하고 싶었음

### 기술적 개선 가능성

- 센서 데이터 DB 저장 및 시간대별 위험 패턴 분석 기능 추가
- Python GUI에 실시간 그래프(matplotlib) 추가
- ESP8266 -> ESP32 교체 시 처리 속도 및 안정성 향상 기대

---

## 7. YOLOv8 비상정지 기반 TurtleBot3 자율주행

### 프로젝트 주제

ROS2 Humble + Gazebo 환경에서 TurtleBot3 Waffle Pi가 일정 속도로 자율 주행하다가, PC 웹캠 영상에서 YOLOv8이 특정 객체(스마트폰)를 검출하면 즉시 비상정지하고, 객체가 시야에서 사라지면 자동으로 주행을 재개하는 시스템. 실습 과제의 "주행 완료 후 특정 객체 검출 시 비상정지 기능 추가" 요구사항을 반영한 개인 실습 구현.

WSL2 + Windows 하이브리드 환경에서 usbipd 기반 웹캠 직접 접근이 불가능한 상황을, Windows 측 Flask HTTP 스트림 서버 + WSL ROS2 브리지 노드 구조로 우회한 것이 특징이다.

### 팀 구성 및 본인 역할

**개인 실습** / 전체 단독 수행
- ROS2 패키지 설계 및 4개 노드 독립 구현
- Gazebo 커스텀 월드 제작 (custom_world.world)
- Windows ↔ WSL 스트림 파이프라인 구축
- 통합 런치 파일 및 문서화

### 시스템 구성

| 노드 / 구성요소 | 역할 |
|----------------|------|
| Windows Flask Server | PC 웹캠 프레임을 MJPEG HTTP 스트림으로 제공 |
| webcam_bridge | HTTP 스트림 구독 -> ROS2 이미지 토픽 발행 |
| yolo_detector | YOLOv8n 추론, cell phone 검출 시 비상정지 신호 발행 |
| emergency_stop | /cmd_vel_raw 필터링, 신호 활성 시 0 속도 덮어쓰기 |
| goal_driver | 상수 속도 주행 명령 발행 |
| Gazebo | TurtleBot3 Waffle Pi 시뮬레이션, 커스텀 월드 로드 |

### 기능적 요소

- TurtleBot3 Waffle Pi Gazebo 시뮬레이션 구동
- 장애물(박스)이 배치된 커스텀 월드 실행
- Windows PC 웹캠 실시간 HTTP MJPEG 스트리밍 (640x480, 15 FPS)
- YOLOv8n 사전학습 모델(COCO 80클래스)로 cell phone 실시간 검출
- 검출 시 /emergency_stop 토픽에 Bool 발행
- emergency_stop 필터 노드가 /cmd_vel_raw -> /cmd_vel 경로에서 속도를 0으로 덮어쓰기
- 신호 해제 후 1초 hold 시간 경과 시 자동 주행 재개 (검출 불안정성 대응)
- 단일 launch 파일로 전체 시스템(5개 프로세스) 순차 기동

### 활용 기술 및 도구

| 구분 | 내용 |
|------|------|
| **OS/환경** | Ubuntu 22.04 (WSL2) + Windows 11 |
| **ROS2** | Humble, rclpy, cv_bridge, launch |
| **시뮬레이션** | Gazebo Classic 11.10, turtlebot3_gazebo |
| **AI/비전** | YOLOv8n (Ultralytics), OpenCV 4.x |
| **스트리밍** | Flask, HTTP MJPEG, cv2.VideoCapture |
| **로봇** | TurtleBot3 Waffle Pi (시뮬레이션) |

### 프로젝트 주요 성과

- factory 플러그인 직접 로드 방식으로 Gazebo spawn_entity timeout 버그 우회
- usbipd 기반 웹캠 접근 실패 환경에서 Windows Flask 서버 + WSL HTTP 브리지로 대체 파이프라인 구축
- ROS2 토픽 리매핑(/cmd_vel -> /cmd_vel_raw -> /cmd_vel)으로 기존 주행 노드를 수정하지 않고 비상정지 필터 삽입
- TimerAction 기반 순차 기동으로 노드 간 초기화 순서 보장
- 커밋 6개를 논리 단위(패키지 구조 / 월드 / 주행 / 비상정지 파이프라인 / 통합 런치 / 문서화)로 분리

### 힘들었던 점 및 아쉬웠던 점

- WSL2에서 USB 웹캠을 usbipd로 attach 시도했으나 V4L2 select() timeout으로 프레임 수신 실패 - 환경

---

## 8. 공기질 연동 자율주행 공기청정 로봇

### 프로젝트 주제

TurtleBot3 Waffle Pi + ROS2 Humble 환경에서 미세먼지 센서(ESP01 + PMS7003) 데이터를 기반으로 오염 구역을 자동 감지하고, A* 경로 탐색 + Pure Pursuit 추종으로 자율주행하여 공기를 정화하는 로봇 시스템. Spring Boot 웹 대시보드를 통해 실시간 모니터링과 원격 제어가 가능하며, Cloudflare Tunnel로 외부 접속을 지원한다.

기존 공기청정기가 고정 위치에서만 작동하는 것과 달리, **로봇이 직접 오염 구역으로 이동하여 청정**하고, FSM 상태 머신으로 자율 판단(출동 -> 청소 -> 복귀)하는 것이 차별점이다.

### 팀 구성 및 본인 역할

4명 (팀 PURE) / **프로젝트 기획 + 센서 연동 + 자동 출동 로직 + PPT/영상 제작**
- 프로젝트 전체 기획 및 구조 설계
- A* + Pure Pursuit 주행 제어 구현
- Arduino, ESP-01, PMS7003 센서 연동 + MQTT 통신 구축
- 미세먼지 기반 자동 출동 로직 구현 (FSM: IDLE -> GO_TO_ZONE -> CLEANING -> RETURN)
- PPT 제작 및 시연 영상 촬영/편집

### 시스템 구성

| 계층 | 구성요소 | 역할 |
|------|---------|------|
| 센서 | ESP01 (ESP8266) + PMS7003 | Wi-Fi MQTT로 PM1.0/2.5/10 데이터 발행 |
| 통신 | Mosquitto MQTT 브로커 | 센서 ↔ ROS2 ↔ 웹 서버 메시지 중계 |
| 로봇 제어 | TurtleBot3 + ROS2 Humble | SLAM, Nav2, A* 경로 탐색, Pure Pursuit 추종 |
| 웹 | Spring Boot 4.0.6 + MySQL | REST API, MQTT 연동, Thymeleaf 대시보드 |
| 터널 | Cloudflare Tunnel | 외부 네트워크에서 웹 대시보드 접속 |

### 기능적 요소

**ROS2 로봇 제어 (14개 노드)**
- FSM 상태 머신: PM2.5 임계치 초과 시 자동 출동, 청소 완료 후 자동 복귀
- A* 경로 탐색: SLAM 맵 기반 최적 경로 계산 + 장애물 팽창(inflation) 적용
- Pure Pursuit 추종: 곡선 구간 부드러운 주행, LiDAR 기반 동적 장애물 회피
- ArUco 마커 정밀 정렬: 홈 복귀 시 카메라 기반 정밀 도킹 (EMA 필터링)
- 먼지 히트맵: 로봇 위치 + PM10 데이터를 0.10m 그리드 셀로 융합 시각화
- MQTT ↔ ROS2 양방향 브리지: 웹 명령 수신, 로봇 상태/경로/배터리/먼지 데이터 발행
- 순찰 모드: node1 -> node2 -> node3 -> home 순환 경로 자동 실행
- 시뮬레이션 모드: 센서 없이 FSM 로직 테스트 가능

**Spring Boot 웹 대시보드**
- 실시간 로봇 상태 모니터링 (위치, 배터리, FSM 상태)
- 9개 제어 명령 전송 (node1~3 이동, 홈 복귀, 정지, 충전, 순찰, 청정 ON/OFF, 긴급정지)
- 구역별 PM1.0 / PM2.5 / PM10 실시간 표시
- SLAM 맵 위 로봇 위치 + 먼지 히트맵 오버레이
- 맵 클릭 네비게이션 (클릭 좌표 -> Nav2 Goal)
- 3D ROS 시각화 (ROS3D.js): 2D 맵 + LiDAR + PointCloud + 카메라 피드
- 회원가입 / 로그인

### 활용 기술 및 도구

| 구분 | 내용 |
|------|------|
| **로봇** | TurtleBot3 Waffle Pi (LDS-03 LiDAR, Intel RealSense) |
| **OS** | Ubuntu 22.04 |
| **ROS2** | Humble, rclpy, Nav2, AMCL, Cartographer |
| **경로** | A* 알고리즘, Pure Pursuit, Safety Cost Map |
| **센서** | ESP01 (ESP8266) + PMS7003 미세먼지 센서 |
| **통신** | Mosquitto MQTT 브로커, paho-mqtt |
| **웹** | Spring Boot 4.0.6, Java 21, Thymeleaf, MySQL 8 |
| **시각화** | ROS3D.js, Three.js, ROSBridge WebSocket |
| **터널** | Cloudflare Tunnel |
| **기타** | ArUco 마커 (OpenCV), numpy, Pillow, Tkinter |

### 프로젝트 주요 성과

- A* + Pure Pursuit 조합으로 SLAM 맵 기반 자율주행 완전 구현 (Nav2 의존 최소화)
- Safety Cost Map으로 장애물 근접 시 비용 증가하여 안전 경로 생성
- ArUco 마커 + EMA 필터링으로 홈 도킹 정밀도 확보
- ESP01 센서 -> MQTT -> ROS2 -> 웹 대시보드까지 전 구간 실시간 데이터 파이프라인 구축
- Spring Boot에서 MQTT Subscribe/Publish 양방향 연동으로 웹 기반 원격 제어 실현
- 14개 ROS2 노드 + 6개 MQTT Subscriber를 단일 launch 파일로 통합 기동

### 힘들었던 점 및 아쉬웠던 점

- MQTT 브리지 노드가 많아(6개) 데이터 흐름 디버깅이 복잡했음
- Pure Pursuit 파라미터(lookahead distance, 최대 회전 속도) 튜닝에 시간 소요
- 좁은 통로에서 A* inflation과 로봇 크기 간 균형 조정이 어려웠음
- 웹 3D 대시보드에서 rosbridge_server 연결 불안정 이슈 간헐적 발생

### 기술적 개선 가능성

- 다중 로봇 협업 청소 (멀티 에이전트)
- 딥러닝 기반 오염원 예측 및 선제 대응
- 자동 충전 도킹 스테이션 연동
- 모바일 앱 (Flutter) 연동

> **소스코드**: [github.com/steeze1213/TBPJ](https://github.com/steeze1213/TBPJ)

---

## 9. 웹 개발 학습 및 ROS 웹 연동 실습

### 프로젝트 주제

HTML, CSS, JavaScript 기본 문법부터 DOM/이벤트 처리, 그리고 ROS와 웹을 연동하는 roslibjs/ros2djs 라이브러리 활용까지 단계별로 학습한 개인 실습. 단순 정적 페이지(인물 소개)에서 시작해 SPA형 채팅 UI 클론, JS 기반 동적 웹 앱(디지털 시계/TODO), 마지막으로 웹 브라우저에서 ROS 토픽을 구독/발행해 turtlesim을 조종하고 실시간 SLAM 지도를 렌더링하는 ROS 웹 클라이언트 구현까지 진행했다.

기존 PyQt5 기반 데스크탑 GUI에서만 다뤘던 로봇 제어,모니터링 인터페이스를, **rosbridge_server 기반 WebSocket으로 분리**해 OS,설치 환경에 종속되지 않는 웹 클라이언트로 재구성한 것이 의미 있는 지점이다.

### 팀 구성 및 본인 역할

**개인 실습** / 전체 단독 수행
- HTML 주요 태그 조사 및 인물 소개 페이지 구현
- CSS Flexbox/Grid 기반 로그인,친구목록,채팅 페이지 클론 구현
- Vanilla JavaScript로 디지털 시계, TODO 리스트 웹 앱 구현
- roslibjs 기반 turtlesim 웹 컨트롤러 구현 (HUD 스타일 UI 디자인 포함)
- ros2djs 기반 실시간 SLAM 맵 뷰어 및 대시보드 확장 구현

### 시스템 구성

| 구성요소 | 역할 |
|---------|------|
| html_tag.html | HTML 기본 태그(h, p, ul, img, blockquote 등) 학습용 인물 소개 페이지 |
| roboclub/ | CSS 속성 학습용 카카오톡 스타일 멀티 페이지 클론(로그인/친구목록/채팅) |
| clock/ | JS Date 객체 + setInterval 기반 7-세그먼트 스타일 디지털 시계 |
| todo/ | JS DOM 조작 + 이벤트 핸들링 기반 TODO 추가/삭제 웹 앱 |
| web_robot/ | roslibjs로 rosbridge에 연결, /turtle1/cmd_vel 발행해 turtlesim 원격 조종 |
| web_robot2/ | ros2djs OccupancyGridClient로 /map 토픽 구독, 실시간 SLAM 지도 시각화 |

### 기능적 요소

**HTML / CSS 기초**
- 자주 사용되는 HTML 태그 20종 조사 후 인물 소개 페이지 구성
- CSS 속성 30종 조사 및 카카오톡 클론(로그인 -> 친구목록 -> 1:1 채팅) 멀티 페이지 구현
- 컴포넌트(header/navbar/userlist) 단위 CSS 분리

**JavaScript 동적 웹 앱**
- 디지털 시계: 1초 간격 setInterval, 꺼진 세그먼트 잔상(ghost) 표현으로 LCD 느낌 재현
- TODO 리스트: 추가/삭제 이벤트, 빈 상태(empty) 표시 토글

**ROS 웹 연동**
- rosbridge_websocket(9090 포트)에 ws:// 연결 후 연결 상태 LED 표시
- 5방향(상하좌우+STOP) 버튼으로 geometry_msgs/Twist 발행
- OccupancyGridClient로 /map 토픽 자동 구독 및 EaselJS 캔버스에 실시간 렌더링
- 맵 갱신 시 viewer scale/shift 자동 조정으로 전체 맵이 화면에 맞도록 처리

### 활용 기술 및 도구

| 구분 | 내용 |
|------|------|
| **마크업/스타일** | HTML5, CSS3 (Flexbox, Grid, 커스텀 폰트 Orbitron/JetBrains Mono) |
| **스크립트** | Vanilla JavaScript (ES6+), DOM API, setInterval, addEventListener |
| **ROS 웹 라이브러리** | roslibjs, ros2djs, EaselJS, EventEmitter2 |
| **ROS** | ROS2 Humble, rosbridge_server, turtlesim, turtlebot3_cartographer |
| **개발 도구** | VS Code, Chrome DevTools, CDN(jsDelivr) |

### 프로젝트 주요 성과

- ROS-Web 간 양방향 통신 파이프라인을 rosbridge WebSocket으로 단순화하여 PyQt 의존 없이 브라우저만으로 로봇 제어 가능
- 컨트롤러 UI를 단순 버튼에서 HUD 스타일(코너 프레임 + 상태 LED)로 재디자인하여 가독성 개선
- CSS를 페이지별/컴포넌트별로 분리해 카카오톡 클론의 유지보수성 확보
- 디지털 시계의 ghost 세그먼트 처리로 실제 LCD 디스플레이의 시각적 특성을 재현

### 힘들었던 점 및 아쉬웠던 점

- ros2djs의 좌표계와 캔버스 좌표계 간 Y축 반전 이슈로 로봇 마커 위치가 어긋나는 문제 발생
- rosbridge_server가 실행되지 않은 상태에서 연결 실패 처리(재시도 로직 부재) 미흡
- CSS 작업 시 컴포넌트 경계가 페이지별 스타일과 일부 겹쳐 우선순위 충돌 발생

### 기술적 개선 가능성

- 디지털 시계,TODO에 LocalStorage 연동해 새로고침 후에도 상태 보존
- ROS 웹 컨트롤러에 키보드 입력(WASD) 핸들링 추가
- 맵 뷰어에 로봇 마커(/odom 구독)와 목표점 클릭 발행(/goal_pose) 기능 통합
- TypeScript + 빌드 도구(Vite) 도입으로 코드 품질,개발 경험 개선

---

## 기술 블로그

학습 과정 및 실습 내용은 티스토리에 정리되어 있습니다. 개인 아이디어 없이 수업 마무리 형태로 진행된 개인 과제는 블로그에서 확인할 수 있으며, 이 레포지토리에는 포함하지 않았습니다.

[Tistory - 로보테크 AI](https://steezer.tistory.com/category/%EB%A1%9C%EB%B3%B4%ED%85%8C%ED%81%ACAI)

---

## 프로젝트 구조

```bash
R2/
├── Game/
│   └── Game/
├── Data/
│   └── Data/
├── TCP/
│   └── TCP/
├── TB3/
│   └── RB/
├── PyQt+MySQL/
│   └── PyQt+MySQL/
├── Arduino+UDP/
│   └── Arduino+UDP/
├── EmergencyStopNav/
│   └── (링크: github.com/steeze1213/emergency_stop_nav)
├── TBPJ/
│   └── (링크: github.com/steeze1213/TBPJ)
└── Web/
    ├── html_tag.html
    ├── clock/
    ├── todo/
    ├── roboclub/
    ├── web_robot/
    └── web_robot2/
```
