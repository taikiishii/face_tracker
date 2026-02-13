#!/bin/bash
# Face Tracker 監視スクリプト
# プログラムの状態を定期的にチェックし、問題があれば再起動

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
LOG_FILE="$SCRIPT_DIR/monitor.log"
PID_FILE="$SCRIPT_DIR/face_tracker.pid"
PYTHON_SCRIPT="$SCRIPT_DIR/face_tracker.py"

# ログに記録する関数
log_message() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# プロセスが実行中かチェック
is_running() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if ps -p "$PID" > /dev/null 2>&1; then
            return 0  # 実行中
        fi
    fi
    return 1  # 停止中
}

# プロセスの健全性をチェック
check_health() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        
        # メモリ使用量をチェック（MB単位）
        MEM_MB=$(ps -p "$PID" -o rss= | awk '{print $1/1024}')
        if [ -n "$MEM_MB" ]; then
            MEM_THRESHOLD=600  # 600MB以上で警告
            if (( $(echo "$MEM_MB > $MEM_THRESHOLD" | bc -l) )); then
                log_message "警告: メモリ使用量が高い: ${MEM_MB}MB"
                return 1
            fi
        fi
        
        # プロセスがゾンビ状態でないかチェック
        STATE=$(ps -p "$PID" -o state= | tr -d ' ')
        if [ "$STATE" = "Z" ]; then
            log_message "エラー: プロセスがゾンビ状態"
            return 1
        fi
        
        # ログファイルが更新されているかチェック（最後の更新から10分以内）
        if [ -f "$SCRIPT_DIR/face_tracker.log" ]; then
            LAST_MODIFIED=$(stat -c %Y "$SCRIPT_DIR/face_tracker.log")
            CURRENT_TIME=$(date +%s)
            TIME_DIFF=$((CURRENT_TIME - LAST_MODIFIED))
            
            # 10分 = 600秒
            if [ $TIME_DIFF -gt 600 ]; then
                log_message "警告: ログファイルが10分以上更新されていません"
                return 1
            fi
        fi
        
        return 0  # 正常
    fi
    return 1  # PIDファイルが存在しない
}

# プロセスを開始
start_process() {
    log_message "Face Trackerを起動します"
    
    cd "$SCRIPT_DIR"
    nohup python3 "$PYTHON_SCRIPT" --no-display > /dev/null 2>&1 &
    PID=$!
    echo $PID > "$PID_FILE"
    
    log_message "Face Trackerを起動しました (PID: $PID)"
}

# プロセスを停止
stop_process() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        log_message "Face Trackerを停止します (PID: $PID)"
        
        # 正常終了を試みる
        kill "$PID" 2>/dev/null
        
        # 5秒待つ
        sleep 5
        
        # まだ実行中なら強制終了
        if ps -p "$PID" > /dev/null 2>&1; then
            log_message "強制終了します"
            kill -9 "$PID" 2>/dev/null
        fi
        
        rm -f "$PID_FILE"
        log_message "Face Trackerを停止しました"
    fi
}

# メインループ
log_message "監視スクリプトを開始しました"

while true; do
    if is_running; then
        # プロセスが実行中
        if check_health; then
            # 正常
            log_message "正常稼働中 (PID: $(cat $PID_FILE))"
        else
            # 異常検出
            log_message "異常を検出しました。再起動します"
            stop_process
            sleep 5
            start_process
        fi
    else
        # プロセスが停止している
        log_message "プロセスが停止しています。起動します"
        start_process
    fi
    
    # 5分待機
    sleep 300
done
