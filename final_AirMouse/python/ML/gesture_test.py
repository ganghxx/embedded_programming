# 파일명: live_predict_manual.py

import serial
import time
import numpy as np
import tensorflow as tf
import joblib  # Scaler를 로드하기 위함
import keyboard  # 키보드 입력을 위한 라이브S러리

# --- 📌 설정 (train_model.py, preprocess_data.py와 동일하게) ---

# 1. 시리얼 포트 설정
COM_PORT = 'COM3'
BAUD_RATE = 9600

# 2. 모델 및 스케일러 파일 경로
MODEL_FILE = "D:\\embed\\final\\gesture_model.h5"
SCALER_FILE = "D:\\embed\\final\\processed_data\\sensor_scaler.pkl"

# 3. 제스처 레이블 정의 (!!! 순서와 내용이 반드시 동일해야 함 !!!)seseseseseseseseseseseseseesese
GESTURE_LABELS = {
    "updown": 0,
    "swipe": 1,
    # (추가한 제스처가 있다면 여기에 계속 정의)
}
GESTURE_MAP = {v: k for k, v in GESTURE_LABELS.items()}

# 4. 추론 설정
# PREDICTION_THRESHOLD: 예측 확률이 이 값(예: 80%) 이상일 때만 제스처로 인정
PREDICTION_THRESHOLD = 0.80


# --------------------------------------------------

def analyze_gesture_buffer(buffer, model, scaler, timesteps, step_size):
    """
    's'부터 'e'까지 수집된 전체 버퍼(시퀀스)를 분석하여
    하나의 제스처로 예측합니다.
    """

    # 1. 수집된 데이터가 너무 짧은지 확인
    #    (최소 1개의 윈도우(TIMESTEPS)는 만들 수 있어야 함)
    if len(buffer) < timesteps:
        print(f"[분석 실패] 제스처가 너무 짧습니다. (최소 {timesteps}개 필요, {len(buffer)}개 수집됨)")
        return None, 0

    print(f"\n... {len(buffer)}개 데이터 분석 중 ...")

    # 2. 버퍼 전체를 스케일링
    try:
        data_array = np.array(buffer)
        data_scaled = scaler.transform(data_array)
    except Exception as e:
        print(f"[분석 실패] 데이터 스케일링 오류: {e}")
        return None, 0

    # 3. 📌 핵심: 전체 시퀀스에서 (학습 때와 동일하게) 윈도우들을 추출
    windows = []
    for i in range(0, len(data_scaled) - timesteps + 1, step_size):
        window = data_scaled[i: i + timesteps]
        windows.append(window)

    if not windows:
        # 이 경우는 1번에서 걸러지지만, 안전장치로 둠
        print("[분석 실패] 윈도우를 생성할 수 없습니다.")
        return None, 0

    # 4. 모든 윈도우를 하나의 배치로 만들어 모델 예측
    batch_input = np.array(windows)
    # (예: 100개 데이터 -> (N, 50, 6) 형태의 윈도우 배치 생성)
    predictions = model.predict(batch_input)

    # 5. 📌 핵심: 모든 윈도우의 예측 확률을 평균냄
    #    (예: [0.1, 0.8, 0.1], [0.0, 0.9, 0.1] -> [0.05, 0.85, 0.1])
    avg_prediction = np.mean(predictions, axis=0)

    # 6. 최종 평균 확률로 제스처 결정
    max_prob = np.max(avg_prediction)
    pred_index = np.argmax(avg_prediction)
    gesture_name = GESTURE_MAP.get(pred_index, "UNKNOWN")

    return gesture_name, max_prob


