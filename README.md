# Face Tracker with Servo Control

両目を検知してカメラをサーボモーターで制御するプログラム

## ハードウェア構成

- **プラットフォーム**: Raspberry Pi 5
- **カメラ**: USB Webカメラ
- **サーボモーター**: Feetech STS3215（3軸）
  - ID 1: パン（左右）
  - ID 2: ロール（回転）
  - ID 3: チルト（上下）

## セットアップ

### 1. 仮想環境の作成とパッケージインストール

```bash
# 仮想環境の作成
python3 -m venv venv

# 仮想環境の有効化
source venv/bin/activate

# 依存パッケージのインストール
pip install -r requirements.txt
```

### 2. サーボモーターのセットアップ

初めてサーボを使用する場合、またはIDや中立位置を設定する必要がある場合は、セットアップツールを使用します。

```bash
source venv/bin/activate
python servo_setup.py
```

#### セットアップツールの主な機能

**1. サーボをスキャン**
- 接続されているすべてのサーボを自動検出
- 各サーボのIDを確認

**2. サーボ情報を表示**
- 位置、電圧、温度、電流、負荷、動作モードを確認

**3. サーボ動作テスト**
- サーボを動かして正常動作を確認
- 左右に動かして中央に戻るテスト

**4. サーボIDを変更**
- サーボのIDを任意の値に変更（EEPROM保存）
- 例: ID 254（工場出荷状態）→ ID 1（パン用）

**5. クイックセットアップ（推奨）**
- 3台のサーボを一括で設定
- ID 1: パン（左右）、ID 2: ロール（回転）、ID 3: チルト（上下）
- 各サーボの動作テストも実行

**6. 中立位置を設定**
- カメラを正面に向けた状態で実行
- 現在の位置を中立位置（2048）として設定
- EEPROM保存で永続的に適用

**7. 位置補正を調整**
- 中立位置の微調整（-2047 ~ +2047 steps）
- 補正値0でリセット可能

#### セットアップの推奨手順

1. サーボをUSBで接続し電源を入れる
2. `python servo_setup.py` を実行
3. メニューから「1. サーボをスキャン」で検出を確認
4. 「5. クイックセットアップ」でID設定と動作確認
5. カメラを取り付けて正面を向ける
6. 「6. 中立位置を設定」で各サーボの中立位置を設定
7. 必要に応じて「7. 位置補正を調整」で微調整

## 使用方法

### face_tracker.py - メインプログラム

#### 開発モード（ディスプレイあり、サーボあり）

```bash
source venv/bin/activate
python face_tracker.py
```

カメラ映像が表示され、両目の検出状況とサーボ制御が確認できます。
- ESCキーで終了

#### サーボなしテストモード

```bash
python face_tracker.py --no-servo
```

カメラと顔検出のみをテストします（サーボは動きません）。

#### 実用モード（ディスプレイなし）

```bash
python face_tracker.py --no-display
```

画面表示なしで動作します。このモードでは：

**動作する機能**:
- ✅ カメラからの映像取得
- ✅ MediaPipeによる顔・虹彩の検出
- ✅ デッドゾーン制御（しきい値以下では動かない）
- ✅ PD制御によるサーボ追随
- ✅ 30フレームごとにコンソールへログ出力

**動作しない機能**:
- ❌ 画面への映像表示
- ❌ デッドゾーンの矩形や目の位置の描画

**メリット**:
- CPU負荷が軽い（画面描画処理がない）
- ヘッドレス運用可能（モニター不要）
- 自動起動に最適

実用・本番運用では`--no-display`モードを推奨します。

#### カスタムシリアルポート指定

```bash
python face_tracker.py --servo-port /dev/ttyACM0
```

デフォルト以外のシリアルポートを使用する場合。

### servo_setup.py - サーボセットアップツール

```bash
source venv/bin/activate
python servo_setup.py
```

インタラクティブメニューでサーボのID設定、中立位置設定、動作テストなどを実行します。

#### カスタムポート指定

```bash
# 別のUSBポートを使用
python servo_setup.py --port /dev/ttyACM0

# ボーレートを変更
python servo_setup.py --baudrate 115200
```

## 自動起動設定

Raspberry Piの起動時に自動的にプログラムを開始するには、systemdサービスとして登録します。

### セットアップ手順

