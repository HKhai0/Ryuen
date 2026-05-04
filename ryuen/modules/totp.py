import os
import sqlite3
import pyotp
import re
import json

# Cấu hình Database
DB_PATH = os.path.join(os.path.dirname(__file__), "totp_data.db")
CONFIG_FILE = "rsmode_config.json" # Dùng để check admin

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    # Bảng lưu mã
    c.execute('CREATE TABLE IF NOT EXISTS totp_multi (uid TEXT, name TEXT, secret TEXT, PRIMARY KEY(uid, name))')
    # Bảng lưu cài đặt style (msg hoặc react)
    c.execute('CREATE TABLE IF NOT EXISTS totp_settings (uid TEXT PRIMARY KEY, style TEXT)')
    conn.commit()
    conn.close()

init_db()

# --- CÁC HÀM TƯƠNG TÁC DATABASE ---
def get_secret(uid, name):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT secret FROM totp_multi WHERE uid = ? AND name = ?', (uid, name))
    row = c.fetchone()
    conn.close()
    return row[0] if row else None

def get_all_names(uid):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT name FROM totp_multi WHERE uid = ?', (uid,))
    rows = c.fetchall()
    conn.close()
    return [r[0] for r in rows]

def set_secret(uid, name, secret):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('INSERT OR REPLACE INTO totp_multi VALUES (?, ?, ?)', (uid, name, secret))
    conn.commit()
    conn.close()

def del_secret(uid, name):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('DELETE FROM totp_multi WHERE uid = ? AND name = ?', (uid, name))
    conn.commit()
    conn.close()

def get_style(uid):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT style FROM totp_settings WHERE uid = ?', (uid,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else "msg"

def set_style(uid, style):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('INSERT OR REPLACE INTO totp_settings VALUES (?, ?)', (uid, style))
    conn.commit()
    conn.close()

def is_admin(uid):
    """Kiểm tra quyền Admin từ file config của RSMODE"""
    if not os.path.exists(CONFIG_FILE): return False
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return str(uid) in json.load(f).get("admins", [])
    except: return False

def clean_base32(raw_text):
    """Tự động fix OCR và lọc rác"""
    clean_text = raw_text.replace("8", "B").replace("0", "O").replace("1", "I")
    return re.sub(r'[^A-Z2-7]', '', clean_text.upper())