def main():
    print("실시간 제스처 인식(수동 모드)을 시작합니다...")

    # 1. 모델 로드
    print(f"'{MODEL_FILE}' 모델 로드 중...")
    try:
        model = tf.keras.models.load_model(MODEL_FILE)
        TIMESTEPS = model.input_shape[1]
        NUM_FEATURES = model.input_shape[2]
        # 📌 윈도우 이동 간격 (preprocess_data.py와 동일하게 설정)
        STEP_SIZE = TIMESTEPS // 2
        print(f"모델 로드 완료. (Input Shape: ({TIMESTEPS}, {NUM_FEATURES}))")
    except Exception as e:
        print(f"[오류] 모델 로드 실패: {e}")
        return

    # 2. 스케일러 로드
    print(f"'{SCALER_FILE}' 스케일러 로드 중...")
    try:
        scaler = joblib.load(SCALER_FILE)
        print("스케일러 로드 완료.")
    except FileNotFoundError:
        print(f"[오류] 스케일러 파일을 찾을 수 없습니다. (경로: {SCALER_FILE})")
        return

    # 3. 시리얼 포트 연결
    try:
        ser = serial.Serial(COM_PORT, BAUD_RATE, timeout=0.1)
        print(f"'{COM_PORT}' 포트 연결됨. 2초 후 시작...")
        time.sleep(2)
    except serial.SerialException as e:
        print(f"오류: '{COM_PORT}' 포트에 연결할 수 없습니다. \n{e}")
        return

    # 4. 실시간 추론 루프
    serial_buffer = ""
    gesture_buffer = []  # 📌 데이터를 담을 리스트 (deque 아님)
    is_recording = False

    print("\n" + "=" * 50)
    print("       's' 키를 눌러 녹화를 시작하세요.")
    print("       'e' 키를 눌러 녹화를 중지하고 분석합니다.")
    print("       (Ctrl+C로 프로그램 종료)")
    print("=" * 50)

    while True:
        try:
            # --- 키보드 입력 감지 ---

            # 's' 키: 녹화 시작
            if keyboard.is_pressed('s') and not is_recording:
                is_recording = True
                gesture_buffer = []  # 버퍼 초기화
                print("\n▶️  녹화 시작! 제스처를 수행하세요...")
                time.sleep(0.2)  # 키 중복 입력 방지

            # 'e' 키: 녹화 중지 및 분석
            if keyboard.is_pressed('e') and is_recording:
                is_recording = False
                print(f"\n⏹️  녹화 중지. {len(gesture_buffer)}개 데이터 수집 완료.")

                # 📌 분석 함수 호출
                gesture_name, gesture_prob = analyze_gesture_buffer(
                    gesture_buffer, model, scaler, TIMESTEPS, STEP_SIZE
                )

                if gesture_name:
                    if gesture_prob >= PREDICTION_THRESHOLD:
                        print("\n" + "*" * 30)
                        print(f"  [최종 예측] ==> {gesture_name.upper()}")
                        print(f"  (신뢰도: {gesture_prob * 100:.1f}%)")
                        print("*" * 30 + "\n")
                    else:
                        print(f"\n  [예측 실패] ==> {gesture_name} (신뢰도 낮음: {gesture_prob * 100:.1f}%)")

                print("\n's' 키를 눌러 다음 녹화를 시작하세요...")
                time.sleep(0.2)  # 키 중복 입력 방지

            # --- 시리얼 데이터 수신 ---
            if ser.in_waiting > 0:
                serial_buffer += ser.read(ser.in_waiting).decode('utf-8', errors='ignore')

            end_idx = serial_buffer.rfind('>')
            if end_idx != -1:
                start_idx = serial_buffer.rfind('<', 0, end_idx)
                if start_idx != -1:
                    line = serial_buffer[start_idx + 1:end_idx]
                    serial_buffer = serial_buffer[end_idx + 1:]

                    if line.startswith('G,') and len(line.split(',')) == (NUM_FEATURES + 1):
                        # 📌 녹화 중일 때만 데이터 저장
                        if is_recording:
                            try:
                                parts = line.split(',')[1:]
                                raw_data = [float(p) for p in parts]
                                gesture_buffer.append(raw_data)
                                # (녹화 중임을 시각적으로 표시)
                                print(".", end="", flush=True)
                            except ValueError:
                                pass  # 파싱 오류 무시

            time.sleep(0.005)  # CPU 사용량 조절

        except KeyboardInterrupt:
            print("\n프로그램을 종료합니다.")
            break
        except Exception as e:
            print(f"오류 발생: {e}")
            break

    if ser.is_open:
        ser.close()
        print("시리얼 포트 연결을 해제했습니다.")


if __name__ == '__main__':
    main()