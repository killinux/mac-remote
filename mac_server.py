"""
Runs on this box (known public IP).
Claude POSTs commands here; the Mac agent polls for them and posts results back.

Start:
    TOKEN=your-long-random-token python3 mac_server.py 0.0.0.0 8090
"""
import json, os, sys, uuid, time, threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

TOKEN = os.environ.get("TOKEN", "change-me")

_tasks = {}
_pending = []
_lock = threading.Lock()
TASK_TTL = 3600


def _gc():
    now = time.time()
    dead = [i for i, t in _tasks.items()
            if t["status"] == "done" and now - t["ts"] > TASK_TTL]
    for i in dead:
        _tasks.pop(i, None)


class H(BaseHTTPRequestHandler):
    def log_message(self, fmt, *a):
        sys.stderr.write("[%s] %s\n" % (self.address_string(), fmt % a))

    def _auth(self):
        if self.headers.get("X-Token") != TOKEN:
            self._json(401, {"error": "unauthorized"})
            return False
        return True

    def _json(self, code, obj):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self):
        n = int(self.headers.get("Content-Length") or 0)
        if not n:
            return {}
        return json.loads(self.rfile.read(n) or b"{}")

    def do_POST(self):
        if not self._auth():
            return
        if self.path == "/tasks":
            body = self._read_json()
            cmd = body.get("cmd")
            if not cmd:
                return self._json(400, {"error": "cmd required"})
            tid = uuid.uuid4().hex
            with _lock:
                _tasks[tid] = {"cmd": cmd, "status": "pending",
                               "result": None, "ts": time.time()}
                _pending.append(tid)
                _gc()
            return self._json(200, {"id": tid})

        if self.path.startswith("/tasks/") and self.path.endswith("/result"):
            tid = self.path.split("/")[2]
            body = self._read_json()
            with _lock:
                t = _tasks.get(tid)
                if not t:
                    return self._json(404, {"error": "no such task"})
                t["status"] = "done"
                t["result"] = {
                    "stdout": body.get("stdout", ""),
                    "stderr": body.get("stderr", ""),
                    "rc": body.get("rc", -1),
                }
                t["ts"] = time.time()
            return self._json(200, {"ok": True})

        self._json(404, {"error": "not found"})

    def do_GET(self):
        if not self._auth():
            return
        if self.path.startswith("/tasks/next"):
            deadline = time.time() + 25
            while time.time() < deadline:
                with _lock:
                    if _pending:
                        tid = _pending.pop(0)
                        t = _tasks[tid]
                        return self._json(200, {"id": tid, "cmd": t["cmd"]})
                time.sleep(1)
            return self._json(204, {})

        if self.path.startswith("/tasks/"):
            tid = self.path.split("/")[2]
            with _lock:
                t = _tasks.get(tid)
                if not t:
                    return self._json(404, {"error": "no such task"})
                return self._json(200, {
                    "status": t["status"], "result": t["result"]
                })

        self._json(404, {"error": "not found"})


if __name__ == "__main__":
    host = sys.argv[1] if len(sys.argv) > 1 else "0.0.0.0"
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 8090
    if TOKEN == "change-me":
        sys.stderr.write("WARNING: TOKEN env var not set, using default\n")
    print(f"listening on {host}:{port}")
    ThreadingHTTPServer((host, port), H).serve_forever()