# --- LOGIC CHÍNH: TOTP QUẢN LÝ ---
def handle_totp(data, parts):
    author_id = str(data.get("author_id"))
    thread_type = str(data.get("thread_type", ""))
    is_group = "2" in thread_type or "GROUP" in thread_type.upper()

    if len(parts) < 2:
        return {
            "method": "reply",
            "content": """Có lỗi xảy ra đối với cú pháp lệnh

🛠️ HƯỚNG DẪN SỬ DỤNG TOTP (Remake) 🛠️
🔹 [LỆNH CƠ BẢN]
- totp add [tên] [mã_base32]: Thêm mã mới
- totp get [tên]: Lấy mã OTP (2FA)
- totp list: Xem danh sách các mã đã lưu
- totp del [tên]: Xóa mã khỏi hệ thống

🔹 [LỆNH CHUYỂN ĐỔI & CHIA SẺ]
- totp style [msg/react]: Đổi kiểu hiển thị mã
- totp copy [tên] [@tag/quote]: Tặng bản sao mã cho người khác (bạn vẫn giữ mã gốc)
- totp transfer [tên] [@tag/quote]: Chuyển nhượng mã (bạn sẽ mất mã này)
- totp secretcode [tên]: Xem lại mã Base32 gốc

🔹 [QUẢN TRỊ & TIỆN ÍCH]
- totp list [UID]: Xem list mã của người khác (Admin only)
- 2fa [mã_base32]: Lấy nhanh OTP mà không cần lưu
- totp info: Thông tin tác giả"""
        }

    action = parts[1].lower()

    # 1. THÊM MÃ
    if action == "add":
        if len(parts) < 4:
            return {"method": "reply", "content": "❌ Cú pháp: totp add [tên_mã] [secretcode]"}
        name_code = parts[2].lower()
        secret = clean_base32("".join(parts[3:]))
        try:
            pyotp.TOTP(secret).now()
            set_secret(author_id, name_code, secret)
            return {"method": "reply", "content": f"✅ Đã lưu mã bảo mật cho: {name_code.upper()}"}
        except Exception:
            return {"method": "reply", "content": "❌ Mã Base32 không hợp lệ!"}

    # 2. CÀI ĐẶT STYLE HIỂN THỊ
    elif action == "style":
        if len(parts) < 3 or parts[2].lower() not in ["msg", "react"]:
            return {"method": "reply", "content": "❌ Cú pháp: totp style [msg/react]"}
        new_style = parts[2].lower()
        set_style(author_id, new_style)
        return {"method": "reply", "content": f"✅ Đã đổi style hiển thị thành: {new_style.upper()}"}

    # 3. CHUYỂN NHƯỢNG MÃ (Mất mã gốc)
    elif action == "transfer":
        if len(parts) < 3: return {"method": "reply", "content": "❌ Cú pháp: totp transfer [tên_mã] [@tag/quote]"}
        name_code = parts[2].lower()
        target_id = data.get("target_id")
        if not target_id: return {"method": "reply", "content": "❌ Vui lòng Tag hoặc Quote người nhận."}
        
        secret = get_secret(author_id, name_code)
        if not secret: return {"method": "reply", "content": f"❌ Không tìm thấy mã '{name_code}'."}
        
        set_secret(target_id, name_code, secret)
        del_secret(author_id, name_code)
        return {"method": "reply", "content": f"✅ Đã TRANSFER quyền lấy mã '{name_code.upper()}' cho ID: {target_id}"}

    # 4. COPY MÃ (Giữ lại mã gốc)
    elif action == "copy":
        if len(parts) < 3: return {"method": "reply", "content": "❌ Cú pháp: totp copy [tên_mã] [@tag/quote]"}
        name_code = parts[2].lower()
        target_id = data.get("target_id")
        if not target_id: return {"method": "reply", "content": "❌ Vui lòng Tag hoặc Quote người nhận."}
        
        secret = get_secret(author_id, name_code)
        if not secret: return {"method": "reply", "content": f"❌ Không tìm thấy mã '{name_code}'."}
        
        set_secret(target_id, name_code, secret)
        return {"method": "reply", "content": f"✅ Đã COPY mã '{name_code.upper()}' cho ID: {target_id}"}

    # 5. XEM DANH SÁCH MÃ
    elif action == "list":
        target_uid = author_id
        is_checking_others = False
        
        if len(parts) >= 3 or data.get("target_id"):
            if not is_admin(author_id):
                return {"method": "reply", "content": "⛔ Chỉ Admin mới được xem list của người khác!"}
            target_uid = data.get("target_id") or parts[2]
            is_checking_others = True

        names = get_all_names(target_uid)
        if not names:
            return {"method": "reply", "content": f"❌ ID {target_uid} chưa lưu mã TOTP nào." if is_checking_others else "❌ Bạn chưa lưu mã TOTP nào."}
        msg = f"📋 List 2FA của {'bạn' if not is_checking_others else target_uid}:\n" + "\n".join([f"- {n.upper()}" for n in names])
        return {"method": "reply", "content": msg}

    # 6. LẤY MÃ OTP
    elif action == "get":
        if len(parts) < 3: return {"method": "reply", "content": "❌ Cú pháp: totp get [tên_mã]"}
        name_code = parts[2].lower()
        secret = get_secret(author_id, name_code)
        if not secret: return {"method": "reply", "content": f"❌ Không tìm thấy '{name_code}'."}
        
        code = pyotp.TOTP(secret).now()
        style = get_style(author_id)
        
        if style == "msg":
            return {"method": "reply", "content": f"🔑 Đang lấy mã...\nOTP [{name_code.upper()}]:\n{code}"}
        else:
            return {"method": "react", "content": f"{code}"}

    # 7. XEM SECRET CODE (Có cảnh báo an toàn)
    elif action == "secretcode":
        if len(parts) < 3: return {"method": "reply", "content": "❌ Cú pháp: totp secretcode [tên_mã]"}
        name_code = parts[2].lower()
        
        # Check an toàn nếu đang ở trong Nhóm
        if is_group and "--group" not in parts:
            return {
                "method": "reply", 
                "content": f"⚠️ CẢNH BÁO: Việc hiển thị Secret Code trong nhóm có thể làm mất tài khoản!\n\nNếu bạn chắc chắn muốn xem, hãy nhập lại lệnh kèm theo tham số ép buộc:\n👉 totp secretcode {name_code} --group"
            }
            
        secret = get_secret(author_id, name_code)
        if not secret: return {"method": "reply", "content": f"❌ Không tìm thấy '{name_code}'."}
        return {"method": "reply", "content": f"🤫 Secret Code của [{name_code.upper()}]:\n{secret}"}

    # 8. XÓA MÃ
    elif action == "del":
        if len(parts) < 3: return {"method": "reply", "content": "❌ Cú pháp: totp del [tên_mã]"}
        name_code = parts[2].lower()
        if not get_secret(author_id, name_code): return {"method": "reply", "content": f"❌ Không tìm thấy '{name_code}'."}
        del_secret(author_id, name_code)
        return {"method": "reply", "content": f"✅ Đã xóa mã '{name_code.upper()}'."}

    # 9. THÔNG TIN MODULE
    elif action == "info":
        return {
            "method": "reply", 
            "content": "ℹ️ 1 bản google authenticator remake , không khuyến khích sử dụng , tạo ra với mục đích lấy mã nhanh ngay trên chat platform"
        }

    return {"method": "reply", "content": "❌ Lệnh không hợp lệ."}

# --- LOGIC PHỤ: 2FA LẤY NHANH ---
def handle_2fa_quick(data, parts):
    """2fa {secretcode} (Lấy nhanh TOTP mà không lưu)"""
    if len(parts) < 2:
        return {"method": "reply", "content": "❌ Cú pháp: 2fa [secretcode_base32]"}
    
    secret = clean_base32("".join(parts[1:]))
    try:
        code = pyotp.TOTP(secret).now()
        return {"method": "reply", "content": f"⚡ Quick 2FA:\n{code}"}
    except Exception as e:
        return {"method": "reply", "content": f"❌ Mã Base32 không hợp lệ!"}

# --- ĐĂNG KÝ VỚI BACKEND ---
def ryuen_get():
    return {
        "totp": handle_totp,
        "2fa": handle_2fa_quick
    }

