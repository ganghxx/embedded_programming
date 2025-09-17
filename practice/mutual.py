import pyfirmata2
import time

# 아두이노 포트 설정 (자동 감지)
PORT = pyfirmata2.Arduino.AUTODETECT

# 'board' 객체와 핀 객체들을 전역에서 참조할 수 있도록 미리 선언
board = None
led1_pin, led2_pin = None, None

# --- 전역 상태 변수 ---
# mode = 1 : LED 1 활성화 상태
# mode = 0 : LED 2 활성화 상태
mode = 1  # 프로그램 시작 시 초기 상태


def update_leds():
    """
    현재 'mode' 변수 값에 따라 모든 LED의 상태를 일괄 갱신합니다.
    """
    if mode == 1:
        # 모드 1: LED 1 켜고, LED 2 끄기
        led1_pin.write(True)
        led2_pin.write(False)
        print(f"Mode: {mode} | LED 1 ON, LED 2 OFF")
    elif mode == 0:
        # 모드 0: LED 1 끄고, LED 2 켜기
        led1_pin.write(False)
        led2_pin.write(True)
        print(f"Mode: {mode} | LED 1 OFF, LED 2 ON")


def on_button_A_change(state):
    """버튼 A의 상태가 변할 때 호출되는 콜백 함수"""
    global mode
    # 버튼이 눌렸을 때만 (state = True) 동작
    if state:
        print("Button A pressed.")
        # LED 1 활성화 모드로 변경
        mode = 1
        # LED 상태 일괄 갱신
        update_leds()


def on_button_B_change(state):
    """버튼 B의 상태가 변할 때 호출되는 콜백 함수"""
    global mode
    # 버튼이 눌렸을 때만 (state = True) 동작
    if state:
        print("Button B pressed.")
        # LED 2 활성화 모드로 변경
        mode = 0
        # LED 상태 일괄 갱신
        update_leds()


try:
    # 아두이노 보드와 연결
    board = pyfirmata2.Arduino(PORT)
    print("✅ 아두이노 보드가 성공적으로 연결되었습니다.")

    # 이터레이터 설정 및 시작
    it = pyfirmata2.util.Iterator(board)
    it.start()

    # 핀 객체 설정
    button_A_pin = board.get_pin('d:7:i')  # 버튼 A (입력)
    button_B_pin = board.get_pin('d:6:i')  # 버튼 B (입력)
    led1_pin = board.get_pin('d:13:o')  # LED 1 (출력)
    led2_pin = board.get_pin('d:12:o')  # LED 2 (출력)

    # 버튼 핀들의 상태 변화를 감지하기 위해 보고 활성화
    button_A_pin.enable_reporting()
    button_B_pin.enable_reporting()

    # 각 버튼에 콜백 함수 등록
    button_A_pin.register_callback(on_button_A_change)
    button_B_pin.register_callback(on_button_B_change)

    print("💡 준비 완료. 버튼 A 또는 B를 누르세요.")
    # 프로그램 시작 시 초기 상태(mode=1)로 LED 설정
    update_leds()

    # 프로그램이 종료되지 않고 계속 실행되도록 유지
    while True:
        time.sleep(1)

except KeyboardInterrupt:
    print("\n프로그램을 종료합니다.")
except Exception as e:
    print(f"오류가 발생했습니다: {e}")

finally:
    # 프로그램 종료 시 보드 연결을 안전하게 해제
    if board is not None:
        # 종료 시 모든 LED를 끕니다.
        led1_pin.write(False)
        led2_pin.write(False)
        board.exit()
        print("🔌 아두이노 연결이 종료되었습니다.")