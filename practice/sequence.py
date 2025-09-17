import pyfirmata2
import time
from collections import deque

# --- 설정 상수 ---
PORT = pyfirmata2.Arduino.AUTODETECT
SECRET_SEQUENCE = [1, 3, 2]  # 정답 순서 (버튼 1 -> 버튼 3 -> 버튼 2)

# --- 전역 변수 ---
board = None
led_pins = []  # LED 핀 객체들을 담을 리스트
# 최근 3개의 입력만 저장하는 버퍼 (큐)
input_buffer = deque(maxlen=3)


# --- 피드백 함수 ---
def success_feedback():
    """정답일 때의 피드백: 모든 LED를 2초간 켠다."""
    print("✅ 정답입니다! 2초간 모든 LED가 켜집니다.")
    for pin in led_pins:
        pin.write(True)
    time.sleep(2)
    for pin in led_pins:
        pin.write(False)


def error_feedback():
    """오답일 때의 피드백: 모든 LED를 200ms 간격으로 2번 깜빡인다."""
    print("❌ 틀렸습니다! 버퍼가 초기화됩니다.")
    for _ in range(2):
        for pin in led_pins:
            pin.write(True)
        time.sleep(0.2)
        for pin in led_pins:
            pin.write(False)
        time.sleep(0.2)


# --- 핵심 로직 함수 ---
def handle_button_press(button_number):
    """
    버튼이 눌렸을 때 호출되어 입력 버퍼를 관리하고 정답을 확인합니다.
    """
    # 입력 버퍼에 버튼 번호 추가
    input_buffer.append(button_number)
    print(f"입력: {button_number} | 현재 버퍼: {list(input_buffer)}")

    # 버퍼가 꽉 찼는지 확인 (입력이 3번 되었는지)
    if len(input_buffer) == 3:
        # 버퍼의 내용과 정답 시퀀스를 비교
        if list(input_buffer) == SECRET_SEQUENCE:
            success_feedback()
        else:
            error_feedback()

        # 정답/오답 처리 후 버퍼 초기화
        input_buffer.clear()


# --- 콜백 함수 정의 ---
# 각 콜백은 버튼이 눌리는 순간(state=True)에만 handle_button_press 함수를 호출합니다.
def on_button1_change(state):
    if state: handle_button_press(1)


def on_button2_change(state):
    if state: handle_button_press(2)


def on_button3_change(state):
    if state: handle_button_press(3)


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
    button1 = board.get_pin('d:7:i')  # 버튼 1
    button2 = board.get_pin('d:6:i')  # 버튼 2
    button3 = board.get_pin('d:5:i')  # 버튼 3

    # 버튼 핀들의 상태 보고 활성화
    button1.enable_reporting()
    button2.enable_reporting()
    button3.enable_reporting()

    # 각 버튼에 콜백 함수 등록
    button1.register_callback(on_button1_change)
    button2.register_callback(on_button2_change)
    button3.register_callback(on_button3_change)

    print(f"💡 준비 완료. 비밀 순서({SECRET_SEQUENCE})를 입력하세요.")

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