```bash
cd /home/taiki/Documents/face_tracker
./install-autostart.sh
```

これで次回起動時から自動的にプログラムが開始されます（ディスプレイなしモードで動作）。

### サービス管理コマンド

```bash
# サービスをすぐに開始
sudo systemctl start face-tracker

# サービスを停止
sudo systemctl stop face-tracker

# サービスを再起動
sudo systemctl restart face-tracker

# サービスの状態を確認
sudo systemctl status face-tracker

# ログをリアルタイム表示
sudo journalctl -u face-tracker -f

# 自動起動を有効化
sudo systemctl enable face-tracker

# 自動起動を無効化
sudo systemctl disable face-tracker
```

### サービス設定のカスタマイズ

[face-tracker.service](face-tracker.service)ファイルを編集して設定を変更できます：

```bash
# サービスファイルを編集
sudo nano /etc/systemd/system/face-tracker.service

# 変更後は再読み込みと再起動
sudo systemctl daemon-reload
sudo systemctl restart face-tracker
```

例: ディスプレイモードで起動する場合は、`ExecStart`行の`--no-display`を削除します。

## 機能

- **両目検出**: MediaPipe Face Meshを使用して高精度に両目の位置を検出
- **3軸制御**:
  - パン: 画面中心に顔の中心を合わせる（左右）
  - チルト: 画面中心に顔の中心を合わせる（上下）
  - ロール: 両目が水平になるようにカメラを回転
- **穏やかな動作**: 低速・低加速度設定でスムーズに動作
- **デッドゾーン制御**: しきい値以下の小さなずれは無視して安定動作
  - パン/チルト: ±20ピクセル以内は動かさない
  - ロール: ±3度以内は動かさない
- **PD制御**: 比例・微分制御で滑らかな追随と振動抑制

## パラメータ調整

[face_tracker.py](face_tracker.py)の以下の値を変更して動作を調整できます：

```python
# デッドゾーン（この範囲内なら動かさない）
self.pan_dead_zone = 20    # ピクセル（左右）
self.tilt_dead_zone = 20   # ピクセル（上下）
self.roll_dead_zone = 3.0  # 度（回転）

# PD制御パラメータ
self.pan_kp = 0.3     # パンの比例ゲイン
self.pan_kd = 1.2     # パンの微分ゲイン
self.tilt_kp = 0.5    # チルトの比例ゲイン
self.tilt_kd = 0.8    # チルトの微分ゲイン
self.roll_kp = 0.3    # ロールの比例ゲイン
self.roll_kd = 1.0    # ロールの微分ゲイン

# サーボ速度・加速度（ServoControllerクラス内）
speed=800  # step/s (デフォルト2400より遅い)
acc=20     # 100 step/s^2単位
```

## トラブルシューティング

### サーボが検出されない

- USBケーブルの接続を確認
- シリアルポートを確認: `ls /dev/ttyASCM*`
- サーボの電源を確認
- ボーレート設定を確認（デフォルト: 1000000）
- `servo_setup.py`の「1. サーボをスキャン」で検出確認

### サーボのIDが分からない

- `servo_setup.py`を起動して「1. サーボをスキャン」を実行
- 検出されたIDが表示されます
- 工場出荷状態のIDは通常254または1

### 中立位置がずれている

- `servo_setup.py`の「6. 中立位置を設定」を使用
- カメラを手動で正面に向けてから実行
- または「7. 位置補正を調整」で微調整

### カメラが開けない

- カメラの接続を確認
- 他のアプリがカメラを使用していないか確認
- `v4l2-ctl --list-devices`でカメラデバイスを確認

### 動作が不安定

- `dead_zone`の値を大きくする
- ゲイン値（`pan_gain`, `tilt_gain`, `roll_gain`）を小さくする
- サーボの速度・加速度を下げる

## ファイル構成

```
face_tracker/
├── face_tracker.py          # メインプログラム（顔検出＋サーボ制御）
├── servo_setup.py           # サーボセットアップツール
├── requirements.txt         # 依存パッケージリスト
├── README.md               # このファイル
├── face-tracker.service    # systemdサービス設定ファイル
├── install-autostart.sh    # 自動起動セットアップスクリプト
└── venv/                   # 仮想環境（作成後）
```

## ライセンス

MIT License
