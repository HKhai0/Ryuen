import json
import base64
import os
import re
import os
import json

def read_imei():
    with open('dataLogin/imei.txt', 'r') as f:
        imei = f.read().strip()
    return imei

def is_base64_encoded(data):
    try:
        base64.b64decode(data).decode('utf-8')
        return True
    except Exception:
        return False

def read_and_format_cookies():
    encCookie = True
    
    with open('dataLogin/cookie.json', 'r') as f:
        data = f.read().strip()

    if is_base64_encoded(data) and not encCookie:
        decoded_data = base64.b64decode(data).decode('utf-8')
        cookies = json.loads(decoded_data)

        with open('dataLogin/cookie.json', 'w') as f:
            json.dump(cookies, f, indent=4)
        
        return cookies
    elif not is_base64_encoded(data) and encCookie:
        with open('dataLogin/cookie.json', 'r') as f:
            cookies = json.load(f)
        
        encoded_data = base64.b64encode(json.dumps(cookies).encode('utf-8')).decode('utf-8')
        
        with open('dataLogin/cookie.json', 'w') as f:
            f.write(encoded_data)
        
        return cookies
    else:
        decoded_data = base64.b64decode(data).decode('utf-8') if is_base64_encoded(data) else data
        return json.loads(decoded_data)

IMEI = read_imei()
SESSION_COOKIES = read_and_format_cookies()
API_KEY = 'api_key'
SECRET_KEY = 'secret_key'