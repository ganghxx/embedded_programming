/* * ============= main_tx.ino =============
 * '메인 Uno'용 코드: MPU, 조이스틱, 블루투스를 처리하고
 * OLED Uno(7번 핀)로 모드 신호만 보냅니다.
 */

#include <Wire.h>
#include <Adafruit_MPU6050.h>
#include <Adafruit_Sensor.h>
#include <SoftwareSerial.h>
#include <stdio.h>
#include <stdlib.h>

// --- 신호 핀 설정 ---
const int oledModePin = 7; // OLED Uno로 신호를 보낼 핀

// --- 기존 전역 변수 ---
Adafruit_MPU6050 mpu;
SoftwareSerial btSerial(2, 3); // RX, TX

// 조이스틱 핀
const int joyXPin = A0;
const int joyYPin = A1;
const int joySWPin = 8;
// --- 상보 필터를 위한 변수 선언 ---
float angleX = 0, angleY = 0;
float gyroX_cal = 0, gyroY_cal = 0;
unsigned long timer = 0;

int lastOledMode = 0; 
char dataPacket[80]; 

void setup() {
  Serial.begin(9600);
  btSerial.begin(9600);

  pinMode(joySWPin, INPUT_PULLUP);
  pinMode(joyXPin, INPUT);
  
  // ⬅️ [추가] 신호 핀을 출력으로 설정
  pinMode(oledModePin, OUTPUT);
  digitalWrite(oledModePin, LOW); // 초기 모드 (마우스) 신호
  // -------------------------

  if (!mpu.begin()) {
    Serial.println("MPU6050 not found!");
    while (1) delay(10);
  }
  Serial.println("MPU Init Success");

  mpu.setAccelerometerRange(MPU6050_RANGE_8_G);
  mpu.setGyroRange(MPU6050_RANGE_500_DEG);
  mpu.setFilterBandwidth(MPU6050_BAND_21_HZ);

  // --- 자이로 센서 캘리브레이션 ---
  Serial.println("Calibrating Gyro... Keep the sensor still!");
  delay(1000);
  for (int i = 0; i < 500; i++) {
    sensors_event_t a, g, temp;
    mpu.getEvent(&a, &g, &temp);
    gyroX_cal += g.gyro.x;
    gyroY_cal += g.gyro.y;
    delay(3);
  }
  gyroX_cal /= 500;
  gyroY_cal /= 500;
  Serial.println("Calibration Complete!");
  timer = micros();
}


void loop() {
  sensors_event_t a, g, temp;
  mpu.getEvent(&a, &g, &temp); 

  // --- 조이스틱 값 읽기 및 모드 결정 ---
  int joyXValue = analogRead(joyXPin);
  int joyYValue = analogRead(joyYPin);
  int clickValue = (digitalRead(joySWPin) == LOW) ? 1 : 0;

  int modeValue = 0; // 0: 마우스, 1: 아래, -1: 위, 2: 제스처
  if (joyXValue < 200) { 
    modeValue = 2; // 제스처 모드(2)
  } else {
    if (joyYValue < 200) {
      modeValue = 1; // 아래 스크롤(1)
    } else if (joyYValue > 800) {
      modeValue = -1; // 위 스크롤(-1)
    }
  }

  // --- ⬅️ [변경] OLED 신호 핀 제어 ---
  int currentOledMode = (modeValue == 2) ? 2 : 0; 
  
  if (currentOledMode != lastOledMode) { 
    if (currentOledMode == 2) {
      digitalWrite(oledModePin, HIGH); // "제스처 모드" 신호
    } else {
      digitalWrite(oledModePin, LOW); // "마우스 모드" 신호
    }
    lastOledMode = currentOledMode; 
  }
  
  // --- [유지] SRAM 최적화된 패킷 전송 ---

  if (modeValue == 2) {
    // 2번 모드(제스처)
    char ax_str[10], ay_str[10], az_str[10];
    char gx_str[10], gy_str[10], gz_str[10];
    
    dtostrf(a.acceleration.x, 4, 2, ax_str);
    dtostrf(a.acceleration.y, 4, 2, ay_str);
    dtostrf(a.acceleration.z, 4, 2, az_str);
    dtostrf(g.gyro.x - gyroX_cal, 4, 2, gx_str);
    dtostrf(g.gyro.y - gyroY_cal, 4, 2, gy_str);
    dtostrf(g.gyro.z, 4, 2, gz_str);

    sprintf(dataPacket, "<G,%s,%s,%s,%s,%s,%s>", 
            ax_str, ay_str, az_str, gx_str, gy_str, gz_str);

    btSerial.println(dataPacket);
    Serial.println(dataPacket); 

    timer = micros();
    
  } else {
    // 그 외 모드(0, 1, -1) (마우스/스크롤)
    float dt = (micros() - timer) / 1000000.0;
    timer = micros();
    float accelAngleX = atan2(a.acceleration.y, a.acceleration.z) * RAD_TO_DEG;
    float accelAngleY = atan2(-a.acceleration.x, sqrt(a.acceleration.y * a.acceleration.y + a.acceleration.z * a.acceleration.z)) * RAD_TO_DEG;
    float gyroX = g.gyro.x - gyroX_cal;
    float gyroY = g.gyro.y - gyroY_cal;
    angleX = 0.98 * (angleX + gyroX * dt) + 0.02 * accelAngleX;
    angleY = 0.98 * (angleY + gyroY * dt) + 0.02 * accelAngleY;
    
    char angleY_str[10], angleX_str[10];
    dtostrf(angleY, 4, 2, angleY_str);
    dtostrf(angleX, 4, 2, angleX_str);

    sprintf(dataPacket, "<M,%s,%s,%d,%d>", 
            angleY_str, angleX_str, modeValue, clickValue);
            
    btSerial.println(dataPacket);
    Serial.println(dataPacket); 
  }
}