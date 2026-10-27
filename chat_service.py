#!/usr/bin/env python3
"""
Wedding AI Chat & In-House TTS Microservice for wedding.tahi.vn
Powered by gemini-3.8-flash via CLIProxy & CapCut Vietnamese TTS API (Ban Mai / Mai)
"""

import hashlib
import json
import logging
import os
import re
import sys
import urllib.request
import urllib.parse
import urllib.error
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("wedding_chat_ai")

PORT = 8082
DEEPGRAM_KEY = "cb375ac97ec487fb10a64240c42cf68fec8967ac"
CARTESIA_API_KEY = os.environ.get("CARTESIA_API_KEY", "") or "sk_car_4G8hzLuum2EH2bUGSBCjQ5"
CARTESIA_VOICE_LINH = "935a9060-373c-49e4-b078-f4ea6326987a"
CLIPROXY_URL = "http://127.0.0.1:8317/v1/chat/completions"
CLIPROXY_KEY = "cpa_P6dmy7mliAIPboi7r2ber2QIYWbTQKajBmhrnuUGvWg"
GUEST_API_URL = "http://127.0.0.1:8081/api/invite/guest/"
VOICE_CACHE_DIR = "/var/www/wedding/voices"

# CapCut In-House TTS Package integration
CAPCUT_DIR = "/opt/weddingcheck/capcut_tts"
if os.path.exists(CAPCUT_DIR) and CAPCUT_DIR not in sys.path:
    sys.path.insert(0, CAPCUT_DIR)

try:
    from capcut_tts_api import CapCutClient
    tts_client = CapCutClient()
    logger.info("In-house CapCutClient initialized successfully.")
except Exception as e:
    tts_client = None
    logger.error(f"In-house CapCut TTS client not available: {e}")

# Supported in-house voices
# ban_mai: multi_female_yangguangnv_uranus_bigtts (Ban Mai - Podcast, dịu dàng, ấm áp nhất cho thiệp cưới)
# mai: BV562_streaming (Mai - tự nhiên, trong trẻo)
DEFAULT_VOICE = "multi_female_yangguangnv_uranus_bigtts"

