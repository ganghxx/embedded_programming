import pyfirmata2
import time

# --- 핀 번호 설정 ---
LED_PIN = 11  # PWM이 가능한 핀 (~)
SWITCH_PIN = 7  # 실제 스위치가 연결된 핀 번호를 확인하세요.
LDR_PIN = 0  # 아날로그 0번 핀

# --- 전역 변수 (상태 관리) ---
is_system_enabled = False

try:
    # 아두이노 보드에 연결합니다.
    board = pyfirmata2.Arduino(pyfirmata2.Arduino.AUTODETECT)
    print("✅ 아두이노 보드에 성공적으로 연결되었습니다.")

    # ✨ 중요: 보드가 데이터를 샘플링하는 주기를 설정합니다. (빠진 부분)
    # 이 명령어가 없으면 데이터 리포팅이 불안정할 수 있습니다.
    board.samplingOn()

    # --- 핀 모드 설정 ---
    led_pin = board.get_pin(f'd:{LED_PIN}:p')
    switch_pin = board.get_pin(f'd:{SWITCH_PIN}:u')
    ldr_pin = board.get_pin(f'a:{LDR_PIN}:i')


    # --- 콜백 함수 정의 ---
    def toggle_system(state):
        global is_system_enabled
        if not state:
            is_system_enabled = not is_system_enabled
            if is_system_enabled:
                print("💡 시스템 ON. 조도에 따라 LED 밝기를 조절합니다.")
            else:
                print("🚫 시스템 OFF. LED를 끕니다.")
                led_pin.write(0)


    def adjust_brightness(value):
        if is_system_enabled:
            brightness = 1.0 - value
            led_pin.write(brightness)
            print(f"조도 값: {value:.2f} -> LED 밝기: {brightness:.2f}")


    # --- 콜백 등록 및 리포팅 활성화 ---
    print("스위치와 조도센서의 입력을 기다립니다...")

    switch_pin.register_callback(toggle_system)
    switch_pin.enable_reporting()

    ldr_pin.register_callback(adjust_brightness)
    ldr_pin.enable_reporting()

    print(f"\n🚀 {SWITCH_PIN}번 스위치로 시스템을 ON/OFF 하세요.")
    print("(프로그램을 종료하려면 Ctrl+C를 누르세요)")

    while True:
        time.sleep(1)

except KeyboardInterrupt:
    print("\n👋 프로그램을 중단합니다.")
except Exception as e:
    print(f"❌ 오류가 발생했습니다: {e}")

finally:
    if 'board' in locals() and board.is_active:
        print("보드와의 연결을 종료합니다.")
        led_pin.write(0)
        board.exit()