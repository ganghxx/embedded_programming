import pyfirmata2
import time

# --- 핀 번호 및 상수 설정 ---
LED_PIN = 11
SWITCH_PIN = 7
LDR_PIN = 0
BUZZER_PIN = 8
TONE_CMD = 0x7E

# --- 전역 변수 (상태 관리) ---
is_system_enabled = False

# --- 부저 제어 함수 ---
def play_tone(board, pin, freq, duration):
    data = [
        pin,
        freq & 0x7F, (freq >> 7) & 0x7F,
        duration & 0x7F, (duration >> 7) & 0x7F
    ]
    board.send_sysex(TONE_CMD, data)

try:
    board = pyfirmata2.Arduino(pyfirmata2.Arduino.AUTODETECT)
    print("✅ 아두이노 보드에 성공적으로 연결되었습니다.")
    board.samplingOn()

    # --- 핀 모드 설정 ---
    led_pin = board.get_pin(f'd:{LED_PIN}:p')
    switch_pin = board.get_pin(f'd:{SWITCH_PIN}:u')
    ldr_pin = board.get_pin(f'a:{LDR_PIN}:i')

    # --- 콜백 함수 정의 ---
    def toggle_system(state):
        global is_system_enabled
        if not state:
            print("삑! 🔊 스위치 눌림")
            buzzer_duration_ms = 100  # 부저 울릴 시간 (밀리초)
            play_tone(board, BUZZER_PIN, 523, buzzer_duration_ms)

            # ✨ 여기가 수정된 부분입니다 ✨
            # 아두이노가 부저 소리를 끝낼 시간을 파이썬에서 기다려줍니다.
            time.sleep(buzzer_duration_ms / 1000.0)

            is_system_enabled = not is_system_enabled
            if is_system_enabled:
                print("💡 시스템 ON. 조도에 따라 LED 밝기를 조절합니다.")
            else:
                print("🚫 시스템 OFF. LED를 끕니다.")
                led_pin.write(0)

    def adjust_brightness(value):
        if is_system_enabled:
            brightness = 0.0
            if value <= 0.75:
                brightness = 1.0
            elif value >= 0.95:
                brightness = 0.0
            else:
                brightness = 1.0 - ((value - 0.75) / (0.95 - 0.75))
            led_pin.write(brightness)
            print(f"조도 값: {value:.3f} -> LED 밝기: {brightness:.2f}")

    # --- 콜백 등록 및 리포팅 활성화 ---
    print("스위치와 조도센서의 입력을 기다립니다...")
    switch_pin.register_callback(toggle_system)
    switch_pin.enable_reporting()
    ldr_pin.register_callback(adjust_brightness)
    ldr_pin.enable_reporting()
    print(f"\n🚀 {SWITCH_PIN}번 스위치로 시스템을 ON/OFF 하고 소리를 들어보세요.")
    print("(프로그램을 종료하려면 Ctrl+C를 누르세요)")

    while True:
        time.sleep(1)

except KeyboardInterrupt:
    print("\n👋 프로그램을 중단합니다.")
except Exception as e:
    print(f"❌ 오류가 발생했습니다: {e}")

finally:
    if 'board' in locals():
        print("보드와의 연결을 종료합니다.")
        if 'led_pin' in locals():
            led_pin.write(0)
        board.exit()