SYSTEM_PROMPT = """Bạn là sự hiện diện số ấm áp, chân thành và dịu dàng của cặp đôi Lê Duy Tân & Đinh Khánh Chi trên website thiệp cưới chính thức (wedding.tahi.vn).
Nhiệm vụ của bạn là thay mặt cô dâu và chú rể trò chuyện, đón tiếp, giải đáp thắc mắc và tiếp nhận lời chúc của khách quý một cách ngọt ngào, tinh tế, khiêm nhường và đong đầy tình cảm.

### 1. NGUYÊN TẮC CỐT LÕI (TONE & VOICE):
- Văn phong: Nhẹ nhàng, ấm áp, từ tốn, chân phương, mộc mạc và chân thành. Tuyệt đối không văn mẫu sáo rỗng, không dùng từ ngữ hành chính/công nghệ/robot (CẤM các từ: "hệ thống", "trạng thái", "thao tác", "đơn vị", "ghi nhận thành công", "AI trợ lý").
- Ngắn gọn, súc tích (1–3 đoạn ngắn, khoảng 35–80 từ), định dạng đẹp, dễ đọc trên điện thoại.
- Luôn sẵn lòng giải đáp: Ở cuối mỗi câu trả lời hoặc khi phù hợp, hãy nhắn gửi nhẹ nhàng, chu đáo: "Bác / bạn có bất cứ điều gì cần hỏi hay dặn dò thêm, cứ nhắn tin ở đây cho hai cháu / tụi mình nhé, cháu / tụi mình sẽ giải đáp toàn bộ và thật chu đáo ạ! 🌸"
- Biểu tượng cảm xúc (Emoji): Sử dụng chừng mực, tươi vui, tinh tế (🌸, ✨, 💐, 💌, 💍, 💕). TUYỆT ĐỐI CẤM dùng emoji chắp tay lạy (🙏).

### 2. QUY TẮC XƯNG HÔ (ADAPTIVE RESPECT):
- Với BẬC TRƯỞNG BỐI (Bác, Chú, Cô, Dì, Ông, Bà, Cậu, Thím... hoặc khi biết khách là người lớn tuổi):
  - Luôn mở đầu kính cẩn, tươi vui: "Dạ, chúng con kính chào [Vai vế] ạ! 🌸"
  - Xưng: "chúng con" / "hai cháu". Gọi: "Bác" / "Chú" / "Cô" / "Dì" / "Gia đình mình".
  - Kết thúc câu luôn có chữ "ạ". Giữ trọn đạo lý kính trên nhường dưới của người Việt. Cấm dùng emoji chắp tay lạy (🙏).
- Với BẠN BÈ / ĐỒNG TRANG LỨA:
  - Xưng: "Tân & Chi" / "tụi mình" / "hai đứa". Gọi: "bạn" / "anh" / "chị" ngọt ngào, thân mật.

### 3. DỮ LIỆU THỰC TẾ CỦA ĐÁM CƯỚI (SSOT - TUYỆT ĐỐI CHÍNH XÁC):
- Chú rể: Lê Duy Tân (Kỹ sư công nghệ, quê Gia Lai).
- Cô dâu: Đinh Khánh Chi (Dịu dàng, phúc hậu, quê Hà Nội).
- Dấu mốc Dạm Ngõ: Ngày 16.09.2026 (06.08 năm Bính Ngọ).
- Thời gian Hôn Lễ:
  • Ngày 1: 17:00 Thứ Bảy, ngày 16/01/2027 (09 Tháng Chạp năm Bính Ngọ) — Tiệc Nhóm Họ, bữa cơm thân mật cùng họ hàng, bà con lối xóm và bạn bè thân thiết dựng rạp ấm cúng.
  • Ngày 2: 10:30 Chủ Nhật, ngày 17/01/2027 (10 Tháng Chạp năm Bính Ngọ) — Nghi Thức Lễ Vu Quy & Khai Tiệc Mừng Hạnh Phúc.
- Địa điểm: Tổ chức trọn vẹn tại Tư Gia Nhà Gái. Có bãi đỗ xe ô tô, xe máy rộng rãi ngay cạnh rạp cưới, có người trong gia đình đón tiếp và hướng dẫn chu đáo.
- Trang phục (Dress code): Không quy định khắt khe. Khách chỉ cần mặc lịch sự, thoải mái, tự tin. Khuyến khích các tone màu ấm (be, pastel, trắng, xanh nhã, đỏ nhung).
- Thực đơn: Cỗ tiệc truyền thống ấm cúng; có chuẩn bị món chay thanh tịnh nếu khách báo trước.
- Mừng cưới: Không bao giờ chủ động gợi ý hay đề cập tiền bạc. Nếu khách hỏi, nói khiêm nhường: "Với tụi mình, nụ cười và sự hiện diện của bạn là món quà cưới quý giá nhất rồi. Nếu ở xa không thể về chung vui trực tiếp, chút tình cảm gửi gắm từ bạn hai đứa xin trân trọng nâng niu cho tổ ấm nhỏ..." (kèm STK: Chú rể Duy Tân - MBBank 0000112233440, Cô dâu Khánh Chi - LPBank 15093012892256).
- Lời chúc: Đón nhận bằng sự xúc động và biết ơn chân thành, báo rằng lời chúc đã được lưu vào Sổ Lưu Bút Kỷ Niệm."""

def fetch_guest_info(slug):
    if not slug:
        return ""
    try:
        url = GUEST_API_URL + urllib.parse.quote(slug)
        req = urllib.request.Request(url, headers={"User-Agent": "WeddingAIChat/1.0"})
        with urllib.request.urlopen(req, timeout=3) as resp:
            if resp.status == 200:
                data = json.loads(resp.read().decode())
                name = data.get("name", "")
                relation = data.get("relation", "")
                side = data.get("side", "")
                side_str = "Nhà Gái" if side == "bride" else "Nhà Trai"
                info = f"Tên khách mời: {name}. Mối quan hệ: {relation} (Khách Quý {side_str})."
                if data.get("personal_message"):
                    info += f" Lời nhắn riêng gửi khách: '{data.get('personal_message')}'."
                return info
    except Exception as e:
        logger.warning(f"Failed to fetch guest info for slug {slug}: {e}")
    return ""

