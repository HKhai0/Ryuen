def handle_example(data, parts):
    # CHỐNG CRASH: Kiểm tra xem người dùng có gõ đủ 3 chữ không
    # Nếu chỉ gõ "example msg" mà không có nội dung đằng sau -> parts[2] sẽ gây lỗi IndexError
    if len(parts) < 3:
        return {"method": "reply", "content": "Gõ thiếu lệnh rồi! Cú pháp: example [msg/reply/react] [nội dung]"}
    
    # Lấy hành động (msg, reply, react)
    action = parts[1].lower() 
    
    # GIẢI QUYẾT PARTS[2]: 
    # Nếu bro dùng parts[2], nó chỉ lấy được ĐÚNG 1 TỪ. Vd: "example msg chao ban" -> nó chỉ lấy chữ "chao"
    # Dùng " ".join(parts[2:]) sẽ gom toàn bộ các từ từ vị trí số 2 đến hết thành 1 câu dài!
    text = " ".join(parts[2:]) 
    
    # Xử lý logic và TRẢ VỀ TRỰC TIẾP luôn, không cần gán biến lằng nhằng
    if action == "msg":
        return {"method": "msg", "content": text}
        
    elif action == "reply":
        return {"method": "reply", "content": text}
        
    elif action == "react":
        # Lưu ý*: Tùy thuộc vào API của Zalo, hàm react có thể đòi hỏi icon cụ thể (như thả tim, haha)
        # Bro cẩn thận check lại xem biến content truyền vào cho react đã chuẩn icon chưa nhé.
        return {"method": "react", "content": text}
        
    else:
        return {"method": "reply", "content": "invalid action"}

def handle_example2(data, parts):
    return {"method": "reply", "content": "ccccccccc"}

# Dictionary map lệnh gọi hàm (Giữ nguyên của bro vì nó đã chuẩn)
def ryuen_get():
    return {
        "example": handle_example,
        "ex": handle_example2
    }