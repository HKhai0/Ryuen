import base64
import ast 
import time
import os
import sys
import json
import threading
import requests
from flask import Flask, request, jsonify
import logging
import httpx
from zlapi.models import Message, ThreadType
from zlapi import ZaloAPI
from colorama import Fore, init

# Load toàn bộ biến (API_KEY, SECRET_KEY, IMEI, SESSION_COOKIES) từ config
from config import *

init(autoreset=True)
colors = [Fore.RED, Fore.YELLOW, Fore.GREEN, Fore.CYAN, Fore.BLUE, Fore.MAGENTA, Fore.WHITE]
BANNER = r"""
██╗  ██╗██╗   ██╗██╗   ██╗    ██╗  ██╗██╗  ██╗ █████╗ ██╗
██║  ██║██║   ██║██║   ██║    ██║ ██╔╝██║  ██║██╔══██╗██║
███████║██║   ██║██║   ██║    █████╔╝ ███████║███████║██║
██╔══██║██║   ██║██║   ██║    ██╔═██╗ ██╔══██║██╔══██║██║
██║  ██║╚██████╔╝╚██████╔╝    ██║  ██╗██║  ██║██║  ██║██║
╚═╝  ╚═╝ ╚═════╝  ╚═════╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝╚═╝
"""
for i, char in enumerate(BANNER):
    print(colors[i % len(colors)] + char, end='')

BACKEND_URL = "http://127.0.0.1:6736/webhook"

# ==========================================
# BỘ NHỚ ĐỆM (CACHE) - CHỐNG LỖI -69 VÀ LƯU MESSAGE
# ==========================================
USER_CACHE = {}
GROUP_CACHE = {}
MSG_CACHE = {} # Lưu tạm message_object để thả react

def serialize_zalo_obj(obj):
    if isinstance(obj, (int, float, str, bool, type(None))): return obj
    elif isinstance(obj, dict): return {k: serialize_zalo_obj(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)): return [serialize_zalo_obj(item) for item in obj]
    elif hasattr(obj, '__dict__'): return serialize_zalo_obj(obj.__dict__)
    else: return str(obj)

# ==========================================
# CỔNG LẮNG NGHE TỪ WEB (FLASK MINI - PORT 3667)
# ==========================================
app_bot = Flask(__name__)

@app_bot.route('/bot_send_local_img', methods=['POST'])
def bot_send_local_img():
    """Cổng nhận ảnh từ Backend gửi sang để đẩy lên Zalo"""
    data = request.json
    thread_id = data.get("thread_id")
    text = data.get("text", "")
    image_path = data.get("image_path")
    
    # Xác định kiểu thread (Nhóm hoặc Cá nhân)
    t_type_str = str(data.get("thread_type", ""))
    t_type = ThreadType.GROUP if "GROUP" in t_type_str.upper() or "2" in t_type_str else ThreadType.USER

    if not global_client or not thread_id or not image_path:
        return jsonify({"status": "error", "message": "Thiếu dữ liệu gửi ảnh"})

    try:
        msg_obj = Message(text=text) if text else None
        
        # Gửi ảnh từ đường dẫn nội bộ
        global_client.sendLocalImage(
            imagePath=image_path, 
            message=msg_obj, 
            thread_id=thread_id, 
            thread_type=t_type
        )
        print(f"{Fore.BLUE}🖼️ [Local Send] Đã gửi ảnh thành công tới: {thread_id}")
        
        # Tự động dọn rác sau khi gửi để nhẹ máy Note 14
        if os.path.exists(image_path):
            os.remove(image_path)
            
        return jsonify({"status": "success"})
    except Exception as e:
        if os.path.exists(image_path): os.remove(image_path)
        return jsonify({"status": "error", "message": str(e)})
logging.getLogger('werkzeug').setLevel(logging.ERROR) # Tắt log rác

