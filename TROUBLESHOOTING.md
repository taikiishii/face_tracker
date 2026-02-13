# Face Tracker トラブルシューティングガイド

## 問題: 長時間稼働すると動かなくなる

### 原因の特定

プログラムが1日程度稼働すると動かなくなる場合、以下の原因が考えられます:

1. **メモリリーク** - MediaPipe、OpenCV、カメラドライバのメモリリークが原因
2. **カメラデバイスの問題** - カメラドライバがハングアップ
3. **シリアルポートの問題** - サーボ通信のエラー蓄積
4. **ファイルディスクリプタのリーク** - リソースが正しく解放されていない
5. **システムリソースの枯渇** - メモリ、ディスクスペース等の不足

### 診断方法

#### 1. 診断スクリプトの実行

```bash
chmod +x diagnose.sh
./diagnose.sh
```

このスクリプトは以下の情報を収集します:
- システム情報（メモリ、CPU、ディスク）
- カメラデバイスの状態
- シリアルポート接続の状態
- プロセス情報
- ログファイルの内容
- カーネルメッセージとエラー

#### 2. ログファイルの確認

プログラムは詳細なログを `face_tracker.log` に記録します:

```bash
# リアルタイムでログを監視
tail -f face_tracker.log

# エラーメッセージだけを表示
grep -i error face_tracker.log

# リソース監視ログを表示
grep "リソース監視" face_tracker.log
```

#### 3. リソース使用状況の確認

プログラム実行中に別のターミナルから:

```bash
# メモリとCPU使用率を監視
top -p $(pgrep -f face_tracker.py)

# メモリの詳細情報
ps aux | grep face_tracker.py

# ファイルディスクリプタ数を確認
ls -l /proc/$(pgrep -f face_tracker.py)/fd/ | wc -l
```

### 改善策

#### 1. 自動監視・再起動スクリプトの使用

`monitor.sh` スクリプトを使用してプログラムを監視し、問題が発生したら自動的に再起動します:

```bash
chmod +x monitor.sh

# バックグラウンドで起動
nohup ./monitor.sh > /dev/null 2>&1 &

# または、systemdサービスとして登録（推奨）
```

監視スクリプトは以下をチェックします:
- プロセスが実行中か
- メモリ使用量が異常に高くないか
- プロセスがゾンビ状態でないか
- ログファイルが定期的に更新されているか

#### 2. ログレベルの調整

詳細なデバッグ情報が必要な場合:

```bash
python3 face_tracker.py --log-level DEBUG
```

通常運用時は INFO または WARNING に設定してディスク使用量を抑えます:

```bash
python3 face_tracker.py --log-level WARNING
```

#### 3. 定期的な再起動

完全な解決策が見つかるまで、cron で定期的に再起動する方法もあります:

```bash
# crontabを編集
crontab -e

# 毎日午前3時に再起動する例
0 3 * * * /path/to/monitor.sh restart
```

### ログファイルから分かること

#### メモリリークの兆候

```
[リソース監視] 稼働時間: 10.0h, メモリ: 150.5MB, CPU: 25.0%
...
[リソース監視] 稼働時間: 20.0h, メモリ: 450.8MB, CPU: 25.0%
...
警告: メモリ使用量が高い: 520.3MB
```

→ メモリが時間とともに増加している場合はメモリリーク

#### カメラエラーの蓄積

```
連続カメラエラー 5 回。再初期化を試みます
カメラを再初期化します
カメラの再初期化完了
```

→ カメラドライバの問題。USB接続を確認

#### サーボ通信エラー

```
サーボ移動エラー: timeout
警告: パンサーボが可動範囲の限界に達しました
```

→ サーボの電源、配線、負荷を確認

### システムレベルの対策

#### 1. スワップメモリの確保

Raspberry Piでメモリが不足する場合:

```bash
# スワップサイズを確認
free -h

# スワップを増やす (例: 2GB)
sudo dphys-swapfile swapoff
sudo nano /etc/dphys-swapfile
# CONF_SWAPSIZE=2048 に変更
sudo dphys-swapfile setup
sudo dphys-swapfile swapon
```

#### 2. カメラドライバの再初期化

USB カメラの場合、ドライバをリセット:

```bash
# USBデバイスをリセット
sudo usbreset /dev/video0

# または、カーネルモジュールの再読み込み
sudo modprobe -r uvcvideo
sudo modprobe uvcvideo
```

#### 3. ウォッチドッグタイマーの有効化

システムがハングした時に自動再起動:

```bash
# ウォッチドッグを有効化
sudo modprobe bcm2835_wdt
sudo nano /etc/systemd/system.conf
# RuntimeWatchdogSec=60 のコメントを外す
sudo systemctl daemon-reload
```

### 開発中のデバッグ

#### メモリプロファイリング

メモリリークを詳細に調査:

```bash
pip install memory_profiler

# プログラムに@profileデコレータを追加
python3 -m memory_profiler face_tracker.py
```

#### psutilでのリソース監視

改良版プログラムにはpsutilによるリソース監視が組み込まれています。
5分ごとに以下の情報がログに記録されます:

- 稼働時間
- メモリ使用量（プロセス）
- CPU使用率
- システム全体のメモリ使用率
- オープン中のファイルディスクリプタ数
- 総フレーム数
- エラー発生回数
- カメラ再初期化回数

## よくある問題と解決策

### Q: プログラムが起動しない

**A:** 必要なパッケージをインストール:
```bash
pip install -r requirements.txt
```

### Q: カメラが見つからない

**A:** カメラデバイスを確認:
```bash
ls -l /dev/video*
v4l2-ctl --list-devices
```

### Q: サーボが動かない

**A:** シリアルポートの権限を確認:
```bash
sudo usermod -a -G dialout $USER
# ログアウト後、再ログイン
```

### Q: ログファイルが大きくなりすぎる

**A:** ログローテーションが自動的に行われます（10MBごとに最大5世代）。
古いログを手動で削除:
```bash
rm face_tracker.log.*
```

## パフォーマンスチューニング

### CPUオーバーヒート対策

```bash
# CPU温度を確認
vcgencmd measure_temp

# 冷却ファンの設置を検討
# またはCPU周波数を制限
```

### カメラ解像度の調整

高解像度はCPU負荷が高い。必要に応じて調整:

```python
self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 320)  # 640から変更
self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 240)  # 480から変更
```

### フレームレートの制限

```python
time.sleep(0.033)  # 約30fps
```
