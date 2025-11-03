#include <SoftwareSerial.h>

// HC-05 연결 핀 (RX, TX)
SoftwareSerial btSerial(10, 11);

void setup() {
  // PC와의 통신 시작
  Serial.begin(9600);
  // 블루투스와의 통신 시작
  btSerial.begin(9600);
  Serial.println("Receiver B is ready. Waiting for data from A.");
}

void loop() {
  // 블루투스로부터 데이터가 들어오면,
  if (btSerial.available()) {
    // 받은 데이터를 PC 시리얼 모니터에 출력한다.
    Serial.write(btSerial.read());
  }
}