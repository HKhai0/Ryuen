import questionary
import os
import time
import shutil
import requests
import json

# --- MÃ MÀU ANSI CHUẨN LINUX ---
C = '\033[96m'  # Cyan
M = '\033[95m'  # Magenta
G = '\033[92m'  # Green
Y = '\033[93m'  # Yellow
R = '\033[91m'  # Red
RESET = '\033[0m' 

def clear_screen():
    os.system('clear')

def print_banner():
    term_width = shutil.get_terminal_size((80, 20)).columns
    box_width = min(term_width - 2, 65) 
    title = "🚀 TMUX MULTI-TOOL PRO 🚀"
    title_length = 25 
    
    padding = (box_width - title_length) // 2
    pad_left = " " * padding
    pad_right = " " * (box_width - title_length - padding)

    print(f"{M}╔" + "═" * box_width + "╗")
    print(f"{M}║" + pad_left + f"{C}{title}{M}" + pad_right + "║")
    print(f"{M}╚" + "═" * box_width + f"╝\n{RESET}")

def is_tmux_running():
    return os.system("tmux has-session -t zlapibot 2>/dev/null") == 0

def trigger_rs_command():
    print(f"\n{Y}[+] Đang bắn tin nhắn ảo để kích hoạt module 'rs.py'...{RESET}")
    try:
        # Cố gắng lấy ID Admin để lách qua trạm kiểm duyệt của module rs
        admin_id = "terminal_admin"
        try:
            with open("rsmode_config.json", "r", encoding="utf-8") as f:
                cfg = json.load(f)
                if cfg.get("admins"):
                    admin_id = cfg["admins"][0]
        except:
            pass

        # Tạo một payload giả mạo Zalo gửi chữ "rs"
        fake_payload = {
            "event_type": "onMessage",
            "data": {
                "msg_text": "rs",
                "author_id": admin_id,
                "thread_id": "terminal_trigger",
                "timestamp": str(int(time.time() * 1000)),
                "mid": f"terminal_{int(time.time())}"
            }
        }
        
        # Bắn thẳng vào cổng Webhook của Backend
        requests.post("http://127.0.0.1:6736/webhook", json=fake_payload, timeout=3)
        print(f"{C}✅ Đã lừa Backend thành công! Hệ thống đang tự nạp lại Modules...{RESET}")
    except Exception as e:
        print(f"{R}❌ Thất bại: Không thể kết nối tới Backend. ({e}){RESET}")

def main_menu():
    while True:
        clear_screen()
        print_banner()

        choice = questionary.select(
            "Sử dụng (↑/↓) để chọn, nhấn Enter để chạy:",
            choices=[
                "▶️  Khởi động TOÀN BỘ hệ thống (Chạy ngầm Tmux)",
                "🔄 Khởi động lại RIÊNG Backend (Kích hoạt lệnh 'rs')",
                "👀 Vào xem Log hệ thống (Attach Tmux)",
                "🛑 Tắt toàn bộ Bot (Kill Tmux)",
                "❌ Thoát Menu"
            ],
            style=questionary.Style([
                ('pointer', 'fg:green bold'),
                ('highlighted', 'fg:cyan bold'),
            ])
        ).ask()

        # --- LOGIC XỬ LÝ ---
        if choice == "▶️  Khởi động TOÀN BỘ hệ thống (Chạy ngầm Tmux)":
            print(f"\n{Y}[+] Đang dọn dẹp session cũ (nếu có)...{RESET}")
            os.system("tmux kill-session -t zlapibot 2>/dev/null")
            
            print(f"{G}[+] Đang tạo không gian ảo Tmux...{RESET}")
            
            # CÁCH CHUẨN: Mở bash trước, sau đó mới gửi lệnh để chống sập cửa sổ
            os.system("tmux new-session -d -s zlapibot -n 'core'")
            os.system("tmux send-keys -t zlapibot:0.0 'python3 main.py' C-m")
            
            os.system("tmux split-window -t zlapibot:0 -h")
            os.system("tmux send-keys -t zlapibot:0.1 'python3 backend.py' C-m")
            
            print(f"{C}✅ Đã nổ máy thành công! Hệ thống đang chạy NGẦM.{RESET}")
            input(f"\nNhấn Enter để quay lại Menu...")

        elif choice == "🔄 Khởi động lại RIÊNG Backend (Kích hoạt lệnh 'rs')":
            if not is_tmux_running():
                print(f"\n{R}⚠️ Hệ thống chưa được khởi động! Vui lòng chọn Khởi động TOÀN BỘ trước.{RESET}")
            else:
                trigger_rs_command()
            input(f"\nNhấn Enter để quay lại Menu...")

        elif choice == "👀 Vào xem Log hệ thống (Attach Tmux)":
            if not is_tmux_running():
                print(f"\n{R}⚠️ Không có hệ thống nào đang chạy!{RESET}")
                input(f"\nNhấn Enter để quay lại Menu...")
            else:
                print(f"\n{C}Đang mở Tmux... {Y}(LƯU Ý: Nhấn [Ctrl + b] sau đó thả ra và bấm phím [d] để quay lại Menu){RESET}")
                time.sleep(2)
                os.system("tmux attach-session -t zlapibot")

        elif choice == "🛑 Tắt toàn bộ Bot (Kill Tmux)":
            os.system("tmux kill-session -t zlapibot 2>/dev/null")
            print(f"\n{R}☠️ Đã tiêu diệt toàn bộ tiến trình của Bot!{RESET}")
            input(f"\nNhấn Enter để quay lại Menu...")

        elif choice == "❌ Thoát Menu" or choice is None:
            print(f"\n{C}Đã thoát Menu. {Y}(Bot vẫn đang chạy ngầm nếu bro đã bật nhé!){RESET}")
            time.sleep(1)
            clear_screen()
            break

if __name__ == "__main__":
    main_menu()