@app_bot.route('/bot_react', methods=['POST'])
def bot_react():
    """Hứng lệnh thả react từ Web Backend truyền sang"""
    data = request.json
    mid = str(data.get("mid"))
    icon = data.get("icon")
    passed_object = data.get("object") 
    thread_id = data.get("thread_id") 
    
    # --- PHỤC HỒI THREAD_TYPE CHUẨN ENUM ---
    t_type_str = str(data.get("thread_type", ""))
    if "GROUP" in t_type_str.upper() or "2" in t_type_str:
        t_type = ThreadType.GROUP
    else:
        t_type = ThreadType.USER

    obj_to_react = None

    # 1. Tìm trong RAM trước (Nếu Bot chưa bị restart)
    if mid in MSG_CACHE:
        msg_data = MSG_CACHE[mid]
        obj_to_react = msg_data["obj"]
        t_type = msg_data["thread_type"] # Dùng nguyên bản trong RAM
        thread_id = msg_data["thread_id"]

    # 2. Nếu không có trong RAM, tái tạo từ dữ liệu Web truyền sang
    elif passed_object:
        try:
            # Ép kiểu an toàn thành Dict
            if isinstance(passed_object, str):
                passed_dict = ast.literal_eval(passed_object)
            else:
                passed_dict = passed_object 
            
            # --- TÁI TẠO THỂ XÁC CHUẨN ZLAPI ---
            obj_to_react = Message(text=passed_dict.get('content', ''))
            
            for key, val in passed_dict.items():
                setattr(obj_to_react, key, val)
            
            if not getattr(obj_to_react, 'msgId', None):
                setattr(obj_to_react, 'msgId', passed_dict.get('msgId') or passed_dict.get('cMsgId') or mid)
            if not getattr(obj_to_react, 'cliMsgId', None):
                setattr(obj_to_react, 'cliMsgId', passed_dict.get('cliMsgId') or passed_dict.get('cMsgId') or mid)
            
        except Exception as e:
            print(f"{Fore.RED}❌ Lỗi tái tạo Object: {e}")

    # 3. THỰC THI THẢ REACT
    if obj_to_react and global_client:
        try:
            global_client.sendReaction(
                messageObject=obj_to_react, 
                reactionIcon=icon, 
                thread_id=thread_id, 
                thread_type=t_type
            )
            print(f"{Fore.GREEN}🚀 Đã thả icon [{icon}] thành công (Khôi phục từ DB Web)")
            return jsonify({"status": "success"})
        except Exception as e:
            print(f"{Fore.RED}❌ Lỗi zlapi sendReaction: {e}")
            return jsonify({"status": "error", "message": str(e)})
            
    return jsonify({"status": "error", "message": "Không thể tái tạo Object để React"})

@app_bot.route('/bot_reply', methods=['POST'])
def bot_reply():
    data = request.json
    mid = str(data.get("mid"))
    text = data.get("text")
    passed_object = data.get("object") 
    thread_id = data.get("thread_id") 
    
    t_type_str = str(data.get("thread_type", ""))
    t_type = ThreadType.GROUP if "GROUP" in t_type_str.upper() or "2" in t_type_str else ThreadType.USER

    obj_to_react = None
    if mid in MSG_CACHE:
        obj_to_react = MSG_CACHE[mid]["obj"]
        t_type = MSG_CACHE[mid]["thread_type"]
        thread_id = MSG_CACHE[mid]["thread_id"]
    elif passed_object:
        try:
            passed_dict = ast.literal_eval(passed_object) if isinstance(passed_object, str) else passed_object
            obj_to_react = Message(text=passed_dict.get('content', ''))
            for key, val in passed_dict.items(): setattr(obj_to_react, key, val)
            if not getattr(obj_to_react, 'msgId', None): setattr(obj_to_react, 'msgId', passed_dict.get('msgId') or passed_dict.get('cMsgId') or mid)
            if not getattr(obj_to_react, 'cliMsgId', None): setattr(obj_to_react, 'cliMsgId', passed_dict.get('cliMsgId') or passed_dict.get('cMsgId') or mid)
        except Exception: pass

    if obj_to_react and global_client:
        try:
            global_client.replyMessage(Message(text=text), obj_to_react, thread_id=thread_id, thread_type=t_type)
            print(f"{Fore.CYAN}💬 Đã Reply: {text}")
            return jsonify({"status": "success"})
        except Exception as e: return jsonify({"status": "error", "message": str(e)})
            
    return jsonify({"status": "error"})

