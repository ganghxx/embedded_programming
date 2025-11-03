#include <SoftwareSerial.h>

// 블루투스 모듈을 위한 SoftwareSerial 객체 생성 (RX: 2번, TX: 3번)
SoftwareSerial btSerial(2, 3);

void setup() {
  // PC와 통신할 시리얼 포트 시작
  Serial.begin(9600);
  // 블루투스와 통신할 시리얼 포트 시작
  btSerial.begin(9600);
  Serial.println("Receiver Ready. Waiting for data...");
}

void loop() {
  // 블루투스로부터 데이터가 들어오면,
  if (btSerial.available()) {
    // 받은 데이터를 그대로 PC 시리얼 포트로 전송
    Serial.write(btSerial.read());
  }
}