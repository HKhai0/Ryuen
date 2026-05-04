import os
import requests
import threading
import json
from PIL import Image, ImageDraw, ImageFont
from pygments import highlight
from pygments.lexers import PythonLexer
from pygments.formatters import HtmlFormatter
from bs4 import BeautifulSoup

CONFIG_FILE = "rsmode_config.json"

def is_admin(uid):
    """Lấy danh sách Admin từ Trạm kiểm duyệt chung"""
    if not os.path.exists(CONFIG_FILE): 
        return False
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return str(uid) in json.load(f).get("admins", [])
    except: 
        return False

def read_command_content(command_name):
    try:
        file_path = f"modules/{command_name}.py"
        if not os.path.exists(file_path):
            return None
        with open(file_path, 'r', encoding='utf-8') as file:
            return file.read()
    except Exception as e:
        return str(e)



def create_image_from_code(code, command_name, font_path="modules/cache/SFMono-Bold.otf"):
    fontcre = "modules/cache/UTM-AvoBold.ttf"
    fontlenh = "modules/cache/UTM-AvoItalic.ttf"

    highlighted_soup = highlight_code(code)
    code_lines = code.splitlines()

    line_height = 30
    line_offset = 80

    temp_img = Image.new('RGBA', (1, 1))
    temp_draw = ImageDraw.Draw(temp_img)
    temp_font = ImageFont.truetype(font_path, 30)

    max_width = max(temp_draw.textlength(line, font=temp_font) for line in code_lines) + 170
    img_width = max(3000, max_width)

    img_width = int(img_width)
    img_height = int(line_offset + len(code_lines) * line_height + 60)

    background_color = (30, 30, 30)
    header_color = (50, 50, 50)

    background = Image.new('RGBA', (img_width, img_height), background_color)
    draw = ImageDraw.Draw(background)

    header_height = 50
    draw.rectangle([(0, 0), (img_width, header_height)], fill=header_color)

    header_font = ImageFont.truetype(font_path, 38)
    ryuen_text = "Python Is Trash"

    ryuen_text_width = temp_draw.textlength(ryuen_text, font=header_font)
    ryuen_text_x = (img_width - ryuen_text_width) // 2 + 10

    ryuen_text_bbox = draw.textbbox((0, 0), ryuen_text, font=header_font)
    ryuen_text_height = ryuen_text_bbox[3] - ryuen_text_bbox[0]

    ryuen_text_y = (header_height - ryuen_text_height) // 2

    draw.text((ryuen_text_x, ryuen_text_y), ryuen_text, font=header_font, fill=(100, 100, 100))

    dot_radius_outer = 12
    dot_radius_inner = 8
    dot_spacing = 20
    dots_x_start = 30

    dot_positions = [
        (dots_x_start, 25),
        (dots_x_start + 2 * dot_radius_outer + dot_spacing, 25),
        (dots_x_start + 4 * dot_radius_outer + 2 * dot_spacing, 25)
    ]
    dot_colors = [(255, 59, 48), (40, 205, 65), (255, 190, 0)]
    inner_dot_color = header_color

    for pos, border_color in zip(dot_positions, dot_colors):
        draw.ellipse([pos[0] - dot_radius_outer, pos[1] - dot_radius_outer,
                      pos[0] + dot_radius_outer, pos[1] + dot_radius_outer], fill=border_color)
        draw.ellipse([pos[0] - dot_radius_inner, pos[1] - dot_radius_inner,
                      pos[0] + dot_radius_inner, pos[1] + dot_radius_inner], fill=inner_dot_color)

    draw.text((ryuen_text_x, 10), ryuen_text, font=header_font, fill=(100, 100, 100))

    command_font = ImageFont.truetype(fontlenh, 25)
    command_text = f"{command_name}.py"

    command_text_width = temp_draw.textlength(command_text, font=command_font)
    python_logo_width = 24
    tab_padding = 20
    tab_width = int(command_text_width + python_logo_width + tab_padding * 3)
    tab_height = 50
    tab_color = background_color
    corner_radius = 15

    tab_x = dots_x_start + 4 * dot_radius_outer + 2 * dot_spacing + 40
    tab_y = (header_height - tab_height) // 2 + 10

    draw.rounded_rectangle([(tab_x, tab_y), (tab_x + tab_width, tab_y + tab_height)], radius=corner_radius, fill=tab_color)

    python_logo_path = "modules/cache/python-logo.png"
    if os.path.exists(python_logo_path):
        python_logo = Image.open(python_logo_path)
        python_logo = python_logo.resize((25, 25))
        background.paste(python_logo, (tab_x + tab_padding, tab_y + 8), python_logo)

    draw.text((tab_x + python_logo_width + tab_padding * 2, tab_y + 0), command_text, font=command_font, fill=(255, 255, 255))

    y_offset = line_offset + header_height

    code_font = ImageFont.truetype(font_path, 25)
    line_font = ImageFont.truetype(font_path, 25)

    for i, line in enumerate(code_lines):
        line_number = f"{i + 1:2}"
        draw.text((10, y_offset), line_number, font=line_font, fill=(220, 220, 220))

        highlighted_line = highlight(line, PythonLexer(), HtmlFormatter())
        soup_line = BeautifulSoup(highlighted_line, 'html.parser')

        leading_spaces = len(line) - len(line.lstrip(' '))
        x_offset = 60 + leading_spaces * draw.textlength(' ', font=code_font)

        spans = soup_line.find_all('span')
        last_end_index = 0

        for span in spans:
            token_text = span.get_text()
            token_color = get_color_for_token_type(span)

            start_index = line.find(token_text, last_end_index)
            if start_index > last_end_index:
                space_text = line[last_end_index:start_index]
                draw.text((x_offset, y_offset), space_text, font=code_font, fill=(220, 220, 220))
                x_offset += draw.textlength(space_text, font=code_font)

            draw.text((x_offset, y_offset), token_text, font=code_font, fill=token_color)
            x_offset += draw.textlength(token_text, font=code_font)
            last_end_index = start_index + len(token_text)

        if last_end_index < len(line):
            remaining_space = line[last_end_index:]
            draw.text((x_offset, y_offset), remaining_space, font=code_font, fill=(220, 220, 220))

        y_offset += line_height

    # Đảm bảo thư mục cache tồn tại
    os.makedirs("modules/cache", exist_ok=True)
    image_path = "modules/cache/anh.png"
    background.save(image_path)
    return image_path, img_width, img_height

