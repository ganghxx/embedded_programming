import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import serial
import serial.tools.list_ports
import pyautogui
import time
import numpy as np
import tensorflow as tf
from tensorflow.keras.preprocessing.sequence import pad_sequences
import joblib
import json
import os
import threading


# --- 1. 기본 설정 (설정 파일 경로는 GUI에서 관리) ---
# CONFIG_FILE 상수를 제거하고, AirMouseApp 클래스 내에서 self.config_file_path로 관리합니다.


# --- 2. 헬퍼 함수 ---
def map_value(value, from_low, from_high, to_low, to_high):
    """주어진 범위의 값을 다른 범위로 매핑합니다."""
    value = max(from_low, min(value, from_high))
    from_span = from_high - from_low
    to_span = to_high - to_low
    value_scaled = float(value - from_low) / float(from_span)
    return to_low + (value_scaled * to_span)


# --- 3. 시리얼 통신 및 머신러닝 처리를 위한 스레드 클래스 ---
class SerialProcessor(threading.Thread):
    def __init__(self, gui_app):
        super().__init__()
        self.gui = gui_app
        self.daemon = True  # 메인 스레드(GUI) 종료 시 함께 종료
        self.stop_event = threading.Event()
        self.ser = None

        # ML 모델/스케일러 관련 변수 초기화
        self.model = None
        self.scaler = None
        self.inverse_label_map = None
        self.MAX_LENGTH = None

    def load_models(self):
        """모델 및 관련 파일을 로드합니다."""
        model_path = self.gui.model_path_var.get()
        if not os.path.isdir(model_path):
            self.gui.update_status(f"오류: 모델 경로를 찾을 수 없습니다: {model_path}")
            return False

        try:
            self.gui.update_status("모델 로딩 중...")
            self.model = tf.keras.models.load_model(os.path.join(model_path, 'gesture_model.h5'))
            self.scaler = joblib.load(os.path.join(model_path, 'gesture_scaler.pkl'))

            with open(os.path.join(model_path, 'label_map.json'), 'r') as f:
                label_map = json.load(f)

            self.inverse_label_map = {v: k for k, v in label_map.items()}
            self.MAX_LENGTH = self.model.input_shape[1]
            self.gui.update_status("모델 로드 완료.")
            return True
        except Exception as e:
            self.gui.update_status(f"오류: 모델 로드 실패. {e}")
            return False

    def perform_action(self, gesture_name):
        """GUI에 설정된 제스처별 동작을 수행합니다."""
        action_string = self.gui.gesture_actions.get(gesture_name)

        if action_string:
            try:
                keys = [key.strip() for key in action_string.split('+')]
                pyautogui.hotkey(*keys)
                print(f"ACTION: '{gesture_name}' -> pyautogui.hotkey({', '.join(keys)})")
            except Exception as e:
                print(f"PyAutoGUI 동작 수행 오류: {e}")
        else:
            print(f"'{gesture_name}'에 대해 설정된 동작이 없습니다.")

    def predict_gesture(self, sequence_data, min_samples, threshold):
        """제스처를 예측하고 동작을 수행합니다."""
        if len(sequence_data) < min_samples:
            print("-> 제스처가 너무 짧아 분석하지 않습니다.")
            return

        try:
            scaled_data = self.scaler.transform(sequence_data)
            padded_data = pad_sequences([scaled_data], maxlen=self.MAX_LENGTH, dtype='float32', padding='post',
                                        truncating='post')
            prediction = self.model.predict(padded_data, verbose=0)[0]
            confidence = np.max(prediction)

            if confidence >= threshold:
                gesture_index = np.argmax(prediction)
                gesture_name = self.inverse_label_map[gesture_index]
                print(f"✅ 인식된 제스처: '{gesture_name}' (정확도: {confidence:.2f})")
                self.perform_action(gesture_name)
            else:
                print(f"-> 인식 실패 (정확도: {confidence:.2f} < {threshold})")
        except Exception as e:
            print(f"❌ 제스처 예측 중 오류 발생: {e}")

    def run(self):
        """스레드 메인 루프: 시리얼 연결 및 데이터 처리"""

        if not self.load_models():
            self.gui.on_connection_closed()
            return

        port = self.gui.com_port_var.get()
        baud_rate = 9600

        try:
            self.ser = serial.Serial(port, baud_rate, timeout=0.1)
            self.gui.update_status(f"'{port}'에 연결되었습니다.")
            time.sleep(2)
        except serial.SerialException as e:
            self.gui.update_status(f"오류: '{port}' 연결 실패. {e}")
            self.gui.on_connection_closed()
            return

        screenWidth, screenHeight = pyautogui.size()
        pyautogui.FAILSAFE = False
        current_x, current_y = screenWidth / 2, screenHeight / 2
        was_clicked = False
        serial_buffer = ""
        gesture_buffer = []
        is_gesturing = False

        CONFIDENCE_THRESHOLD = 0.85
        MIN_GESTURE_SAMPLES = 10

        try:
            while not self.stop_event.is_set():
                # --- GUI에서 실시간 설정 값 읽어오기 ---
                angle_range_val = self.gui.angle_range_var.get()
                ANGLE_RANGE_X = [-angle_range_val, angle_range_val]
                ANGLE_RANGE_Y = [-angle_range_val, angle_range_val]
                SCROLL_SPEED = self.gui.scroll_speed_var.get()

                # --- 스무딩 제거: SMOOTHING_FACTOR를 1.0으로 고정 ---
                SMOOTHING_FACTOR = 1.0

                if self.ser.in_waiting > 0:
                    try:
                        serial_buffer += self.ser.read(self.ser.in_waiting).decode('utf-8', errors='ignore')
                    except Exception as e:
                        print(f"Serial read/decode error: {e}")
                        serial_buffer = ""

                last_end_index = serial_buffer.rfind('>')
                if last_end_index != -1:
                    last_start_index = serial_buffer.rfind('<', 0, last_end_index)
                    if last_start_index != -1:
                        line = serial_buffer[last_start_index + 1:last_end_index]
                        serial_buffer = serial_buffer[last_end_index + 1:]

                        try:
                            data = line.split(',')
                            packet_type = data[0]

                            # --- 제스처 모드 ---
                            if packet_type == 'G' and len(data) == 7:
                                if not is_gesturing:
                                    is_gesturing = True
                                    print("\n(제스처 모드 시작...)")
                                ax, ay, az, gx, gy, gz = map(float, data[1:])
                                gesture_buffer.append([ax, ay, az, gx, gy, gz])

                            # --- 마우스 모드 ---
                            elif packet_type == 'M' and len(data) == 5:
                                if is_gesturing:
                                    print("(제스처 모드 종료...)")
                                    is_gesturing = False
                                    self.predict_gesture(gesture_buffer, MIN_GESTURE_SAMPLES, CONFIDENCE_THRESHOLD)
                                    gesture_buffer = []

                                angle_x, angle_y, scroll, click = map(float, data[1:])

                                target_x = map_value(angle_x, ANGLE_RANGE_X[0], ANGLE_RANGE_X[1], screenWidth, 0)
                                target_y = map_value(angle_y, ANGLE_RANGE_Y[0], ANGLE_RANGE_Y[1], 0, screenHeight)

                                # 스무딩 로직: SMOOTHING_FACTOR가 1.0이므로 current = target이 됨
                                current_x = (1 - SMOOTHING_FACTOR) * current_x + SMOOTHING_FACTOR * target_x
                                current_y = (1 - SMOOTHING_FACTOR) * current_y + SMOOTHING_FACTOR * target_y

                                pyautogui.moveTo(current_x, current_y)

                                if scroll != 0:
                                    pyautogui.scroll(int(scroll) * SCROLL_SPEED)

                                is_clicked = (click == 1.0)
                                if is_clicked and not was_clicked:
                                    pyautogui.mouseDown()
                                elif not is_clicked and was_clicked:
                                    pyautogui.mouseUp()
                                was_clicked = is_clicked

                        except (ValueError, IndexError) as e:
                            print(f"Packet parsing error: {e}, Line: '{line}'")
                            pass

                time.sleep(0.005)

        except Exception as e:
            if not self.stop_event.is_set():
                self.gui.update_status(f"스레드 오류: {e}")
                print(f"스레드 실행 중 오류 발생: {e}")

        finally:
            if self.ser and self.ser.is_open:
                self.ser.close()
            print("시리얼 스레드 종료.")
            if not self.stop_event.is_set():
                self.gui.update_status("연결이 끊어졌습니다.")
                self.gui.on_connection_closed()

    def stop(self):
        """스레드를 안전하게 중지시킵니다."""
        self.stop_event.set()


