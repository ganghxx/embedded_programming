import pyfirmata2
import time

# 아두이노 포트 설정 (자동 감지)
PORT = pyfirmata2.Arduino.AUTODETECT

# 전역 변수 선언
board = None
led_pin = None

# --- 상태 변수 ---
# 밝기 (0.0 ~ 1.0 사이의 값)
brightness = 0.5  # 초기 밝기 50%

# 오토리핏을 위한 상태 플래그
increase_active = False
decrease_active = False


def update_led():
    """
    현재 'brightness' 변수 값을 LED 핀에 쓰고, 상태를 출력합니다.
    """
    global brightness
    # 밝기 값을 0.0과 1.0 사이로 제한 (Clamping)
    brightness = max(0.0, min(1.0, brightness))

    led_pin.write(brightness)
    # 보기 쉽게 퍼센트로 변환하여 출력
    print(f"💡 LED Brightness: {brightness:.0%}")


# --- 콜백 함수 정의 ---
def on_increase_change(state):
    """밝기 증가 버튼의 상태가 변할 때 호출 (오토리핏 플래그 설정)"""
    global increase_active
    increase_active = state
    # 버튼을 누르는 순간 바로 한번 적용
    if state:
        global brightness
        brightness += 0.1
        update_led()


def on_decrease_change(state):
    """밝기 감소 버튼의 상태가 변할 때 호출 (오토리핏 플래그 설정)"""
    global decrease_active
    decrease_active = state
    # 버튼을 누르는 순간 바로 한번 적용
    if state:
        global brightness
        brightness -= 0.1
        update_led()


def on_off_change(state):
    """끄기 버튼이 눌렸을 때 호출"""
    # 버튼이 눌리는 순간 (state=True)에만 동작
    if state:
        global brightness
        brightness = 0.0
        update_led()


try:
    # 아두이노 보드와 연결
    board = pyfirmata2.Arduino(PORT)
    print("✅ 아두이노 보드가 성공적으로 연결되었습니다.")

    # 이터레이터 설정 및 시작
    it = pyfirmata2.util.Iterator(board)
    it.start()

    # 핀 객체 설정
    led_pin = board.get_pin('d:11:p')  # LED (PWM 출력)
    button_inc = board.get_pin('d:6:i')  # 밝기 증가 버튼 (입력)
    button_dec = board.get_pin('d:7:i')  # 밝기 감소 버튼 (입력)
    button_off = board.get_pin('d:5:i')  # 끄기 버튼 (입력)

    # 모든 버튼 핀의 상태 보고 활성화
    button_inc.enable_reporting()
    button_dec.enable_reporting()
    button_off.enable_reporting()

    # 각 버튼에 콜백 함수 등록
    button_inc.register_callback(on_increase_change)
    button_dec.register_callback(on_decrease_change)
    button_off.register_callback(on_off_change)

    print("💡 준비 완료. 버튼으로 LED 밝기를 조절하세요.")
    # 초기 밝기 값으로 LED 설정
    update_led()

    # --- 메인 루프: 오토리핏 처리 ---
    while True:
        if increase_active or decrease_active:
            if increase_active:
                brightness += 0.1
            if decrease_active:
                brightness -= 0.1

            update_led()

        # 오토리핏 속도 조절 (0.1초)
        # 버튼을 누르고 있을 때만 sleep 간격을 짧게 하여 반복 효과를 줌
        time.sleep(0.1 if (increase_active or decrease_active) else 0.2)


except KeyboardInterrupt:
    print("\n프로그램을 종료합니다.")
except Exception as e:
    print(f"오류가 발생했습니다: {e}")

finally:
    # 프로그램 종료 시 보드 연결을 안전하게 해제
    if board is not None:
        led_pin.write(0)  # LED 끄기
        board.exit()
        print("🔌 아두이노 연결이 종료되었습니다.")