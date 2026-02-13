#!/bin/bash
# Face Tracker 診断スクリプト
# システムの状態を診断して問題を特定する

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DIAG_LOG="$SCRIPT_DIR/diagnosis_$(date +%Y%m%d_%H%M%S).log"

echo "Face Tracker 診断スクリプト" | tee "$DIAG_LOG"
echo "診断時刻: $(date)" | tee -a "$DIAG_LOG"
echo "========================================" | tee -a "$DIAG_LOG"

# システム情報
echo -e "\n[システム情報]" | tee -a "$DIAG_LOG"
uname -a | tee -a "$DIAG_LOG"
echo "稼働時間:" | tee -a "$DIAG_LOG"
uptime | tee -a "$DIAG_LOG"

# メモリ使用状況
echo -e "\n[メモリ使用状況]" | tee -a "$DIAG_LOG"
free -h | tee -a "$DIAG_LOG"

# ディスク使用状況
echo -e "\n[ディスク使用状況]" | tee -a "$DIAG_LOG"
df -h / | tee -a "$DIAG_LOG"

# CPUロード
echo -e "\n[CPU負荷]" | tee -a "$DIAG_LOG"
top -bn1 | head -20 | tee -a "$DIAG_LOG"

# face_trackerプロセスの確認
echo -e "\n[face_tracker プロセス]" | tee -a "$DIAG_LOG"
ps aux | grep -E "(face_tracker|python)" | grep -v grep | tee -a "$DIAG_LOG"

# カメラデバイスの確認
echo -e "\n[カメラデバイス]" | tee -a "$DIAG_LOG"
ls -l /dev/video* 2>&1 | tee -a "$DIAG_LOG"
v4l2-ctl --list-devices 2>&1 | tee -a "$DIAG_LOG"

# シリアルポートの確認
echo -e "\n[シリアルポート]" | tee -a "$DIAG_LOG"
ls -l /dev/ttyACM* /dev/ttyUSB* 2>&1 | tee -a "$DIAG_LOG"
dmesg | tail -50 | grep -E "(tty|USB)" | tee -a "$DIAG_LOG"

# USB デバイス
echo -e "\n[USB デバイス]" | tee -a "$DIAG_LOG"
lsusb | tee -a "$DIAG_LOG"

# ログファイルのサイズ
echo -e "\n[ログファイル]" | tee -a "$DIAG_LOG"
ls -lh "$SCRIPT_DIR"/*.log 2>&1 | tee -a "$DIAG_LOG"

# ログファイルの最後の100行
if [ -f "$SCRIPT_DIR/face_tracker.log" ]; then
    echo -e "\n[face_tracker.log (最後の100行)]" | tee -a "$DIAG_LOG"
    tail -100 "$SCRIPT_DIR/face_tracker.log" | tee -a "$DIAG_LOG"
fi

# カーネルメッセージ（エラー関連）
echo -e "\n[カーネルメッセージ (エラー・警告)]" | tee -a "$DIAG_LOG"
dmesg | tail -100 | grep -E "(error|warn|fail)" -i | tee -a "$DIAG_LOG"

# システムログ（最近のエラー）
echo -e "\n[システムログ (最近のエラー)]" | tee -a "$DIAG_LOG"
journalctl -xe --no-pager -n 50 | grep -E "(error|fail)" -i | tee -a "$DIAG_LOG"

# ファイルディスクリプタの使用状況
if [ -f "$SCRIPT_DIR/face_tracker.pid" ]; then
    PID=$(cat "$SCRIPT_DIR/face_tracker.pid")
    if ps -p "$PID" > /dev/null 2>&1; then
        echo -e "\n[ファイルディスクリプタ使用状況 (PID: $PID)]" | tee -a "$DIAG_LOG"
        ls -l /proc/$PID/fd/ 2>&1 | wc -l | tee -a "$DIAG_LOG"
        ls -l /proc/$PID/fd/ 2>&1 | tee -a "$DIAG_LOG"
    fi
fi

echo -e "\n========================================" | tee -a "$DIAG_LOG"
echo "診断完了: $DIAG_LOG" | tee -a "$DIAG_LOG"
