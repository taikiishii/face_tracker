#!/usr/bin/env python3
"""
STS3215サーボモーター セットアップスクリプト
サーボIDの確認・変更を行います
"""

import sys
from st3215 import ST3215
import time


class ServoSetup:
    def __init__(self, port='/dev/ttyACM0', baudrate=1000000):
        """
        Args:
            port: シリアルポート
            baudrate: ボーレート
        """
        try:
            print(f"サーボコントローラーに接続中: {port} @ {baudrate}bps")
            self.servo = ST3215(port)
            print("接続成功！\n")
        except Exception as e:
            print(f"エラー: サーボコントローラーに接続できませんでした")
            print(f"詳細: {e}")
            print("\n確認事項:")
            print("  1. USBケーブルが接続されているか")
            print("  2. サーボの電源が入っているか")
            print(f"  3. ポート名が正しいか（現在: {port}）")
            print("     利用可能なポート: ls /dev/ttyUSB*")
            sys.exit(1)
    
    def scan_servos(self):
        """接続されているサーボをスキャン"""
        print("=" * 60)
        print("サーボをスキャン中...")
        print("=" * 60)
        
        try:
            servo_ids = self.servo.ListServos()
            
            if servo_ids:
                print(f"\n✓ {len(servo_ids)}台のサーボが見つかりました: {servo_ids}\n")
                return servo_ids
            else:
                print("\n✗ サーボが見つかりませんでした")
                print("\n確認事項:")
                print("  1. サーボの電源が入っているか")
                print("  2. 配線が正しく接続されているか")
                print("  3. ボーレート設定が正しいか")
                return []
        except Exception as e:
            print(f"\nエラー: スキャン中に問題が発生しました")
            print(f"詳細: {e}")
            return []
    
    def show_servo_info(self, servo_id):
        """サーボの詳細情報を表示"""
        print(f"\n--- サーボ ID {servo_id} の情報 ---")
        
        try:
            # 現在位置
            position = self.servo.ReadPosition(servo_id)
            if position is not None:
                print(f"  現在位置: {position} (中心=2048)")
            
            # 電圧
            voltage = self.servo.ReadVoltage(servo_id)
            if voltage is not None:
                print(f"  電圧: {voltage:.2f}V")
            
            # 温度
            temperature = self.servo.ReadTemperature(servo_id)
            if temperature is not None:
                print(f"  温度: {temperature}°C")
            
            # 電流
            current = self.servo.ReadCurrent(servo_id)
            if current is not None:
                print(f"  電流: {current:.1f}mA")
            
            # 負荷
            load = self.servo.ReadLoad(servo_id)
            if load is not None:
                print(f"  負荷: {load:.1f}%")
            
            # モード
            mode = self.servo.ReadMode(servo_id)
            if mode is not None:
                mode_names = {
                    0: "位置制御モード",
                    1: "定速回転モード", 
                    2: "PWM制御モード",
                    3: "ステップサーボモード"
                }
                print(f"  動作モード: {mode} ({mode_names.get(mode, '不明')})")
            
            return True
            
        except Exception as e:
            print(f"  エラー: 情報の取得に失敗しました - {e}")
            return False
    
    def test_servo_movement(self, servo_id):
        """サーボを動かしてテスト"""
        print(f"\nサーボ ID {servo_id} の動作テストを行います")
        response = input("テストを実行しますか？ [y/N]: ").strip().lower()
        
        if response != 'y':
            print("テストをスキップしました")
            return
        
        try:
            # トルクを有効化
            self.servo.StartServo(servo_id)
            
            # 中央位置に移動
            print("  中央位置(2048)に移動...")
            self.servo.MoveTo(servo_id, 2048, speed=800, acc=20, wait=True)
            time.sleep(0.5)
            
            # 右に移動
            print("  右方向(2348)に移動...")
            self.servo.MoveTo(servo_id, 2348, speed=800, acc=20, wait=True)
            time.sleep(0.5)
            
            # 左に移動
            print("  左方向(1748)に移動...")
            self.servo.MoveTo(servo_id, 1748, speed=800, acc=20, wait=True)
            time.sleep(0.5)
            
            # 中央に戻る
            print("  中央位置(2048)に戻る...")
            self.servo.MoveTo(servo_id, 2048, speed=800, acc=20, wait=True)
            
            print("✓ テスト完了")
            
        except Exception as e:
            print(f"✗ テスト中にエラーが発生しました: {e}")
    
    def change_servo_id(self, current_id, new_id):
        """サーボのIDを変更"""
        print(f"\nサーボ ID {current_id} を ID {new_id} に変更します")
        print("警告: この操作はサーボのEEPROMに書き込まれ、永続的に変更されます")
        
        response = input("本当に変更しますか？ [y/N]: ").strip().lower()
        
        if response != 'y':
            print("ID変更をキャンセルしました")
            return False
        
        try:
            # サーボが存在することを確認
            if not self.servo.PingServo(current_id):
                print(f"✗ サーボ ID {current_id} が応答しません")
                return False
            
            # EEPROMをアンロック
            print("  EEPROMをアンロック中...")
            result = self.servo.UnLockEprom(current_id)
            time.sleep(0.2)
            
            # STS_IDアドレス（アドレス5）に新しいIDを書き込み
            print(f"  ID {current_id} → {new_id} に変更中...")
            STS_ID = 5  # ID is at address 5 in the control table
            
            result = self.servo.write1ByteTxOnly(current_id, STS_ID, new_id)
            time.sleep(0.5)
            
            # 新しいIDで応答確認
            print("  新しいIDで応答を確認中...")
            if self.servo.PingServo(new_id):
                print(f"✓ ID変更成功！ サーボは現在 ID {new_id} です")
                
                # EEPROMをロック（新しいIDで）
                print("  EEPROMをロック中...")
                self.servo.LockEprom(new_id)
                
                return True
            else:
                print("✗ ID変更に失敗しました（新しいIDで応答がありません）")
                # 元に戻す試行
                print("  元のIDでロックを試みます...")
                try:
                    self.servo.LockEprom(current_id)
                except:
                    pass
                return False
                
        except Exception as e:
            print(f"✗ ID変更中にエラーが発生しました: {e}")
            import traceback
            traceback.print_exc()
            # エラー時は元のIDでロックを試みる
            try:
                self.servo.LockEprom(current_id)
            except:
                pass
            return False
    
    def define_middle_position(self, servo_id):
        """現在位置を中立位置（2048）として設定"""
        print(f"\nサーボ ID {servo_id} の中立位置を設定します")
        
        try:
            # 現在位置を取得
            current_pos = self.servo.ReadPosition(servo_id)
            if current_pos is None:
                print("✗ 現在位置を読み取れませんでした")
                return False
            
            print(f"  現在位置: {current_pos}")
            print("  この位置を新しい中立位置（2048）として設定します")
            print("  警告: この操作はEEPROMに書き込まれ、永続的に変更されます")
            
            response = input("実行しますか？ [y/N]: ").strip().lower()
            
            if response != 'y':
                print("キャンセルしました")
                return False
            
            # EEPROMをアンロック
            print("  EEPROMをアンロック中...")
            self.servo.UnLockEprom(servo_id)
            time.sleep(0.1)
            
            # 中立位置を設定
            print("  中立位置を設定中...")
            self.servo.DefineMiddle(servo_id)
            time.sleep(0.5)
            
            # EEPROMをロック
            print("  EEPROMをロック中...")
            self.servo.LockEprom(servo_id)
            
            # 確認
            new_pos = self.servo.ReadPosition(servo_id)
            print(f"✓ 中立位置設定完了！ 現在位置: {new_pos}")
            
            return True
            
        except Exception as e:
            print(f"✗ 中立位置設定中にエラーが発生しました: {e}")
            return False
    
    def adjust_position_correction(self, servo_id):
        """位置補正値を調整"""
        print(f"\nサーボ ID {servo_id} の位置補正を調整します")
        
        try:
            # 現在の補正値を取得
            current_correction = self.servo.ReadCorrection(servo_id)
            current_pos = self.servo.ReadPosition(servo_id)
            
            if current_correction is not None:
                print(f"  現在の補正値: {current_correction} steps")
            if current_pos is not None:
                print(f"  現在位置: {current_pos}")
            
            print("\n補正値の範囲: -2047 ~ +2047 steps")
            print("補正値を加えると中立位置がシフトします")
            print("例: 補正値+100 → 中立位置が100ステップ右にずれる")
            
            correction = input("\n新しい補正値を入力 (0でリセット): ").strip()
            
            try:
                correction = int(correction)
                
                if correction < -2047 or correction > 2047:
                    print("✗ 補正値は -2047 ~ +2047 の範囲で入力してください")
                    return False
                
                print(f"  補正値を {correction} に設定します")
                print("  警告: この操作はEEPROMに書き込まれ、永続的に変更されます")
                
                response = input("実行しますか？ [y/N]: ").strip().lower()
                
                if response != 'y':
                    print("キャンセルしました")
                    return False
                
                # EEPROMをアンロック
                print("  EEPROMをアンロック中...")
                self.servo.UnLockEprom(servo_id)
                time.sleep(0.1)
                
                # 補正値を設定
                print("  補正値を設定中...")
                self.servo.CorrectPosition(servo_id, correction)
                time.sleep(0.5)
                
                # EEPROMをロック
                print("  EEPROMをロック中...")
                self.servo.LockEprom(servo_id)
                
                # 確認
                new_correction = self.servo.ReadCorrection(servo_id)
                new_pos = self.servo.ReadPosition(servo_id)
                print(f"✓ 補正値設定完了！")
                print(f"  補正値: {new_correction} steps")
                print(f"  現在位置: {new_pos}")
                
                return True
                
            except ValueError:
                print("✗ 数値を入力してください")
                return False
                
        except Exception as e:
            print(f"✗ 補正値設定中にエラーが発生しました: {e}")
            return False
    
    def check_motion_range(self):
        """3軸の動作範囲を調べる"""
        print("\n" + "=" * 60)
        print("3軸の動作範囲確認")
        print("=" * 60)
        print("\n各軸のサーボをフリーにして、手で動かして範囲を確認します。")
        print("準備:")
        print("  1. パン（左右）サーボ: ID 1")
        print("  2. ロール（回転）サーボ: ID 2")
        print("  3. チルト（上下）サーボ: ID 3")
        
        servo_ids = self.servo.ListServos()
        print(f"\n検出されたサーボ: {servo_ids}")
        
        # 各軸のIDを確認
        required_ids = [1, 2, 3]
        missing_ids = [sid for sid in required_ids if sid not in servo_ids]
        
        if missing_ids:
            print(f"\n警告: 必要なサーボID {missing_ids} が見つかりません")
            response = input("続行しますか？ [y/N]: ").strip().lower()
            if response != 'y':
                return False
        
        axis_names = {1: "パン（左右）", 2: "ロール（回転）", 3: "チルト（上下）"}
        
        for servo_id in [1, 2, 3]:
            if servo_id not in servo_ids:
                print(f"\nサーボID {servo_id} がスキップされました（検出されていません）")
                continue
            
            axis_name = axis_names[servo_id]
            print(f"\n--- {axis_name} (ID {servo_id}) の動作範囲確認 ---")
            
            try:
                # トルクを無効化（フリー状態にする）
                print("  サーボをフリーにしています...")
                self.servo.StopServo(servo_id)
                time.sleep(0.3)
                
                print(f"  {axis_name}軸を手で動かして、動作範囲全体を確認してください")
                print("  準備ができたらEnterキーを押してください...")
                input()
                
                # 位置を記録開始
                print("  位置を記録中... (10秒間)")
                positions = []
                start_time = time.time()
                
                while time.time() - start_time < 10:
                    try:
                        pos = self.servo.ReadPosition(servo_id)
                        if pos is not None:
                            positions.append(pos)
                        time.sleep(0.1)
                    except:
                        pass
                
                if positions:
                    min_pos = min(positions)
                    max_pos = max(positions)
                    center_pos = 2048
                    range_total = max_pos - min_pos
                    range_positive = max_pos - center_pos
                    range_negative = center_pos - min_pos
                    
                    print(f"\n  結果:")
                    print(f"    最小位置: {min_pos}")
                    print(f"    最大位置: {max_pos}")
                    print(f"    中心位置: {center_pos}")
                    print(f"    動作範囲: {range_total} steps")
                    print(f"    正方向: +{range_positive} steps (角度: {range_positive * 0.088:.1f}度)")
                    print(f"    負方向: -{range_negative} steps (角度: {range_negative * 0.088:.1f}度)")
                else:
                    print("  警告: 位置データを取得できませんでした")
                
                # トルクを再度有効化
                print("  サーボをトルクONにしています...")
                self.servo.StartServo(servo_id)
                
            except Exception as e:
                print(f"  エラー: {e}")
                try:
                    self.servo.StartServo(servo_id)
                except:
                    pass
        
        print("\n" + "=" * 60)
        print("動作範囲確認完了")
        print("=" * 60)
        return True
    
    def interactive_menu(self):
        """インタラクティブメニュー"""
        while True:
            print("\n" + "=" * 60)
            print("STS3215 サーボセットアップ メニュー")
            print("=" * 60)
            print("1. サーボをスキャン")
            print("2. サーボ情報を表示")
            print("3. サーボ動作テスト")
            print("4. サーボIDを変更")
            print("5. クイックセットアップ（3軸用: ID 1, 2, 3に設定）")
            print("6. 中立位置を設定（現在位置を中央として設定）")
            print("7. 位置補正を調整（微調整用）")
            print("8. 動作範囲を確認（3軸の可動範囲を調べる）")
            print("0. 終了")
            print("=" * 60)
            
            choice = input("選択してください [0-8]: ").strip()
            
            if choice == '1':
                self.scan_servos()
            
            elif choice == '2':
                servo_ids = self.servo.ListServos()
                if not servo_ids:
                    print("\nサーボが見つかりません。先にスキャンしてください。")
                    continue
                
                print(f"\n検出されたサーボ: {servo_ids}")
                servo_id = input("情報を表示するサーボID: ").strip()
                
                try:
                    servo_id = int(servo_id)
                    if servo_id in servo_ids:
                        self.show_servo_info(servo_id)
                    else:
                        print(f"エラー: ID {servo_id} は検出されていません")
                except ValueError:
                    print("エラー: 数値を入力してください")
            
            elif choice == '3':
                servo_ids = self.servo.ListServos()
                if not servo_ids:
                    print("\nサーボが見つかりません。先にスキャンしてください。")
                    continue
                
                print(f"\n検出されたサーボ: {servo_ids}")
                servo_id = input("テストするサーボID: ").strip()
                
                try:
                    servo_id = int(servo_id)
                    if servo_id in servo_ids:
                        self.test_servo_movement(servo_id)
                    else:
                        print(f"エラー: ID {servo_id} は検出されていません")
                except ValueError:
                    print("エラー: 数値を入力してください")
            
            elif choice == '4':
                servo_ids = self.servo.ListServos()
                if not servo_ids:
                    print("\nサーボが見つかりません。先にスキャンしてください。")
                    continue
                
                print(f"\n検出されたサーボ: {servo_ids}")
                current_id = input("変更元のサーボID: ").strip()
                new_id = input("変更先のサーボID: ").strip()
                
                try:
                    current_id = int(current_id)
                    new_id = int(new_id)
                    
                    if current_id not in servo_ids:
                        print(f"エラー: ID {current_id} は検出されていません")
                        continue
                    
                    if new_id in servo_ids:
                        print(f"警告: ID {new_id} は既に使用されています")
                        response = input("本当に続行しますか？ [y/N]: ").strip().lower()
                        if response != 'y':
                            continue
                    
                    self.change_servo_id(current_id, new_id)
                    
                except ValueError:
                    print("エラー: 数値を入力してください")
            
            elif choice == '5':
                print("\n3軸カメラ制御用のクイックセットアップを開始します")
                print("必要なサーボ: 3台")
                print("  - パン（左右）用: ID 1")
                print("  - ロール（回転）用: ID 2")
                print("  - チルト（上下）用: ID 3")
                
                servo_ids = self.servo.ListServos()
                if len(servo_ids) < 3:
                    print(f"\nエラー: 3台のサーボが必要ですが、{len(servo_ids)}台しか検出されていません")
                    continue
                
                print(f"\n現在検出されているサーボ: {servo_ids}")
                print("\n各サーボを1台ずつ設定していきます")
                response = input("続行しますか？ [y/N]: ").strip().lower()
                
                if response != 'y':
                    continue
                
                # 1台ずつ設定
                for target_id in [1, 2, 3]:
                    role = {1: "パン（左右）", 2: "ロール（回転）", 3: "チルト（上下）"}[target_id]
                    
                    print(f"\n--- {role}用サーボ を ID {target_id} に設定 ---")
                    
                    # 既にIDが正しければスキップ
                    servo_ids = self.servo.ListServos()
                    if target_id in servo_ids:
                        print(f"ID {target_id} は既に存在します")
                        response = input(f"このサーボを{role}用として使用しますか？ [y/N]: ").strip().lower()
                        if response == 'y':
                            self.test_servo_movement(target_id)
                            continue
                    
                    # IDを設定
                    print(f"\n利用可能なサーボ: {servo_ids}")
                    current_id = input(f"{role}用サーボの現在のID: ").strip()
                    
                    try:
                        current_id = int(current_id)
                        if current_id in servo_ids:
                            if self.change_servo_id(current_id, target_id):
                                self.test_servo_movement(target_id)
                        else:
                            print(f"エラー: ID {current_id} は検出されていません")
                            break
                    except ValueError:
                        print("エラー: 数値を入力してください")
                        break
                
                print("\n✓ クイックセットアップ完了！")
                print("最終確認のため、サーボをスキャンします...")
                self.scan_servos()
            
            elif choice == '6':
                servo_ids = self.servo.ListServos()
                if not servo_ids:
                    print("\nサーボが見つかりません。先にスキャンしてください。")
                    continue
                
                print(f"\n検出されたサーボ: {servo_ids}")
                print("\n中立位置設定:")
                print("  サーボを手動で目的の位置（カメラ正面など）に動かしてから、")
                print("  その位置を中立位置（2048）として設定できます。")
                
                servo_id = input("\n中立位置を設定するサーボID: ").strip()
                
                try:
                    servo_id = int(servo_id)
                    if servo_id in servo_ids:
                        # 現在位置を表示
                        current_pos = self.servo.ReadPosition(servo_id)
                        print(f"\n現在位置: {current_pos}")
                        print("必要に応じて位置を調整してください")
                        print("  例: servo.MoveTo({}, 目的の位置)".format(servo_id))
                        
                        response = input("\nこの位置で中立位置を設定しますか？ [y/N]: ").strip().lower()
                        if response == 'y':
                            self.define_middle_position(servo_id)
                    else:
                        print(f"エラー: ID {servo_id} は検出されていません")
                except ValueError:
                    print("エラー: 数値を入力してください")
            
            elif choice == '7':
                servo_ids = self.servo.ListServos()
                if not servo_ids:
                    print("\nサーボが見つかりません。先にスキャンしてください。")
                    continue
                
                print(f"\n検出されたサーボ: {servo_ids}")
                print("\n位置補正:")
                print("  中立位置を少しずらしたい場合に使用します。")
                print("  補正値を設定すると、すべての位置指令にオフセットが加わります。")
                
                servo_id = input("\n補正値を設定するサーボID: ").strip()
                
                try:
                    servo_id = int(servo_id)
                    if servo_id in servo_ids:
                        self.adjust_position_correction(servo_id)
                    else:
                        print(f"エラー: ID {servo_id} は検出されていません")
                except ValueError:
                    print("エラー: 数値を入力してください")
            
            elif choice == '8':
                self.check_motion_range()
            
            elif choice == '0':
                print("\nセットアップツールを終了します")
                break
            
            else:
                print("\n無効な選択です。0-8の数字を入力してください。")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='STS3215サーボセットアップツール')
    parser.add_argument('--port', type=str, default='/dev/ttyACM0',
                       help='シリアルポート（デフォルト: /dev/ttyACM0）')
    parser.add_argument('--baudrate', type=int, default=1000000,
                       help='ボーレート（デフォルト: 1000000）')
    args = parser.parse_args()
    
    print("=" * 60)
    print("STS3215 サーボモーター セットアップツール")
    print("=" * 60)
    print()
    
    setup = ServoSetup(port=args.port, baudrate=args.baudrate)
    
    # 初期スキャン
    setup.scan_servos()
    
    # メニュー表示
    setup.interactive_menu()


if __name__ == "__main__":
    main()