def clean_for_tts(text: str) -> str:
    # Remove markdown bold/italics/quotes/bullets
    t = re.sub(r'[*#_>~`•]', ' ', text)
    # Remove emojis
    t = re.sub(r'[\U00010000-\U0010ffff]', '', t)
    # Normalize whitespaces
    t = re.sub(r'\s+', ' ', t).strip()
    return t[:260]

def generate_voice_url(text: str, voice: str = DEFAULT_VOICE) -> str:
    if not tts_client:
        return ""

    clean = clean_for_tts(text)
    if not clean:
        return ""

    # Ensure cache directory exists
    try:
        os.makedirs(VOICE_CACHE_DIR, exist_ok=True)
    except Exception:
        pass

    text_hash = hashlib.md5(f"{clean}_{voice}".encode("utf-8")).hexdigest()
    cache_filename = f"voice_{text_hash}.mp3"
    cache_path = os.path.join(VOICE_CACHE_DIR, cache_filename)
    public_url = f"/voices/{cache_filename}"

    # Return cached audio if already downloaded
    if os.path.exists(cache_path) and os.path.getsize(cache_path) > 1000:
        return public_url

    # 1. Cartesia Sonic Engine (Voice Linh - 90ms TTFB)
    if CARTESIA_API_KEY:
        try:
            cart_payload = json.dumps({
                "model_id": "sonic-3.6",
                "transcript": clean,
                "voice": {
                    "mode": "id",
                    "id": CARTESIA_VOICE_LINH
                },
                "output_format": {
                    "container": "mp3",
                    "sample_rate": 44100
                },
                "language": "vi"
            }).encode("utf-8")
            cart_req = urllib.request.Request(
                "https://api.cartesia.ai/tts/bytes",
                data=cart_payload,
                headers={
                    "X-API-Key": CARTESIA_API_KEY,
                    "Cartesia-Version": "2024-06-10",
                    "Content-Type": "application/json"
                },
                method="POST"
            )
            with urllib.request.urlopen(cart_req, timeout=8.0) as resp:
                audio_bytes = resp.read()
            if audio_bytes and len(audio_bytes) > 1000:
                with open(cache_path, "wb") as f:
                    f.write(audio_bytes)
                logger.info(f"Generated Cartesia Sonic Linh voiceover: {cache_path} ({len(audio_bytes)} bytes)")
                return public_url
        except Exception as e:
            logger.warning(f"Cartesia Sonic Linh error: {e}")

    # 2. In-House CapCut TTS generator (Ban Mai / Mai) fallback
    if tts_client:
        for target_voice in [voice, "BV562_streaming"]:
            try:
                res = tts_client.generate_speech(texts=clean, voice=target_voice, wait=True, timeout=9.0)
                tasks = (res.get("data") or {}).get("tasks") or []
                if tasks:
                    payload = json.loads(tasks[0].get("payload"))
                    subs = payload.get("audio_subtitles") or []
                    if subs and subs[0].get("speech_url"):
                        remote_url = subs[0]["speech_url"]
                        req = urllib.request.Request(remote_url, headers={"User-Agent": "Mozilla/5.0"})
                        with urllib.request.urlopen(req, timeout=9) as resp:
                            audio_bytes = resp.read()
                        if audio_bytes and len(audio_bytes) > 1000:
                            with open(cache_path, "wb") as f:
                                f.write(audio_bytes)
                            logger.info(f"Generated in-house voiceover ({target_voice}): {cache_path} ({len(audio_bytes)} bytes)")
                            return public_url
            except Exception as e:
                logger.warning(f"In-house CapCut TTS error with voice {target_voice}: {e}")

    return ""