# --- 4. 메인 GUI 애플리케이션 클래스 ---
class AirMouseApp(tk.Tk):
    def __init__(self):
        super().__init__()
        # self.title("에어 마우스 설정") # 제목은 update_title에서 설정
        self.geometry("450x350")

        self.serial_thread = None
        self.is_connected = False

        # --- 설정 파일 경로 변수 ---
        self.config_file_path = os.path.abspath("air_mouse_config.json")  # 기본 경로

        # --- 설정 변수 ---
        self.com_port_var = tk.StringVar()
        self.status_var = tk.StringVar(value="연결되지 않음")
        self.model_path_var = tk.StringVar(value=os.path.abspath("."))

        # 민감도
        self.angle_range_var = tk.IntVar(value=30)
        self.scroll_speed_var = tk.IntVar(value=20)
        # self.smoothing_var 제거

        # 제스처
        self.label_map = {}
        self.gesture_actions = {}
        self.selected_gesture_var = tk.StringVar()
        self.hotkey_action_var = tk.StringVar()

        # 설정 파일 로드 (GUI 생성 전 변수 초기화)
        self.load_config()

        # GUI 생성
        self.create_gui()

        # 포트 목록 갱신
        self.refresh_ports()

        # 창 제목 설정
        self.update_title()

    def update_title(self):
        """창 제목에 현재 설정 파일 경로를 표시합니다."""
        self.title(f"에어 마우스 설정 - {os.path.basename(self.config_file_path)}")

    def create_gui(self):
        # --- 메뉴바 생성 ---
        self.menu_bar = tk.Menu(self)
        self.config(menu=self.menu_bar)

        self.file_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="파일", menu=self.file_menu)
        self.file_menu.add_command(label="설정 불러오기...", command=self.load_config_from_file)
        self.file_menu.add_command(label="설정 다른 이름으로 저장...", command=self.save_config_as)
        self.file_menu.add_separator()
        self.file_menu.add_command(label="종료", command=self.on_closing)

        # --- 탭 생성 ---
        self.notebook = ttk.Notebook(self)

        self.conn_tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(self.conn_tab, text="연결")
        self.create_connection_tab()

        self.sens_tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(self.sens_tab, text="민감도")
        self.create_sensitivity_tab()

        self.gest_tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(self.gest_tab, text="제스처")
        self.create_gesture_tab()

        self.notebook.pack(expand=True, fill='both')

        # --- 하단 상태바 ---
        status_bar = ttk.Label(self, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)

    def create_connection_tab(self):
        # COM 포트
        port_frame = ttk.Frame(self.conn_tab)
        port_frame.pack(fill='x', pady=5)
        ttk.Label(port_frame, text="COM 포트:").pack(side=tk.LEFT, padx=5)
        self.port_combo = ttk.Combobox(port_frame, textvariable=self.com_port_var, state='readonly')
        self.port_combo.pack(side=tk.LEFT, fill='x', expand=True)
        ttk.Button(port_frame, text="갱신", command=self.refresh_ports).pack(side=tk.LEFT, padx=5)

        # 연결 버튼
        self.connect_button = ttk.Button(self.conn_tab, text="연결", command=self.toggle_connection)
        self.connect_button.pack(pady=20, fill='x')

    def create_sensitivity_tab(self):
        # 마우스 민감도 (Angle Range)
        sens_frame = ttk.Frame(self.sens_tab)
        sens_frame.pack(fill='x', pady=10)
        self.sens_label = ttk.Label(sens_frame, text=f"마우스 민감도 (각도 범위: ±{self.angle_range_var.get()}°)")
        self.sens_label.pack()
        sens_slider = ttk.Scale(sens_frame, from_=10, to=60, orient=tk.HORIZONTAL,
                                variable=self.angle_range_var, command=self.update_sens_label)
        sens_slider.bind("<ButtonRelease-1>", lambda e: self.save_config())
        sens_slider.pack(fill='x', expand=True)
        ttk.Label(sens_frame, text="(값이 작을수록 민감함)").pack()

        # 스크롤 속도
        scroll_frame = ttk.Frame(self.sens_tab)
        scroll_frame.pack(fill='x', pady=10)
        ttk.Label(scroll_frame, text=f"스크롤 속도").pack()
        scroll_slider = ttk.Scale(scroll_frame, from_=1, to=100, orient=tk.HORIZONTAL,
                                  variable=self.scroll_speed_var, command=lambda e: self.save_config(True))
        scroll_slider.bind("<ButtonRelease-1>", lambda e: self.save_config())
        scroll_slider.pack(fill='x', expand=True)

        # --- 마우스 부드러움 UI 제거 ---
        # smooth_frame = ttk.Frame(self.sens_tab)
        # ...

    def create_gesture_tab(self):
        # --- 제스처 폴더 ---
        path_frame = ttk.Frame(self.gest_tab)
        path_frame.pack(fill='x', pady=5)
        ttk.Label(path_frame, text="제스처 폴더:").pack(side=tk.LEFT, padx=5)
        ttk.Entry(path_frame, textvariable=self.model_path_var, width=40).pack(side=tk.LEFT, fill='x', expand=True)
        ttk.Button(path_frame, text="찾기", command=self.browse_model_path).pack(side=tk.LEFT, padx=5)

        # --- 기존 제스처 탭 내용 ---
        main_frame = ttk.Frame(self.gest_tab)
        main_frame.pack(fill='both', expand=True, pady=5)

        # 왼쪽: 제스처 목록
        left_frame = ttk.Frame(main_frame)
        left_frame.pack(side=tk.LEFT, fill='y', padx=5)

        ttk.Label(left_frame, text="감지된 제스처:").pack(anchor='w')
        self.gesture_listbox = tk.Listbox(left_frame, exportselection=False, height=10)
        self.gesture_listbox.pack(fill='y', expand=True)
        self.gesture_listbox.bind('<<ListboxSelect>>', self.on_gesture_select)

        # 오른쪽: 동작 설정
        right_frame = ttk.Frame(main_frame)
        right_frame.pack(side=tk.LEFT, fill='both', expand=True, padx=5)

        ttk.Button(right_frame, text="제스처 목록 불러오기", command=self.load_gesture_list).pack(fill='x', pady=5)
        ttk.Label(right_frame, text="선택된 제스처:").pack(anchor='w')
        ttk.Entry(right_frame, textvariable=self.selected_gesture_var, state='readonly').pack(fill='x')
        ttk.Label(right_frame, text="수행할 동작 (예: Ctrl+C, Alt+Left):").pack(anchor='w', pady=(10, 0))
        ttk.Entry(right_frame, textvariable=self.hotkey_action_var).pack(fill='x')
        ttk.Button(right_frame, text="동작 저장", command=self.save_gesture_action).pack(fill='x', pady=10)

        # 제스처 목록 로드 시도
        self.load_gesture_list()

    # --- GUI 콜백 함수 ---

    def browse_model_path(self):
        path = filedialog.askdirectory(title="모델이 있는 폴더를 선택하세요")
        if path:
            self.model_path_var.set(path)
            self.save_config()
            self.load_gesture_list()

    def refresh_ports(self):
        ports = [port.device for port in serial.tools.list_ports.comports()]
        self.port_combo['values'] = ports
        if ports:
            saved_port = self.com_port_var.get()
            if saved_port in ports:
                self.port_combo.set(saved_port)
            else:
                self.port_combo.set(ports[0])
        else:
            self.com_port_var.set("")

    def update_sens_label(self, value):
        val = int(float(value))
        self.sens_label.config(text=f"마우스 민감도 (각도 범위: ±{val}°)")

    # def update_smooth_label(self, value): # 제거
    #     ...

    def load_gesture_list(self):
        """MODEL_PATH에서 label_map.json을 읽어 제스처 목록을 채웁니다."""
        model_path = self.model_path_var.get()
        label_map_file = os.path.join(model_path, 'label_map.json')

        try:
            with open(label_map_file, 'r') as f:
                self.label_map = json.load(f)

            self.gesture_listbox.delete(0, tk.END)
            for gesture_name in sorted(self.label_map.keys()):
                self.gesture_listbox.insert(tk.END, gesture_name)

            # 목록을 새로고침했으므로, 선택된 제스처의 핫키도 다시 표시
            self.on_gesture_select(None)

            self.update_status("제스처 목록 로드 완료.")
        except Exception as e:
            self.update_status(f"label_map.json 로드 실패: {e}")
            self.gesture_listbox.delete(0, tk.END)

    def on_gesture_select(self, event):
        """제스처 목록에서 항목 선택 시 호출됩니다."""
        try:
            selected_index_tuple = self.gesture_listbox.curselection()
            if not selected_index_tuple:  # 선택된 항목이 없으면 (예: 목록 새로고침 시)
                self.selected_gesture_var.set("")
                self.hotkey_action_var.set("")
                return

            selected_index = selected_index_tuple[0]
            selected_gesture = self.gesture_listbox.get(selected_index)

            self.selected_gesture_var.set(selected_gesture)

            action = self.gesture_actions.get(selected_gesture, "")
            self.hotkey_action_var.set(action)

        except IndexError:
            pass

    def save_gesture_action(self):
        """현재 제스처에 대한 동작을 저장합니다."""
        gesture_name = self.selected_gesture_var.get()
        action_string = self.hotkey_action_var.get()

        if not gesture_name:
            messagebox.showwarning("저장 오류", "먼저 제스처를 선택하세요.")
            return

        self.gesture_actions[gesture_name] = action_string
        self.save_config()
        messagebox.showinfo("저장 완료", f"'{gesture_name}'에 대한 동작이 저장되었습니다.")

    # --- 연결 관리 ---
    def toggle_connection(self):
        if self.is_connected:
            if self.serial_thread:
                self.serial_thread.stop()
                self.serial_thread.join(timeout=2)

            self.is_connected = False
            self.connect_button.config(text="연결")
            self.update_status("연결 해제됨")
            self.port_combo.config(state='readonly')
            self.notebook.tab(self.sens_tab, state='normal')
        else:
            port = self.com_port_var.get()
            if not port:
                messagebox.showwarning("연결 오류", "COM 포트를 선택하세요.")
                return

            # 모델 폴더(제스처 폴더)가 유효한지 먼저 확인
            model_path = self.model_path_var.get()
            if not os.path.isdir(model_path) or not os.path.exists(os.path.join(model_path, 'gesture_model.h5')):
                messagebox.showwarning("연결 오류", f"유효한 제스처 폴더를 선택하세요.\n(gesture_model.h5 파일을 찾을 수 없음)")
                return

            self.is_connected = True
            self.connect_button.config(text="연결 해제")
            self.update_status("연결 중...")
            self.port_combo.config(state='disabled')
            self.notebook.tab(self.sens_tab, state='disabled')

            self.serial_thread = SerialProcessor(self)
            self.serial_thread.start()

    def update_status(self, message):
        """스레드-안전(thread-safe)하게 상태 메시지를 업데이트합니다."""
        self.after(0, self.status_var.set, message)

    def on_connection_closed(self):
        """스레드가 (오류 등으로) 종료되었을 때 GUI를 리셋합니다."""

        def reset_gui():
            self.is_connected = False
            self.connect_button.config(text="연결")
            self.port_combo.config(state='readonly')
            self.notebook.tab(self.sens_tab, state='normal')

        self.after(0, reset_gui)

    # --- 설정 저장/로드 (파일 경로 관리 기능 추가) ---

    def load_config_from_file(self):
        """파일 대화상자를 열어 설정 파일을 불러옵니다."""
        filepath = filedialog.askopenfilename(
            title="설정 파일 선택",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if filepath:
            self.load_config(filepath)
            # 새 설정 로드 후 COM 포트 목록 갱신 (저장된 포트가 선택되도록)
            self.refresh_ports()
            # 제스처 목록 및 핫키 설정 갱신
            self.load_gesture_list()

    def save_config_as(self):
        """파일 대화상자를 열어 설정을 다른 이름으로 저장합니다."""
        filepath = filedialog.asksaveasfilename(
            title="설정 파일 저장",
            initialfile=os.path.basename(self.config_file_path),
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if filepath:
            if not filepath.endswith('.json'):
                filepath += '.json'
            self.config_file_path = os.path.abspath(filepath)  # 새 경로를 기본 경로로 설정
            self.save_config()  # 새 경로에 저장
            self.update_title()  # 제목 업데이트
            messagebox.showinfo("저장 완료", f"설정이 다음 파일에 저장되었습니다:\n{filepath}")

    def load_config(self, filepath=None):
        """지정된 경로(없으면 기본 경로)에서 설정을 로드합니다."""
        load_path = filepath if filepath else self.config_file_path

        try:
            if os.path.exists(load_path):
                with open(load_path, 'r') as f:
                    config = json.load(f)

                self.com_port_var.set(config.get('com_port', ''))
                self.model_path_var.set(config.get('model_path', os.path.abspath(".")))
                self.angle_range_var.set(config.get('angle_range', 30))
                self.scroll_speed_var.set(config.get('scroll_speed', 20))
                # self.smoothing_var.set(...) # 제거됨
                self.gesture_actions = config.get('gesture_actions', {})

                # 성공적으로 로드한 경우에만 경로 업데이트
                self.config_file_path = os.path.abspath(load_path)
                if hasattr(self, 'notebook'):  # GUI가 생성된 후에만 제목 업데이트
                    self.update_title()

        except Exception as e:
            print(f"설정 파일 로드 오류: {e}")
            self.gesture_actions = {}

    def save_config(self, from_scroll=False, filepath=None):
        """현재 설정을 지정된 경로(없으면 기본 경로)에 저장합니다."""
        save_path = filepath if filepath else self.config_file_path

        if from_scroll and self.is_connected:
            return

        config = {
            'com_port': self.com_port_var.get(),
            'model_path': self.model_path_var.get(),
            'angle_range': self.angle_range_var.get(),
            'scroll_speed': self.scroll_speed_var.get(),
            # 'smoothing': ... # 제거됨
            'gesture_actions': self.gesture_actions
        }

        try:
            with open(save_path, 'w') as f:
                json.dump(config, f, indent=4)
        except Exception as e:
            print(f"설정 파일 저장 오류: {e}")

    def on_closing(self):
        """프로그램 종료 시 호출됩니다."""
        self.save_config()  # 종료 직전 현재 경로에 최종 설정 저장
        if self.is_connected and self.serial_thread:
            self.serial_thread.stop()
            self.serial_thread.join(timeout=1)
        self.destroy()


# --- 5. 애플리케이션 실행 ---
if __name__ == "__main__":
    app = AirMouseApp()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()