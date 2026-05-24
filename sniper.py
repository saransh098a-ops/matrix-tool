import re
import threading
import json
import time
import os
from http.server import BaseHTTPRequestHandler, HTTPServer
from pyrogram import Client, filters, idle

# ==========================================
# MASTER VARIABLES
# ==========================================
latest_code = ""
latest_channel = ""
code_queue = []
seen_codes = set()
MEMORY_FILE = "claimed_codes.txt"

# ==========================================
# 0. BOOT UP THE MEMORY BANK
# ==========================================
if os.path.exists(MEMORY_FILE):
    with open(MEMORY_FILE, "r") as f:
        for line in f:
            seen_codes.add(line.strip())
    print(f"🧠 Elephant Brain loaded {len(seen_codes)} past codes from memory.")

def save_code_to_memory(code):
    with open(MEMORY_FILE, "a") as f:
        f.write(code + "\n")

# ==========================================
# 1. HTTP SERVER — Railway compatible
# ==========================================
class CodeServer(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
            self.send_header('Access-Control-Allow-Headers', '*')
            self.end_headers()
            data = json.dumps({
                "code": latest_code,
                "channel": latest_channel
            })
            self.wfile.write(data.encode('utf-8'))
        except Exception:
            pass

    def do_OPTIONS(self):
        try:
            self.send_response(200)
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
            self.send_header('Access-Control-Allow-Headers', '*')
            self.end_headers()
        except Exception:
            pass

    def log_message(self, format, *args):
        pass  # Silence noisy logs

def run_server():
    # Railway injects PORT automatically — falls back to 5000 locally
    port = int(os.environ.get('PORT', 5000))
    server = HTTPServer(('0.0.0.0', port), CodeServer)
    print(f"🚀 Radar Server live on port {port}")
    server.serve_forever()

threading.Thread(target=run_server, daemon=True).start()

# ==========================================
# 2. QUEUE MANAGER
# ==========================================
def process_queue():
    global latest_code, latest_channel
    while True:
        if len(code_queue) > 0:
            item = code_queue.pop(0)
            latest_code    = item["code"]
            latest_channel = item["channel"]
            print(f"⚡ DEPLOYING: {latest_code} from @{latest_channel} ({len(code_queue)} left)")
            time.sleep(1.0)
        else:
            time.sleep(0.1)

threading.Thread(target=process_queue, daemon=True).start()

# ==========================================
# 3. TELEGRAM LISTENER
# ==========================================
api_id   = 23011335
api_hash = "e6afd493eef834ef069e5fe84fec10f1"

app = Client("claimer_session", api_id=api_id, api_hash=api_hash)

# Listens to ALL chats — HTML routing grid decides which game gets the code
@app.on_message(filters.text | filters.caption)
def code_catcher(client, message):
    text = message.text or message.caption
    if not text:
        return

    # Get channel/group username or fallback name
    chat = message.chat
    if chat.username:
        channel_id = chat.username.lower()
    elif chat.title:
        channel_id = chat.title.lower().replace(" ", "_")
    else:
        channel_id = "direct_message"

    raw_matches = re.findall(r'\b[A-Za-z0-9]{15,45}\b', text)

    # Filter: must have both letters AND numbers (not pure alpha/digit)
    valid_codes = [c for c in raw_matches if not c.isalpha() and not c.isdigit()]

    if valid_codes:
        new_count = 0
        for code in valid_codes:
            if code not in seen_codes:
                seen_codes.add(code)
                save_code_to_memory(code)
                code_queue.append({"code": code, "channel": channel_id})
                new_count += 1
        if new_count > 0:
            print(f"🎯 {new_count} NEW CODE(S) from @{channel_id}")

# ==========================================
# 4. BOOT SEQUENCE
# ==========================================
async def boot_sniper():
    await app.start()
    print("👁️  Telegram Sniper booting...")
    print("🔄 Syncing chats to fix Peer ID errors...")
    try:
        async for dialog in app.get_dialogs():
            pass
    except Exception:
        pass
    print("✅ Chat sync done!")
    print("🛡️  Anti-duplicate filter active.")
    print("👂 Listening for code drops across ALL chats...")
    await idle()
    await app.stop()

app.run(boot_sniper())
  
