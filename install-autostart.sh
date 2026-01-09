#!/bin/bash

# Face Tracker自動起動セットアップスクリプト

echo "=== Face Tracker 自動起動設定 ==="
echo ""

# サービスファイルをsystemdディレクトリにコピー
echo "1. サービスファイルをコピー中..."
sudo cp face-tracker.service /etc/systemd/system/

# systemdを再読み込み
echo "2. systemdを再読み込み中..."
sudo systemctl daemon-reload

# サービスを有効化（自動起動設定）
echo "3. サービスを有効化中..."
sudo systemctl enable face-tracker.service

echo ""
echo "=== セットアップ完了 ==="
echo ""
echo "次回起動時から自動的にプログラムが開始されます。"
echo ""
echo "便利なコマンド："
echo "  sudo systemctl start face-tracker    # すぐに開始"
echo "  sudo systemctl stop face-tracker     # 停止"
echo "  sudo systemctl restart face-tracker  # 再起動"
echo "  sudo systemctl status face-tracker   # 状態確認"
echo "  sudo journalctl -u face-tracker -f   # ログをリアルタイム表示"
echo "  sudo systemctl disable face-tracker  # 自動起動を無効化"
echo ""
