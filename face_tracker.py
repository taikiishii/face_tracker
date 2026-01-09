#!/usr/bin/env python3
"""
両目検知プログラム - MediaPipe Face Mesh使用
ラズベリーパイ5用 + STS3215サーボ制御
"""

import cv2
import mediapipe as mp
import numpy as np
import argparse
import time
import math
from st3215 import ST3215


class ServoController:
    """STS3215サーボモーター制御クラス"""
    
    # サーボID定義
    PAN_SERVO_ID = 1    # パン（左右）
    ROLL_SERVO_ID = 2   # ロール（回転）
    TILT_SERVO_ID = 3   # チルト（上下）
    
    # 位置定義（STS3215は0-4095、中心は2048）
    CENTER_POSITION = 2048
    
    # 角度範囲（±50度 = ±568 steps、STS3215は1 step = 0.088度）
    ANGLE_RANGE = 568  # 50度 / 0.088度 ≈ 568 steps
    
    def __init__(self, port='/dev/ttyACM0', baudrate=1000000, enable_servo=True):
        """
        Args:
            port: シリアルポート
            baudrate: ボーレート
            enable_servo: サーボを有効化するか（Falseの場合、動作確認用）
        """
        self.enable_servo = enable_servo
        self.servo = None
        
        # 累積オフセット（虹彩を中央に保つための位置）
        self.pan_cumulative_offset = 0
        self.tilt_cumulative_offset = 0
        self.roll_cumulative_offset = 0
        
        if self.enable_servo:
            try:
                self.servo = ST3215(port)
                print(f"サーボコントローラー初期化成功: {port}")
                
                # サーボ検出
                servo_ids = self.servo.ListServos()
                if servo_ids:
                    print(f"検出されたサーボID: {servo_ids}")
                else:
                    print("警告: サーボが検出されませんでした")
                
                # サーボを初期化（低速・低加速度設定）
                self._initialize_servos()
                
            except Exception as e:
                print(f"サーボコントローラー初期化エラー: {e}")
                print("サーボなしモードで続行します")
                self.enable_servo = False
        else:
            print("サーボなしモードで起動")
    
    def _initialize_servos(self):
        """サーボを初期位置に移動し、パラメータを設定"""
        servo_ids = [self.PAN_SERVO_ID, self.TILT_SERVO_ID, self.ROLL_SERVO_ID]
        
        for servo_id in servo_ids:
            try:
                # トルクを有効化
                self.servo.StartServo(servo_id)
                
                # ゆっくり動かすための設定
                # 速度: 200 step/s（非常に遅い）
                # 加速度: 5 (100 step/s^2単位なので500 step/s^2)
                self.servo.SetSpeed(servo_id, 200)
                self.servo.SetAcceleration(servo_id, 5)
                
                # 中央位置に移動（無効化）
                # print(f"サーボID {servo_id} を中央位置に移動中...")
                # self.servo.MoveTo(servo_id, self.CENTER_POSITION, speed=800, acc=20, wait=True)
                
                print(f"サーボID {servo_id} 初期化完了")
                
            except Exception as e:
                print(f"サーボID {servo_id} の初期化エラー: {e}")
    
    def move_to_position(self, pan_delta, tilt_delta, roll_delta):
        """
        サーボを指定位置に移動（累積オフセット方式）
        
        Args:
            pan_delta: パン軸の移動量（虹彩のずれに応じた増分）
            tilt_delta: チルト軸の移動量（虹彩のずれに応じた増分）
            roll_delta: ロール軸の移動量（虹彩のずれに応じた増分）
        """
        if not self.enable_servo:
            return
        
        # 累積オフセットに加算
        self.pan_cumulative_offset += pan_delta
        self.tilt_cumulative_offset += tilt_delta
        self.roll_cumulative_offset += roll_delta
        
        # 範囲外チェック用に元の値を保存
        original_pan = self.pan_cumulative_offset
        original_tilt = self.tilt_cumulative_offset
        original_roll = self.roll_cumulative_offset
        
        # 範囲制限
        self.pan_cumulative_offset = max(-self.ANGLE_RANGE, min(self.ANGLE_RANGE, self.pan_cumulative_offset))
        self.tilt_cumulative_offset = max(-self.ANGLE_RANGE, min(self.ANGLE_RANGE, self.tilt_cumulative_offset))
        self.roll_cumulative_offset = max(-self.ANGLE_RANGE, min(self.ANGLE_RANGE, self.roll_cumulative_offset))
        
        # 範囲外警告
        if original_pan != self.pan_cumulative_offset or original_tilt != self.tilt_cumulative_offset or original_roll != self.roll_cumulative_offset:
            warnings = []
            if original_pan != self.pan_cumulative_offset:
                warnings.append(f"パン: {original_pan:.0f} → {self.pan_cumulative_offset:.0f}")
            if original_tilt != self.tilt_cumulative_offset:
                warnings.append(f"チルト: {original_tilt:.0f} → {self.tilt_cumulative_offset:.0f}")
            if original_roll != self.roll_cumulative_offset:
                warnings.append(f"ロール: {original_roll:.0f} → {self.roll_cumulative_offset:.0f}")
            print(f"警告: サーボ可動範囲外のため制限しました - {', '.join(warnings)}")
        
        # 目標位置計算
        pan_pos = int(self.CENTER_POSITION + self.pan_cumulative_offset)
        tilt_pos = int(self.CENTER_POSITION + self.tilt_cumulative_offset)
        roll_pos = int(self.CENTER_POSITION + self.roll_cumulative_offset)
        
        try:
            # 各サーボに移動指令（waitはFalseで非同期実行）
            self.servo.MoveTo(self.PAN_SERVO_ID, pan_pos, speed=200, acc=5, wait=False)
            self.servo.MoveTo(self.TILT_SERVO_ID, tilt_pos, speed=200, acc=5, wait=False)
            self.servo.MoveTo(self.ROLL_SERVO_ID, roll_pos, speed=200, acc=5, wait=False)
            
        except Exception as e:
            print(f"サーボ移動エラー: {e}")
    
    def get_current_positions(self):
        """現在のサーボ位置を取得"""
        if not self.enable_servo:
            return None, None, None
        
        try:
            pan_pos = self.servo.ReadPosition(self.PAN_SERVO_ID)
            tilt_pos = self.servo.ReadPosition(self.TILT_SERVO_ID)
            roll_pos = self.servo.ReadPosition(self.ROLL_SERVO_ID)
            return pan_pos, tilt_pos, roll_pos
        except Exception as e:
            print(f"位置読み取りエラー: {e}")
            return None, None, None
    
    def stop_all(self):
        """全サーボのトルクを無効化"""
        if not self.enable_servo:
            return
        
        servo_ids = [self.PAN_SERVO_ID, self.TILT_SERVO_ID, self.ROLL_SERVO_ID]
        for servo_id in servo_ids:
            try:
                self.servo.StopServo(servo_id)
            except Exception as e:
                print(f"サーボID {servo_id} の停止エラー: {e}")
        
        print("全サーボを停止しました")


