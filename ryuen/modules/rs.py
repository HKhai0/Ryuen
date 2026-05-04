import sys
import os
import json
import time
import threading
import requests
from datetime import datetime
try:
    from colorama import Fore
except ImportError:
    class Fore: YELLOW = ""; GREEN = ""; CYAN = ""; RED = ""; RESET = ""

des = {
    'version': "2.0.0",
    'credits': "Python Is Trash (Lê Hữu Khải) & Zlapi Pro",
    'description': "Restart thủ công & Tự động Restart mỗi 30 phút theo giờ mạng"
}

CONFIG_FILE = "rsmode_config.json"

# ==========================================
# CÁC HÀM TIỆN ÍCH (CONFIG)
# ==========================================
def load_config():
    if not os.path.exists(CONFIG_FILE):
        default_cfg = {"mode": "all", "admins": [], "allowlist": []}
        save_config(default_cfg)
        return default_cfg
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return {"mode": "all", "admins": [], "allowlist": []}

def save_config(cfg):
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(cfg, f, ensure_ascii=False, indent=4)

# ==========================================
# LOGIC RESTART CỐT LÕI
# ==========================================
def execute_restart(silent=False):
    """Tiến hành khởi động lại Backend"""
    if not silent:
        time.sleep(1.5) # Chờ xíu để Backend kịp báo tin nhắn về Zalo (nếu RS thủ công)
    
    print(f"\n{Fore.CYAN}🔄 [HỆ THỐNG] Đang khởi động lại Backend để làm mới & nạp modules...{Fore.RESET}")
    python = sys.executable
    os.execl(python, python, *sys.argv)

# ==========================================
# LOGIC AUTO RESTART (THỜI GIAN MẠNG)
# ==========================================
def get_network_time():
    """Lấy thời gian chuẩn từ mạng nội bộ/internet"""
    try:
        # Lấy giờ múi GMT+7 (Hồ Chí Minh) từ API Thế giới
        res = requests.get("http://worldtimeapi.org/api/timezone/Asia/Ho_Chi_Minh", timeout=3)
        dt_str = res.json()['datetime']
        # Cắt chuỗi lấy phần yyyy-mm-ddThh:mm:ss (Bỏ qua phần mili-giây và múi giờ)
        clean_str = dt_str.split('+')[0][:19]
        return datetime.strptime(clean_str, "%Y-%m-%dT%H:%M:%S")
    except Exception:
        # Nếu rớt mạng hoặc API sập, fallback về giờ của máy (Termux/Windows)
        return datetime.now()

def auto_restart_scheduler():
    """Luồng đếm ngược tự động restart vào mốc xx:00 hoặc xx:30"""
    now = get_network_time()
    
    # Tính toán xem mốc tiếp theo là phút 30 hay phút 00 (của giờ tiếp theo)
    if now.minute < 30:
        target_minute = 30
        target_hour = now.hour
    else:
        target_minute = 0
        target_hour = (now.hour + 1) % 24

    # Tính ra chính xác CẦN CHỜ BAO NHIÊU GIÂY NỮA
    minutes_to_wait = (target_minute - now.minute) % 60
    if minutes_to_wait == 0: 
        minutes_to_wait = 30 # Tránh trường hợp vừa khởi động vào đúng phút 00/30
        
    seconds_to_wait = (minutes_to_wait * 60) - now.second
    target_time_str = f"{target_hour:02d}:{target_minute:02d}:00"
    
    print(f"{Fore.YELLOW}⏰ [Auto-RS] Đã đồng bộ giờ Mạng. Hẹn giờ Restart tự động vào lúc {target_time_str} (sau {int(seconds_to_wait)}s nữa).{Fore.RESET}")
    
    # Cho luồng này ngủ yên cho đến đúng mốc thời gian đó
    time.sleep(seconds_to_wait)
    
    print(f"\n{Fore.GREEN}⏰ [Auto-RS] Đã tới mốc {target_time_str}! Tiến hành dọn dẹp và Restart...{Fore.RESET}")
    execute_restart(silent=True)

# KÍCH HOẠT AUTO RESTART NGAY KHI MODULE NÀY ĐƯỢC LOAD LÊN
threading.Thread(target=auto_restart_scheduler, daemon=True).start()

# ==========================================
# LỆNH RESTART THỦ CÔNG TỪ ZALO
# ==========================================
def handle_rs(data, parts):
    author_id = str(data.get("author_id"))
    cfg = load_config()
    admins = cfg.get("admins", [])

    # Chỉ Admin mới được quyền dùng lệnh này
    if author_id not in admins and len(admins) > 0:
        return {"method": "react", "content": "⛔"}

    try:
        # Kích hoạt luồng chạy ngầm để bot kịp trả lời tin nhắn trước khi chết
        threading.Thread(target=execute_restart, args=(False,), daemon=True).start()

        return {
            "method": "reply", 
            "content": "🔄 Đang khởi động lại hệ thống...\n⏳ Quá trình này sẽ nạp lại toàn bộ Modules, vui lòng đợi 3s!"
        }
    except Exception as e:
        return {"method": "reply", "content": f"❌ Lỗi xảy ra khi restart bot: {str(e)}"}

# ==========================================
# ĐĂNG KÝ MODULE VỚI NÃO BỘ
# ==========================================
def ryuen_get():
    return {
        'rs': handle_rs,
        'restart': handle_rs
    }