def call_llm(user_msg, guest_info="", history=None):
    sys_content = SYSTEM_PROMPT
    if guest_info:
        sys_content += f"\n\n### THÔNG TIN KHÁCH MỜI ĐANG TRÒ CHUYỆN:\n{guest_info}"

    messages = [{"role": "system", "content": sys_content}]

    # Append recent conversation history (up to 6 turns)
    if history and isinstance(history, list):
        for h in history[-6:]:
            role = h.get("role")
            content = h.get("content")
            if role in ["user", "assistant"] and content:
                messages.append({"role": role, "content": content})

    messages.append({"role": "user", "content": user_msg})

    payload = {
        "model": "gemini-3.8-flash",
        "messages": messages,
        "max_tokens": 250,
        "temperature": 0.7,
    }

    req = urllib.request.Request(
        CLIPROXY_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {CLIPROXY_KEY}"
        }
    )

    try:
        with urllib.request.urlopen(req, timeout=12) as resp:
            res = json.loads(resp.read().decode())
            choices = res.get("choices", [])
            if choices and "message" in choices[0]:
                return choices[0]["message"].get("content", "").strip()
    except Exception as e:
        logger.error(f"CLIProxy request failed: {e}")

    # Graceful fallback if AI proxy is down
    return "Tân & Chi cảm ơn lời nhắn của bạn nhiều nha! Tụi mình luôn ở đây để sẻ chia mọi thông tin về ngày vui cùng bạn. 🌸"

class ChatHandler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS, GET")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        if self.path == "/health":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"status": "ok", "service": "wedding-chat-ai", "in_house_tts": true}')
            return
        self.send_response(404)
        self.end_headers()

    def do_POST(self):
        if self.path in ["/api/chat", "/api/chat/", "/chat"]:
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)

            try:
                data = json.loads(body.decode("utf-8"))
            except Exception:
                data = {}

            user_msg = data.get("message", "").strip()
            slug = data.get("slug", "").strip()
            history = data.get("history", [])

            if not user_msg:
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(b'{"error": "Empty message"}')
                return

            guest_info = fetch_guest_info(slug)
            reply = call_llm(user_msg, guest_info=guest_info, history=history)

            # Generate In-House TTS Voiceover URL (Ban Mai voice)
            audio_url = generate_voice_url(reply)

            res_body = json.dumps({"reply": reply, "audio_url": audio_url}, ensure_ascii=False).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(res_body)

        elif self.path in ["/api/tts", "/api/tts/", "/tts"]:
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)
            try:
                data = json.loads(body.decode("utf-8"))
            except Exception:
                data = {}
            text = data.get("text", "").strip()
            voice = data.get("voice", DEFAULT_VOICE)
            audio_url = generate_voice_url(text, voice=voice)

            res_body = json.dumps({"audio_url": audio_url}, ensure_ascii=False).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(res_body)

        elif self.path in ["/api/stt", "/api/stt/", "/stt"]:
            content_length = int(self.headers.get("Content-Length", 0))
            audio_data = self.rfile.read(content_length)
            content_type = self.headers.get("Content-Type", "audio/webm")

            transcript = ""
            try:
                url = "https://api.deepgram.com/v1/listen?model=nova-3&language=vi&smart_format=true"
                req = urllib.request.Request(
                    url,
                    data=audio_data,
                    headers={
                        "Authorization": f"Token {DEEPGRAM_KEY}",
                        "Content-Type": content_type
                    },
                    method="POST"
                )
                with urllib.request.urlopen(req, timeout=10) as resp:
                    dg_res = json.loads(resp.read().decode("utf-8"))
                    channels = (dg_res.get("results") or {}).get("channels") or []
                    if channels and channels[0].get("alternatives"):
                        transcript = channels[0]["alternatives"][0].get("transcript", "").strip()
            except Exception as e:
                logger.error(f"Deepgram STT API error: {e}")

            res_body = json.dumps({"transcript": transcript}, ensure_ascii=False).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(res_body)

        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        logger.info("%s - - [%s] %s" % (self.client_address[0], self.log_date_time_string(), format % args))

def run():
    server = ThreadingHTTPServer(("127.0.0.1", PORT), ChatHandler)
    logger.info(f"Wedding AI Chat Server (In-House TTS) running on http://127.0.0.1:{PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.server_close()

if __name__ == "__main__":
    run()
