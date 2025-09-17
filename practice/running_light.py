import pyfirmata2
import time

# --- 설정 상수 ---
PORT = pyfirmata2.Arduino.AUTODETECT
NUM_LEDS = 4  # 전체 LED 개수

# --- 전역 변수 ---
board = None
led_pins = []  # LED 핀 객체 리스트
# 현재 켜져 있는 LED의 인덱스 (0, 1, 2, 3)
current_led_index = 0


def update_leds():
    """
    모든 LED를 끈 뒤, 'current_led_index'에 해당하는 LED만 켭니다.
    """
    # 1. 모든 LED를 먼저 끈다.
    for pin in led_pins:
        pin.write(False)

    # 2. 현재 인덱스에 해당하는 LED만 켠다.
    led_pins[current_led_index].write(True)

    print(f"🔦 LED #{current_led_index + 1} ON")


def on_button_press(state):
    """
    버튼 상태가 변할 때 호출되는 콜백 함수.
    state가 True일 때 (눌리는 순간)에만 동작합니다.
    """
    # 'state'가 True일 때, 즉 버튼이 눌렸을 때만 로직을 실행 (엣지 검출)
    if state:
        global current_led_index
        # 인덱스를 1 증가시키고, LED 개수로 나눈 나머지를 취해 순환시킴 (모듈러 연산)
        # 예: (3 + 1) % 4 = 0, (0 + 1) % 4 = 1
        current_led_index = (current_led_index + 1) % NUM_LEDS

        # 변경된 인덱스로 LED 상태를 업데이트
        update_leds()


# --- 메인 실행 블록 ---
try:
    # 아두이노 보드와 연결
    board = pyfirmata2.Arduino(PORT)
    print("✅ 아두이노 보드가 성공적으로 연결되었습니다.")

    # 이터레이터 설정 및 시작
    it = pyfirmata2.util.Iterator(board)
    it.start()

    # 핀 객체 설정
    led_pins = [
        board.get_pin('d:13:o'),  # LED 1 (index 0)
        board.get_pin('d:12:o'),  # LED 2 (index 1)
        board.get_pin('d:11:o'),  # LED 3 (index 2)
        board.get_pin('d:10:o')  # LED 4 (index 3)
    ]
    button = board.get_pin('d:7:i')

    # 버튼 핀의 상태 보고 활성화
    button.enable_reporting()

    # 버튼에 콜백 함수 등록
    button.register_callback(on_button_press)

    print("💡 준비 완료. 버튼을 눌러 LED를 순차적으로 점등하세요.")
    # 프로그램 시작 시 초기 상태(첫 번째 LED)로 설정
    update_leds()

    # 프로그램이 종료되지 않도록 유지
    while True:
        time.sleep(1)

except KeyboardInterrupt:
    print("\n프로그램을 종료합니다.")
except Exception as e:
    print(f"오류가 발생했습니다: {e}")

finally:
    # 프로그램 종료 시 보드 연결을 안전하게 해제
    if board is not None:
        for pin in led_pins:
            pin.write(False)  # 모든 LED 끄기
        board.exit()
        print("🔌 아두이노 연결이 종료되었습니다.")