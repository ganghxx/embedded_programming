import pyfirmata2
import time

# --- 설정 상수 ---
PORT = pyfirmata2.Arduino.AUTODETECT

# --- 전역 변수 ---
board = None
# 각 LED의 켜짐(True)/꺼짐(False) 상태를 저장하는 리스트
led_states = [False, False, False]
led_pins = []


# --- 콜백 함수 정의 ---
def toggle_led(index):
    """지정된 인덱스의 LED 상태를 토글하는 함수"""
    # 현재 상태를 반전시킴 (False -> True, True -> False)
    led_states[index] = not led_states[index]

    # 반전된 상태를 실제 LED 핀에 적용
    led_pins[index].write(led_states[index])

    # 현재 상태를 콘솔에 출력
    state_text = "ON" if led_states[index] else "OFF"
    print(f"LED #{index + 1} turned {state_text}")


# 각 버튼에 대한 콜백 함수
# 버튼이 눌리는 순간(state=True)에만 toggle_led 함수를 호출합니다.
def on_button1_change(state):
    if state:
        toggle_led(0)  # LED 1 (인덱스 0)


def on_button2_change(state):
    if state:
        toggle_led(1)  # LED 2 (인덱스 1)


def on_button3_change(state):
    if state:
        toggle_led(2)  # LED 3 (인덱스 2)


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
        board.get_pin('d:13:o'),  # LED 1
        board.get_pin('d:12:o'),  # LED 2
        board.get_pin('d:11:o')  # LED 3
    ]
    button1 = board.get_pin('d:7:i')
    button2 = board.get_pin('d:6:i')
    button3 = board.get_pin('d:5:i')

    # 버튼 핀들의 상태 보고 활성화
    button1.enable_reporting()
    button2.enable_reporting()
    button3.enable_reporting()

    # 각 버튼에 콜백 함수 등록
    button1.register_callback(on_button1_change)
    button2.register_callback(on_button2_change)
    button3.register_callback(on_button3_change)

    print("💡 준비 완료. 각 버튼을 눌러 해당 LED를 토글하세요.")

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