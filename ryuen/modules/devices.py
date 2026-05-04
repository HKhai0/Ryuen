import subprocess
import os
import json
import re

def get_fastfetch_info(data, parts):
    try:
        # Chạy fastfetch với các flag quan trọng:
        # --color false: Tắt mã màu để lấy text thuần cho dễ xử lý
        # --pipe: Chế độ xuất dữ liệu tối giản để parse cho dễ
        command = "fastfetch --structure os:host:uptime:de:terminal:cpu:gpu:memory:swap:disk --logo none --color white"

        result = subprocess.run(
            command,
            shell=True,
            capture_output=True, # Bắt trọn gói log vào result
            text=True,           # Trả về dạng string
            encoding='utf-8',    # Đảm bảo ko lỗi font tiếng Việt
            timeout=10           # Đề phòng treo lệnh
        )

        if result.returncode == 0:
            full_log = result.stdout.strip()
            full_log.replace("DE:", "UI:")

            # --- KHU VỰC XỬ LÝ LOG ---
            # Ví dụ: Chỉ lấy dòng chứa GPU hoặc RAM

            # ------------------------

            # Trả về toàn bộ log để gửi Zalo
            return {"method": "reply", "content": f"{full_log}"}
        else:
            return f"❌ Lỗi chạy lệnh: {result.stderr}"

    except Exception as e:
        return f"❌ Lỗi hệ thống: {str(e)}"

def ryuen_get():
    return {"devices": get_fastfetch_info
}






