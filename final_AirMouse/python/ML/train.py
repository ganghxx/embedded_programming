# 파일명: train_model.py

import os
import numpy as np
import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout, BatchNormalization
from tensorflow.keras.callbacks import EarlyStopping, ModelCheckpoint
import matplotlib.pyplot as plt

# --- 📌 설정 ---

# 1. 전처리된 데이터가 있는 폴더
PROCESSED_DATA_DIR = "D:\\embed\\final\\processed_data"

# 2. 학습된 모델을 저장할 경로와 이름
MODEL_SAVE_PATH = "D:\\embed\\final\\gesture_model.h5"

# 3. 학습 하이퍼파라미터
EPOCHS = 100  # 총 학습 횟수 (에포크)
BATCH_SIZE = 32  # 한 번에 학습할 데이터 개수 (배치 크기)
VALIDATION_SPLIT = 0.2  # (참고) X_test, y_test를 사용하므로 여기서는 0.0


# -----------------

def load_data(data_dir):
    """
    processed_data 폴더에서 .npy 파일들을 로드합니다.
    """
    print(f"'{data_dir}'에서 전처리된 데이터 로드 중...")
    try:
        X_train = np.load(os.path.join(data_dir, 'X_train.npy'))
        y_train = np.load(os.path.join(data_dir, 'y_train.npy'))
        X_test = np.load(os.path.join(data_dir, 'X_test.npy'))
        y_test = np.load(os.path.join(data_dir, 'y_test.npy'))

        print("데이터 로드 완료.")
        print(f"  - X_train shape: {X_train.shape}")
        print(f"  - y_train shape: {y_train.shape}")
        print(f"  - X_test shape: {X_test.shape}")
        print(f"  - y_test shape: {y_test.shape}")

        return X_train, y_train, X_test, y_test

    except FileNotFoundError as e:
        print(f"[오류] 데이터 파일을 찾을 수 없습니다: {e}")
        print("preprocess_data.py를 먼저 실행했는지 확인하세요.")
        return None, None, None, None
    except Exception as e:
        print(f"[오류] 데이터 로드 중 문제 발생: {e}")
        return None, None, None, None


def build_model(input_shape, num_classes):
    """
    LSTM 모델을 정의합니다.
    input_shape: (TIMESTEPS, NUM_FEATURES)
    num_classes: 분류할 제스처의 총 개수
    """
    model = Sequential()

    # 입력층 (LSTM)
    # return_sequences=True: 다음 LSTM 층이 있다면 True
    model.add(LSTM(64, return_sequences=True, input_shape=input_shape))
    model.add(Dropout(0.3))  # 과적합 방지를 위한 드롭아웃

    # 두 번째 LSTM 층
    model.add(LSTM(64, return_sequences=False))  # 마지막 LSTM 층은 False
    model.add(Dropout(0.3))

    # (선택적) 완전 연결층 (Dense)
    model.add(Dense(32, activation='relu'))
    model.add(BatchNormalization())  # 배치 정규화

    # 출력층
    # num_classes 만큼의 노드로 분류, softmax로 확률 출력
    model.add(Dense(num_classes, activation='softmax'))

    print("\n모델 구성 완료:")
    model.summary()
    return model


def plot_history(history):
    """
    모델 학습 과정(정확도, 손실)을 그래프로 시각화합니다.
    """
    plt.figure(figsize=(12, 5))

    # 1. 정확도 그래프
    plt.subplot(1, 2, 1)
    plt.plot(history.history['accuracy'], label='Training Accuracy')
    plt.plot(history.history['val_accuracy'], label='Validation Accuracy')
    plt.title('Training and Validation Accuracy')
    plt.xlabel('Epochs')
    plt.ylabel('Accuracy')
    plt.legend()

    # 2. 손실 그래프
    plt.subplot(1, 2, 2)
    plt.plot(history.history['loss'], label='Training Loss')
    plt.plot(history.history['val_loss'], label='Validation Loss')
    plt.title('Training and Validation Loss')
    plt.xlabel('Epochs')
    plt.ylabel('Loss')
    plt.legend()

    plt.tight_layout()
    plt.show()


def main():
    # 1. 데이터 로드
    X_train, y_train, X_test, y_test = load_data(PROCESSED_DATA_DIR)
    if X_train is None:
        return

    # 2. 모델 파라미터 자동 설정
    # X_train.shape = (데이터개수, TIMESTEPS, NUM_FEATURES)
    # y_train.shape = (데이터개수, NUM_CLASSES)
    try:
        timesteps = X_train.shape[1]
        num_features = X_train.shape[2]
        num_classes = y_train.shape[1]

        input_shape = (timesteps, num_features)

        print(f"\n모델 파라미터 확인:")
        print(f"  - TIMESTEPS (윈도우 크기): {timesteps}")
        print(f"  - NUM_FEATURES (센서 축): {num_features}")
        print(f"  - NUM_CLASSES (제스처 개수): {num_classes}")

    except IndexError as e:
        print(f"[오류] 데이터 형태(shape)가 올바르지 않습니다: {e}")
        print("  - X 데이터가 3차원(samples, timesteps, features)인지 확인하세요.")
        return
    except Exception as e:
        print(f"[오류] 파라미터 설정 중 문제 발생: {e}")
        return

    # 3. 모델 빌드
    model = build_model(input_shape, num_classes)

    # 4. 모델 컴파일
    #    loss: 'categorical_crossentropy' (원-핫 인코딩된 다중 분류)
    model.compile(optimizer='adam',
                  loss='categorical_crossentropy',
                  metrics=['accuracy'])

    # 5. 콜백(Callbacks) 설정
    #    - EarlyStopping: 검증 손실(val_loss)이 5번 연속 개선되지 않으면 학습 조기 종료
    early_stop = EarlyStopping(monitor='val_loss', patience=10, restore_best_weights=True)

    #    - ModelCheckpoint: 검증 정확도(val_accuracy)가 가장 높은 모델만 저장
    model_check = ModelCheckpoint(filepath=MODEL_SAVE_PATH,
                                  monitor='val_accuracy',
                                  save_best_only=True,
                                  verbose=1)

    print("\n모델 학습을 시작합니다...")

    # 6. 모델 학습
    history = model.fit(
        X_train, y_train,
        epochs=EPOCHS,
        batch_size=BATCH_SIZE,
        validation_data=(X_test, y_test),  # 테스트 데이터로 검증
        callbacks=[early_stop, model_check]
    )

    print("\n모델 학습 완료.")

    # 7. (선택적) 최종 모델 평가 (가장 성능이 좋았던 모델 기준)
    # ModelCheckpoint의 restore_best_weights=True로 인해
    # model 객체는 이미 최상의 가중치를 가지고 있음
    print("\n저장된 최적 모델로 최종 평가:")
    test_loss, test_acc = model.evaluate(X_test, y_test, verbose=0)
    print(f"  - 테스트 손실 (Test Loss): {test_loss:.4f}")
    print(f"  - 테스트 정확도 (Test Accuracy): {test_acc * 100:.2f} %")

    print(f"\n🎉 최적 모델이 '{MODEL_SAVE_PATH}'에 저장되었습니다.")

    # 8. 학습 과정 시각화
    print("학습 과정 그래프를 표시합니다...")
    plot_history(history)


if __name__ == '__main__':
    main()