class EyeTracker:
    def __init__(self, display_mode=True, enable_servo=True, servo_port='/dev/ttyACM0'):
        """
        Args:
            display_mode: Trueの場合、画面に映像を表示（開発用）
                         Falseの場合、画面表示なし（実用時）
            enable_servo: サーボ制御を有効化
            servo_port: サーボのシリアルポート
        """
        self.display_mode = display_mode
        
        # サーボコントローラーの初期化
        self.servo_controller = ServoController(
            port=servo_port, 
            enable_servo=enable_servo
        )
        
        # MediaPipe Face Meshの初期化
        self.mp_face_mesh = mp.solutions.face_mesh
        self.face_mesh = self.mp_face_mesh.FaceMesh(
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        self.mp_drawing = mp.solutions.drawing_utils
        self.mp_drawing_styles = mp.solutions.drawing_styles
        
        # カメラの初期化
        self.cap = cv2.VideoCapture(0)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        
        # MediaPipe Face Meshの目のランドマークインデックス
        # 左目: 33, 133, 160, 159, 158, 157, 173
        # 右目: 362, 263, 385, 386, 387, 388, 466
        self.LEFT_EYE_CENTER = 468  # 左目虹彩中心
        self.RIGHT_EYE_CENTER = 473  # 右目虹彩中心
        
        # カメラフレームの中心座標（後で設定）
        self.frame_center_x = 320
        self.frame_center_y = 240
        
        # デッドゾーン（しきい値）設定
        self.pan_dead_zone = 20    # ピクセル（左右のずれがこれ以下なら動かさない）
        self.tilt_dead_zone = 20   # ピクセル（上下のずれがこれ以下なら動かさない）
        self.roll_dead_zone = 6.0  # 度（傾きがこれ以下なら動かさない）
        
        # 制御ゲイン（ピクセル差をサーボ角度に変換）
        self.pan_gain = 3.0   # パンのゲイン
        self.tilt_gain = 0.7  # チルトのゲイン
        self.roll_gain = 2.0  # ロールのゲイン
        
        # PD制御用のパラメータ
        self.tilt_kp = 0.5    # 比例ゲイン
        self.tilt_kd = 0.8    # 微分ゲイン（振動抑制）
        self.pan_kp = 0.3     # パンの比例ゲイン（振動抑制のため低め）
        self.pan_kd = 1.2     # パンの微分ゲイン（振動抑制のため高め）
        self.roll_kp = 0.3    # ロールの比例ゲイン（振動抑制のため低め）
        self.roll_kd = 1.0    # ロールの微分ゲイン
        
        # 前回の誤差（微分項計算用）
        self.prev_pan_error = 0
        self.prev_tilt_error = 0
        self.prev_roll_error = 0
        
        print("Eye Tracker 初期化完了")
        print(f"ディスプレイモード: {'ON' if display_mode else 'OFF'}")
        print(f"サーボ制御: {'ON' if enable_servo else 'OFF'}")
    
    def get_eye_positions(self, frame):
        """
        フレームから両目の位置を検出
        
        Returns:
            tuple: (left_eye_pos, right_eye_pos, center_pos)
                   各posは(x, y)のタプル、検出失敗時はNone
        """
        # BGR to RGB変換
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # 顔検出
        results = self.face_mesh.process(rgb_frame)
        
        if not results.multi_face_landmarks:
            return None, None, None
        
        # 最初の顔のランドマークを取得
        face_landmarks = results.multi_face_landmarks[0]
        
        h, w = frame.shape[:2]
        
        # 左目中心座標
        left_eye = face_landmarks.landmark[self.LEFT_EYE_CENTER]
        left_pos = (int(left_eye.x * w), int(left_eye.y * h))
        
        # 右目中心座標
        right_eye = face_landmarks.landmark[self.RIGHT_EYE_CENTER]
        right_pos = (int(right_eye.x * w), int(right_eye.y * h))
        
        # 両目の中心点（顔の中心として使用）
        center_pos = (
            (left_pos[0] + right_pos[0]) // 2,
            (left_pos[1] + right_pos[1]) // 2
        )
        
        return left_pos, right_pos, center_pos
    
    def calculate_servo_offsets(self, left_pos, right_pos, center_pos):
        """
        目の位置からサーボの移動量（増分）を計算（PD制御 + デッドゾーン）
        
        Returns:
            tuple: (pan_delta, tilt_delta, roll_delta) - サーボの移動増分
        """
        if not left_pos or not right_pos or not center_pos:
            return 0, 0, 0
        
        # パン（左右）: 中心のX座標のずれ
        pan_error = center_pos[0] - self.frame_center_x
        
        # デッドゾーン適用：しきい値以下なら誤差を0に
        if abs(pan_error) < self.pan_dead_zone:
            pan_error = 0
            self.prev_pan_error = 0  # 微分項もリセット
        
        # PD制御
        if pan_error != 0:
            p_term = pan_error * self.pan_kp
            d_term = (pan_error - self.prev_pan_error) * self.pan_kd
            pan_delta = int(p_term + d_term)
            self.prev_pan_error = pan_error
        else:
            pan_delta = 0
        
        # チルト（上下）: 中心のY座標のずれ
        tilt_error = center_pos[1] - self.frame_center_y
        
        # デッドゾーン適用
        if abs(tilt_error) < self.tilt_dead_zone:
            tilt_error = 0
            self.prev_tilt_error = 0
        
        # PD制御
        if tilt_error != 0:
            p_term = tilt_error * self.tilt_kp
            d_term = (tilt_error - self.prev_tilt_error) * self.tilt_kd
            tilt_delta = int(p_term + d_term)
            self.prev_tilt_error = tilt_error
        else:
            tilt_delta = 0
        
        # ロール（回転）: 両目の傾き
        dy = right_pos[1] - left_pos[1]
        dx = right_pos[0] - left_pos[0]
        angle_rad = math.atan2(dy, dx)
        angle_deg = math.degrees(angle_rad)
        
        # デッドゾーン適用
        if abs(angle_deg) < self.roll_dead_zone:
            angle_deg = 0
            self.prev_roll_error = 0
        
        # PD制御（目が水平になるように制御）
        if angle_deg != 0:
            p_term = angle_deg * self.roll_kp * 5
            d_term = (angle_deg - self.prev_roll_error) * self.roll_kd * 5
            roll_delta = int(p_term + d_term)
            self.prev_roll_error = angle_deg
        else:
            roll_delta = 0
        
        return pan_delta, tilt_delta, roll_delta
    
    def draw_eye_info(self, frame, left_pos, right_pos, center_pos):
        """画面に目の位置情報を描画（開発用）"""
        # フレームの中心に十字線を描画
        cv2.line(frame, (self.frame_center_x - 20, self.frame_center_y), 
                (self.frame_center_x + 20, self.frame_center_y), (128, 128, 128), 1)
        cv2.line(frame, (self.frame_center_x, self.frame_center_y - 20), 
                (self.frame_center_x, self.frame_center_y + 20), (128, 128, 128), 1)
        
        # 画面中央にデッドゾーンを示す矩形を描画（緑色）
        cv2.rectangle(frame, 
                     (self.frame_center_x - self.pan_dead_zone, self.frame_center_y - self.tilt_dead_zone),
                     (self.frame_center_x + self.pan_dead_zone, self.frame_center_y + self.tilt_dead_zone),
                     (0, 255, 0), 2)
        
        if left_pos and right_pos:
            # 左右の虹彩を結ぶ長い直線を描画（水平基準線として）
            # 直線を画面端まで延長
            dy = right_pos[1] - left_pos[1]
            dx = right_pos[0] - left_pos[0]
            if dx != 0:
                # 直線の傾きを計算
                slope = dy / dx
                # 画面の左端(x=0)と右端(x=640)での y座標を計算
                y_at_0 = int(left_pos[1] - slope * left_pos[0])
                y_at_640 = int(left_pos[1] + slope * (640 - left_pos[0]))
                cv2.line(frame, (0, y_at_0), (640, y_at_640), (255, 255, 0), 2)
            else:
                # 垂直の場合
                cv2.line(frame, (left_pos[0], 0), (left_pos[0], 480), (255, 255, 0), 2)
            
            # 左目に青い円
            cv2.circle(frame, left_pos, 5, (255, 0, 0), -1)
            cv2.putText(frame, "L", (left_pos[0] + 10, left_pos[1]), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)
            
            # 右目に緑の円
            cv2.circle(frame, right_pos, 5, (0, 255, 0), -1)
            cv2.putText(frame, "R", (right_pos[0] + 10, right_pos[1]), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
            
            # 中心点に赤い十字
            cv2.drawMarker(frame, center_pos, (0, 0, 255), 
                          cv2.MARKER_CROSS, 20, 2)
            
            # 座標情報を表示
            cv2.putText(frame, f"Center: {center_pos}", (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
            
            # 目の間隔を計算して表示
            eye_distance = np.sqrt((right_pos[0] - left_pos[0])**2 + 
                                  (right_pos[1] - left_pos[1])**2)
            cv2.putText(frame, f"Eye Distance: {eye_distance:.1f}px", (10, 60),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)
            
            # 傾き角度を表示
            dy = right_pos[1] - left_pos[1]
            dx = right_pos[0] - left_pos[0]
            angle_deg = math.degrees(math.atan2(dy, dx))
            cv2.putText(frame, f"Angle: {angle_deg:.1f}deg", (10, 90),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)
        
        return frame
    
    def run(self):
        """メインループ"""
        print("プログラム開始。終了するにはESCキーまたはCtrl+Cを押してください。")
        
        frame_count = 0
        start_time = time.time()
        
        try:
            while True:
                ret, frame = self.cap.read()
                if not ret:
                    print("カメラからの読み込みに失敗しました")
                    break
                
                # カメラが上下逆に取り付けられているため、画像を上下反転
                frame = cv2.flip(frame, 0)
                
                # 両目の位置を検出
                left_pos, right_pos, center_pos = self.get_eye_positions(frame)
                
                # サーボのオフセットを計算
                pan_offset, tilt_offset, roll_offset = self.calculate_servo_offsets(
                    left_pos, right_pos, center_pos
                )
                
                # サーボを動かす（5フレームに1回だけ更新して制御周期を遅くする）
                frame_count += 1
                if left_pos and right_pos and center_pos and frame_count % 5 == 0:
                    self.servo_controller.move_to_position(
                        pan_offset, tilt_offset, roll_offset
                    )
                
                # コンソールに情報を出力（ディスプレイなしモードでも確認可能）
                if center_pos:
                    if frame_count % 30 == 0:  # 30フレームごとに出力
                        elapsed = time.time() - start_time
                        fps = frame_count / elapsed
                        print(f"[{elapsed:.1f}s] 中心: {center_pos}, "
                              f"サーボ: P={pan_offset} T={tilt_offset} R={roll_offset}, "
                              f"FPS: {fps:.1f}")
                else:
                    if frame_count % 30 == 0:
                        print("顔が検出されませんでした")
                
                # ディスプレイモードの場合、画面に表示
                if self.display_mode:
                    frame = self.draw_eye_info(frame, left_pos, right_pos, center_pos)
                    cv2.imshow('Eye Tracker', frame)
                    
                    # ESCキーで終了
                    if cv2.waitKey(1) & 0xFF == 27:
                        print("ESCキーが押されました。終了します。")
                        break
                else:
                    # ディスプレイなしモードでも処理を続ける
                    # ここに実際のカメラ制御ロジックを追加
                    time.sleep(0.01)  # CPU使用率を抑える
        
        except KeyboardInterrupt:
            print("\nCtrl+Cが押されました。終了します。")
        
        finally:
            self.cleanup()
    
    def cleanup(self):
        """リソースの解放"""
        # サーボを停止
        self.servo_controller.stop_all()
        
        self.cap.release()
        if self.display_mode:
            cv2.destroyAllWindows()
        print("リソースを解放しました。")


def main():
    parser = argparse.ArgumentParser(description='両目検知プログラム')
    parser.add_argument('--no-display', action='store_true',
                       help='ディスプレイなしモードで実行（実用時）')
    parser.add_argument('--no-servo', action='store_true',
                       help='サーボなしモードで実行（テスト用）')
    parser.add_argument('--servo-port', type=str, default='/dev/ttyACM0',
                       help='サーボのシリアルポート（デフォルト: /dev/ttyACM0）')
    args = parser.parse_args()
    
    # ディスプレイモードの判定
    display_mode = not args.no_display
    enable_servo = not args.no_servo
    
    # トラッカーの起動
    tracker = EyeTracker(
        display_mode=display_mode,
        enable_servo=enable_servo,
        servo_port=args.servo_port
    )
    tracker.run()


if __name__ == "__main__":
    main()