@app_bot.route('/bot_send', methods=['POST'])
def bot_send():
    data = request.json
    thread_id = data.get("thread_id")
    text = data.get("text")
    
    t_type_str = str(data.get("thread_type", ""))
    t_type = ThreadType.GROUP if "GROUP" in t_type_str.upper() or "2" in t_type_str else ThreadType.USER

    if global_client and thread_id and text:
        try:
            global_client.send(Message(text=text), thread_id=thread_id, thread_type=t_type)
            print(f"{Fore.BLUE}📤 Đã gửi tin nhắn: {text}")
            return jsonify({"status": "success"})
        except Exception as e: return jsonify({"status": "error", "message": str(e)})
        
    return jsonify({"status": "error"})

@app_bot.route('/ping', methods=['GET'])
def ping():
    """Cổng API cho phép Web kiểm tra xem Bot có sống không"""
    return jsonify({"status": "pong"})

# ==========================================
# PHẦN 1: BỘ PHẬN GIAO LIÊN (ZALO CLIENT)
# ==========================================
class Client(ZaloAPI):
    def __init__(self, api_key, secret_key, imei, session_cookies):
        super().__init__(api_key, secret_key, imei=imei, session_cookies=session_cookies)
        self.async_client = httpx.AsyncClient()

    def onLoggedIn(self, phone=None):
        self.uid = self._state.user_id
        print(f"\n{Fore.GREEN}✅ Gateway Opened For zlapi! UID: {self.uid}")

    def send_to_backend(self, payload, message_object, thread_id, thread_type):
        try:
            res = requests.post(BACKEND_URL, json=payload, timeout=5)
            if res.status_code == 200:
                data = res.json()
                method = data.get("method")
                content = data.get("content")
                
                # --- PHÂN LUỒNG XỬ LÝ LỆNH ---
                if method in ["msg", "send", "reply", "send_target"]:
                    
                    # 1. Bọc nội dung vào Object Message (nếu có nội dung)
                    msg_obj = Message(text=str(content)) if content else Message(text="")
                    
                    # 💥 2. HACK PAYLOAD TỰ HỦY (Gắn bom hẹn giờ)
                    if "ttl" in data:
                        msg_obj.properties = {
                            "ttl": data["ttl"],
                            "isAutoDelete": "1"
                        }
                    
                    # 3. Kích hoạt gửi đi
                    if method in ["msg", "send"]:
                        self.send(msg_obj, thread_id=thread_id, thread_type=thread_type)
                        
                    elif method == "reply":
                        self.replyMessage(msg_obj, message_object, thread_id=thread_id, thread_type=thread_type)
                        
                    elif method == "send_target":
                        target_id = data.get("target_id")
                        if target_id:
                            # Bắn thẳng qua inbox riêng của ai đó (thread_type=1 là Cá nhân)
                            self.send(msg_obj, thread_id=target_id, thread_type=ThreadType.USER)
                
                elif method == "react":
                    self.sendReaction(messageObject=message_object, reactionIcon=content, thread_id=thread_id, thread_type=thread_type)
                    
                elif method == "send_base64_img":
                    b64_data = data.get("base64_data")
                    msg_obj = Message(text=content) if content else None
                    
                    # 💥 Hack tự hủy cho cả Ảnh (nếu muốn)
                    if "ttl" in data and msg_obj:
                        msg_obj.properties = {"ttl": data["ttl"], "isAutoDelete": "1"}
                    
                    if b64_data:
                        # 1. Tạo tên file tạm trên điện thoại
                        temp_path = f"temp_b64_{int(time.time())}.png"
                        try:
                            # 2. Giải mã văn bản thành ảnh và lưu tạm
                            with open(temp_path, "wb") as f:
                                f.write(base64.b64decode(b64_data))
                            
                            # 3. Gửi ảnh lên Zalo
                            self.sendLocalImage(imagePath=temp_path, message=msg_obj, thread_id=thread_id, thread_type=thread_type)
                            print(f"{Fore.BLUE}🖼️ Đã nhận và gửi ảnh Base64 từ Backend thành công!")
                            
                        except Exception as e:
                            print(f"{Fore.RED}❌ Lỗi giải mã/gửi ảnh Base64: {e}")
                        finally:
                            # 4. Gửi xong thì tự hủy ảnh rác để nhẹ máy
                            if os.path.exists(temp_path):
                                os.remove(temp_path)

        except Exception:
            pass 

    def onMessage(self, mid, author_id, message, message_object, thread_id, thread_type, **kwargs):
        try:
            message_text = message.text if isinstance(message, Message) else str(message)
            
            # --- TRÍCH XUẤT TARGET_ID TỪ QUOTE HOẶC TAG ---
            target_id = None
            if getattr(message_object, 'mentions', None) and len(message_object.mentions) > 0:
                target_id = str(message_object.mentions[0].get('uid', ''))
            elif getattr(message_object, 'quote', None):
                target_id = str(message_object.quote.ownerId)
            
            # --- CACHE THÔNG TIN (FIX LỖI -69) ---
            if author_id not in USER_CACHE:
                try:
                    info = self.fetchUserInfo(author_id).changed_profiles.get(author_id, {})
                    USER_CACHE[author_id] = info.get('zaloName', 'Không xác định')
                except: USER_CACHE[author_id] = "Lỗi tên"
            author_name = USER_CACHE[author_id]

            if thread_id not in GROUP_CACHE:
                try:
                    g_info = self.fetchGroupInfo(thread_id)
                    GROUP_CACHE[thread_id] = g_info.gridInfoMap.get(thread_id, {}).get('name', 'None')
                except: GROUP_CACHE[thread_id] = "None"
            group_name = GROUP_CACHE[thread_id]
            # ------------------------------------

            current_time = time.strftime("%H:%M:%S", time.localtime())
            
            # --- LƯU CACHE TIN NHẮN ĐỂ SAU NÀY REACT ---
            MSG_CACHE[str(mid)] = {
                "obj": message_object,
                "thread_id": thread_id,
                "thread_type": thread_type
            }
            if len(MSG_CACHE) > 200: 
                MSG_CACHE.pop(next(iter(MSG_CACHE)))
            # ------------------------------------

            if str(author_id) == str(self.uid):
                print(f"{Fore.MAGENTA}[{current_time}] {Fore.GREEN}BOT {Fore.WHITE}-> {Fore.GREEN}{message_text[:50]}")
            else:
                print(f"{Fore.MAGENTA}[{current_time}] {Fore.CYAN}{author_name} {Fore.WHITE}-> {Fore.YELLOW}{message_text[:50]}")

            is_bot = str(author_id) == str(self.uid)

            payload = {
                "event_type": "onMessage",
                "is_bot": is_bot,
                "data": {
                    "msg_text": message_text,
                    "mid": mid,
                    "author_id": str(author_id),
                    "author_name": author_name if not is_bot else "zlapi Runner",
                    "thread_id": str(thread_id),
                    "group_name": group_name,
                    "thread_type": str(thread_type),
                    "timestamp": current_time,
                    "target_id": target_id, # Đã ghim target_id vào Payload
                    "object": serialize_zalo_obj(message_object),
                    "kwargs": serialize_zalo_obj(kwargs)
                }
            }
            
            output = (
                f"------------------------------\n"
                f"Message: {message_text}\n"
                f"Author: {author_name} ({author_id})\n"
                f"Group: {group_name} ({thread_id})\n"
                f"Target ID: {target_id}\n" # In ra terminal để debug
                f"Object: {message_object}\n"
                f"------------------------------"
            )
            print(output)
            
            threading.Thread(target=self.send_to_backend, args=(payload, message_object, thread_id, thread_type)).start()

        except Exception as e:
            print(f"{Fore.RED}❌ Lỗi xử lý onMessage: {e}")

# ==========================================
# KHỞI ĐỘNG HỆ THỐNG
# ==========================================
global_client = None

if __name__ == "__main__":
    try:
        # 1. Khởi động Client thẳng từ biến config
        global_client = Client(API_KEY, SECRET_KEY, IMEI, SESSION_COOKIES)
        
        # 2. Khởi động Flask Server của Bot ở nhánh phụ
        print(f"{Fore.CYAN}📡 Đang mở cổng 3667 chờ lệnh từ Web...")
        threading.Thread(target=lambda: app_bot.run(host="0.0.0.0", port=3667, use_reloader=False), daemon=True).start()
        
        # 3. Lắng nghe tin nhắn
        global_client.listen(thread=False, delay=0)
    except Exception as e:
        print(f"{Fore.RED}❌ Lỗi khởi động: {str(e)}")