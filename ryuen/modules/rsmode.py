import json
import os

CONFIG_FILE = "rsmode_config.json"

# --- CÁC HÀM TIỆN ÍCH ---
def load_config():
    if not os.path.exists(CONFIG_FILE):
        # Khởi tạo mặc định nếu chưa có file
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

# --- LOGIC XỬ LÝ LỆNH ---
def handle_rsmode(data, parts):
    author_id = str(data.get("author_id"))
    thread_id = str(data.get("thread_id"))
    target_id = data.get("target_id") # Lấy UID từ Mentions/Quote do main.py gửi sang
    
    cfg = load_config()
    admins = cfg.get("admins", [])

    # Chỉ Admin mới được quyền dùng lệnh này để quản trị bot
    if author_id not in admins and len(admins) > 0:
        return {"method": "react", "content": "❌"}

    if len(parts) < 2:
        return {
            "method": "reply",
            "content": f"🛡️ [RSMODE SYSTEM]\n- Chế độ hiện tại: {cfg['mode'].upper()}\n\n"
                       f"1. rsmode [all|admin|allow]: Đổi chế độ\n"
                       f"2. rsmode addadmin [@tag]: Thêm quyền Admin\n"
                       f"3. rsmode addallow: Thêm nhóm/user vào Allowlist\n"
                       f"4. rsmode status: Xem chi tiết cấu hình"
        }

    action = parts[1].lower()

    # 1. ĐỔI CHẾ ĐỘ PHẢN HỒI
    if action in ["all", "admin", "allow"]:
        cfg["mode"] = action
        save_config(cfg)
        return {"method": "reply", "content": f"✅ Đã chuyển sang chế độ: {action.upper()}"}

    # 2. QUẢN LÝ ADMIN (Thêm/Xóa)
    elif action == "addadmin":
        if not target_id:
            return {"method": "reply", "content": "❌ Vui lòng Tag hoặc Quote người muốn cấp quyền Admin."}
        if target_id not in cfg["admins"]:
            cfg["admins"].append(target_id)
            save_config(cfg)
            return {"method": "reply", "content": f"✅ Đã thêm {target_id} làm Admin."}
        return {"method": "reply", "content": "⚠️ Người này đã là Admin rồi."}

    # 3. QUẢN LÝ ALLOWLIST (Cho phép nhóm hoặc cá nhân)
    elif action == "addallow":
        # Nếu gõ lệnh trong nhóm mà không tag ai -> Thêm nguyên cái Nhóm đó vào list
        uid_to_allow = target_id if target_id else thread_id
        if uid_to_allow not in cfg["allowlist"]:
            cfg["allowlist"].append(uid_to_allow)
            save_config(cfg)
            return {"method": "reply", "content": f"✅ Đã thêm ID {uid_to_allow} vào danh sách được phép."}
        return {"method": "reply", "content": "⚠️ ID này đã có trong danh sách rồi."}

    # 4. XEM TRẠNG THÁI CHI TIẾT
    elif action == "status":
        msg = (f"📊 [RSMODE STATUS]\n"
               f"- Mode: {cfg['mode'].upper()}\n"
               f"- Số Admin: {len(cfg['admins'])}\n"
               f"- VIP List: {len(cfg['allowlist'])} ID")
        return {"method": "reply", "content": msg}

    return {"method": "reply", "content": "❌ Lệnh không hợp lệ."}

# --- ĐĂNG KÝ VỚI BACKEND ---
def ryuen_get():
    return {
        "rsmode": handle_rsmode
    }

