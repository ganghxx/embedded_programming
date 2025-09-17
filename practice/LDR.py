import pyfirmata2
import time

try:
    # 포트를 자동으로 찾아 아두이노와 연결합니다.
    board = pyfirmata2.Arduino(pyfirmata2.Arduino.AUTODETECT)
    print("✅ 아두이노 보드에 성공적으로 연결되었습니다.")

    # 제어할 디지털 13번 핀을 출력(output) 모드로 미리 설정합니다.
    led_pin = board.get_pin('d:13:o')


    def process_and_control_led(data):
        """
        아날로그 핀 데이터 수신 시 호출되는 콜백 함수입니다.
        데이터가 0.6을 초과하면 LED를 켜고, 그렇지 않으면 끕니다.
        이 함수는 try 블록 내에 있어 외부의 led_pin 변수에 접근할 수 있습니다.
        """
        # 아날로그 값을 0 또는 1 (LED 상태)로 변환합니다.
        led_state = 1 if data > 0.6 else 0

        # 현재 상태를 출력합니다.
        status_text = "ON" if led_state else "OFF"
        print(f"A0 핀 원본 값: {data:.4f} -> LED 상태: {status_text}")

        # 계산된 상태(0 또는 1)를 LED 핀에 씁니다.
        led_pin.write(led_state)


    # 아날로그 0번 핀(A0)에 위에서 정의한 콜백 함수를 등록합니다.
    board.analog[0].register_callback(process_and_control_led)

    # A0 핀의 데이터 리포팅을 활성화합니다.
    board.analog[0].enable_reporting()

    # 백그라운드에서 100ms 간격으로 데이터 샘플링을 시작합니다.
    board.samplingOn(100)

    print("🚀 10초 동안 A0 핀 값에 따라 LED를 제어합니다.")

    # 메인 프로그램은 10초 동안 대기합니다.
    time.sleep(100)

    print("\n측정이 종료되었습니다.")

# 사용자가 Ctrl+C를 눌러 프로그램을 중단하려고 할 때 실행됩니다.
except KeyboardInterrupt:
    print("\n👋 프로그램을 중단합니다.")
except Exception as e:
    # 아두이노 연결 실패 등 다른 예외 처리
    print(f"❌ 오류가 발생했습니다: {e}")

# 프로그램이 어떤 이유로든 종료될 때 항상 실행됩니다.
finally:
    print("보드와의 연결을 종료합니다.")
    # 'board' 변수가 생성되었는지 확인 후 안전하게 연결을 종료합니다.
    if 'board' in locals():
        # 프로그램을 종료하기 전에 LED를 끕니다.
        led_pin.write(0)
        board.exit()

print("완료되었습니다.")

