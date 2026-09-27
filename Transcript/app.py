"""Local-only Whisper transcription UI. Run with the project's existing venv."""
from __future__ import annotations

import argparse
import json
import os
import queue
import secrets
import socket
import tempfile
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parent
MODEL_DIR = ROOT.parent / ".models" / "faster-whisper-large-v3-turbo"
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"
MAX_BYTES = 100 * 1024 * 1024
jobs: dict[str, dict] = {}
lock = threading.Lock()
pending: queue.Queue = queue.Queue(maxsize=24)
state = {"status": "loading", "error": "", "model": "Whisper large-v3-turbo"}


def worker():
    try:
        from faster_whisper import WhisperModel
        if not (MODEL_DIR / "model.bin").is_file():
            raise FileNotFoundError(f"مدل موجود پیدا نشد: {MODEL_DIR}")
        model = WhisperModel(str(MODEL_DIR), device="cpu", compute_type="int8",
                             cpu_threads=min(4, os.cpu_count() or 2), num_workers=1,
                             local_files_only=True)
        with lock:
            state["status"] = "ready"
        print("Whisper ready (local CPU / int8).", flush=True)
    except Exception as exc:
        with lock:
            state.update(status="error", error=str(exc))
        return
    while True:
        job_id, path, language = pending.get()
        try:
            with lock:
                jobs[job_id]["status"] = "processing"
            segments, info = model.transcribe(
                str(path), language=None if language == "auto" else language,
                beam_size=3, temperature=0, condition_on_previous_text=False,
                vad_filter=True,
                vad_parameters={"min_silence_duration_ms": 450, "speech_pad_ms": 250},
            )
            for segment in segments:
                with lock:
                    job = jobs[job_id]
                    job["segments"].append({"start": segment.start, "end": segment.end,
                                             "text": segment.text.strip()})
                    job["text"] = " ".join(s["text"] for s in job["segments"])
            with lock:
                jobs[job_id].update(status="done", language=info.language, duration=info.duration)
        except Exception as exc:
            with lock:
                jobs[job_id].update(status="error", error=str(exc))
        finally:
            path.unlink(missing_ok=True)
            pending.task_done()


class LocalServer(ThreadingHTTPServer):
    allow_reuse_address = False

    def server_bind(self):
        if os.name == "nt":
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        super().server_bind()


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        # Keep the local console quiet; no transcript content is logged.
        pass

    def reply(self, code, data, content_type="application/json; charset=utf-8"):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8") if isinstance(data, dict) else data
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Permissions-Policy", "microphone=(self)")
        self.end_headers()
        try:
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def local_request(self):
        allowed = {f"127.0.0.1:{self.server.server_port}", f"localhost:{self.server.server_port}"}
        if self.headers.get("Host", "") not in allowed:
            self.reply(403, {"error": "فقط دسترسی محلی مجاز است."})
            return False
        origin = self.headers.get("Origin")
        if origin and origin not in {f"http://{host}" for host in allowed}:
            self.reply(403, {"error": "مبدأ درخواست مجاز نیست."})
            return False
        return True

    def do_GET(self):
        if not self.local_request():
            return
        route = urlparse(self.path).path
        if route == "/api/status":
            with lock:
                snapshot = dict(state, queued=pending.qsize())
            self.reply(200, snapshot)
        elif route.startswith("/api/jobs/"):
            with lock:
                job = jobs.get(route.rsplit("/", 1)[-1])
                snapshot = json.loads(json.dumps(job)) if job else None
            self.reply(200 if snapshot else 404, snapshot or {"error": "درخواست پیدا نشد."})
        elif route in {"/", "/index.html", "/style.css", "/app.js"}:
            name = "index.html" if route == "/" else route[1:]
            kind = {"html": "text/html", "css": "text/css", "js": "text/javascript"}[name.rsplit(".", 1)[-1]]
            self.reply(200, (ROOT / "static" / name).read_bytes(), kind + "; charset=utf-8")
        else:
            self.reply(404, {"error": "صفحه پیدا نشد."})

    def do_POST(self):
        if not self.local_request():
            return
        if self.path != "/api/transcribe":
            return self.reply(404, {"error": "مسیر پیدا نشد."})
        with lock:
            status, error = state["status"], state["error"]
        if status != "ready":
            return self.reply(503, {"error": error or "مدل در حال آماده‌سازی است."})
        try:
            size = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            return self.reply(400, {"error": "اندازهٔ فایل نامعتبر است."})
        if not 0 < size <= MAX_BYTES:
            return self.reply(413, {"error": "فایل باید بین ۱ بایت و ۱۰۰ مگابایت باشد."})
        language = self.headers.get("X-Language", "fa")
        if language not in {"fa", "en", "auto"}:
            return self.reply(400, {"error": "زبان نامعتبر است."})
        path = None
        try:
            self.connection.settimeout(60)
            body = self.rfile.read(size)
            if len(body) != size:
                return self.reply(400, {"error": "دریافت فایل کامل نشد."})
            with tempfile.NamedTemporaryFile(prefix="local_whisper_", suffix=".audio", delete=False) as file:
                path = Path(file.name)
                file.write(body)
            job_id = secrets.token_urlsafe(18)
            with lock:
                cutoff = time.time() - 3600
                for old_id in list(jobs):
                    if jobs[old_id]["created"] < cutoff and jobs[old_id]["status"] in {"done", "error"}:
                        del jobs[old_id]
                jobs[job_id] = {"status": "queued", "text": "", "segments": [], "error": "", "created": time.time()}
            try:
                pending.put_nowait((job_id, path, language))
            except queue.Full:
                with lock:
                    del jobs[job_id]
                path.unlink(missing_ok=True)
                return self.reply(429, {"error": "صف پردازش پر است؛ کمی صبر کنید."})
            self.reply(202, {"id": job_id})
        except Exception as exc:
            if path:
                path.unlink(missing_ok=True)
            self.reply(400, {"error": str(exc)})


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()
    url = f"http://127.0.0.1:{args.port}"
    try:
        with urlopen(url + "/api/status", timeout=2) as response:
            existing = json.load(response)
        if existing.get("model") == state["model"] and "queued" in existing:
            print(f"Transcript is already running: {url}", flush=True)
            if not args.no_browser:
                webbrowser.open(url)
            return
    except Exception:
        pass
    try:
        server = LocalServer(("127.0.0.1", args.port), Handler)
    except OSError:
        try:
            with urlopen(url + "/api/status", timeout=2) as response:
                existing = json.load(response)
            if existing.get("model") == state["model"] and "queued" in existing:
                print(f"Transcript is already running: {url}", flush=True)
                if not args.no_browser:
                    webbrowser.open(url)
                return
        except Exception:
            pass
        print(f"Port {args.port} is in use. Try --port 8766.", flush=True)
        raise SystemExit(1)
    threading.Thread(target=worker, daemon=True).start()
    print(f"Local transcription: {url}\nClose this console or press Ctrl+C to stop.", flush=True)
    if not args.no_browser:
        threading.Timer(0.7, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        while True:
            try:
                _, path, _ = pending.get_nowait()
                path.unlink(missing_ok=True)
            except queue.Empty:
                break


if __name__ == "__main__":
    main()