def highlight_code(code):
    formatter = HtmlFormatter()
    highlighted_code = highlight(code, PythonLexer(), formatter)
    soup = BeautifulSoup(highlighted_code, "html.parser")
    return soup

def get_color_for_token_type(span):
    color_map = {
        'k': (0, 255, 255), 'n': (255, 232, 255), 's': (255, 255, 107),
        'c': (173, 216, 230), 'o': (225, 225, 225), 'p': (0, 255, 0),
        'm': (233, 51, 35),
    }
    if 'class' in span.attrs:
        token_type = span['class'][0][0]
        return color_map.get(token_type, (220, 220, 220))
    return (220, 220, 220)

import threading
import requests

def task_render_and_post(command_content, command_name, thread_id, thread_type):
    """Luồng chạy ngầm: Vẽ ảnh và tự động gọi main.py để gửi"""
    try:
        # 1. Thực hiện vẽ ảnh vào mục cache (Hàm create_image_from_code của bro)
        image_path, img_width, img_height = create_image_from_code(command_content, command_name)

        if os.path.exists(image_path):
            payload = {
                "thread_id": thread_id,
                "thread_type": thread_type,
                "image_path": image_path,
                "text": f"💻 Source Code: {command_name}.py"
            }
            # 2. Gửi POST sang cổng 3667 của main.py
            requests.post("http://127.0.0.1:3667/bot_send_local_img", json=payload, timeout=300)
            
    except Exception as e:
        # Nếu lỗi thì báo về Zalo qua lệnh gửi text thông thường
        requests.post("http://127.0.0.1:3667/bot_send", json={
            "thread_id": thread_id,
            "thread_type": thread_type,
            "text": f"❌ Lỗi vẽ ảnh module {command_name}: {str(e)}"
        })

def handle_viewcode_command(data, parts):
    """Hàm xử lý lệnh chính (Trả lời ngay để tránh timeout)"""
    author_id = str(data.get("author_id"))
    thread_id = str(data.get("thread_id"))
    thread_type = str(data.get("thread_type"))

    # Check quyền Admin từ Trạm kiểm soát chung (rsmode_config.json)
    if not is_admin(author_id):
        return {"method": "react", "content": "⛔"}

    if len(parts) < 2:
        return {"method": "reply", "content": "❌ Gõ: viewcode [tên_module]"}

    command_name = parts[1].strip()
    command_content = read_command_content(command_name)
    
    if command_content is None:
        return {"method": "reply", "content": f"❌ Không thấy file: {command_name}.py"}

    # --- KÍCH HOẠT CHẠY NGẦM ---
    threading.Thread(
        target=task_render_and_post, 
        args=(command_content, command_name, thread_id, thread_type), 
        daemon=True
    ).start()

    # Trả lời Zalo ngay lập tức để không bị 'đứng' bot
    return {
        "method": "reply", 
        "content": f"Đang vẽ ảnh '{command_name}' , độ phân giải mặc định 3000 pixels"
    }

def ryuen_get():
    return {
        'viewcode': handle_viewcode_command
}
