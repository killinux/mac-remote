"""
Runs on your Mac.
Polls the remote server for commands, executes them locally, posts results back.

Start:
    SERVER_URL=http://<server-public-ip>:8090 \
    TOKEN=your-long-random-token \
    python3 mac_agent.py
"""
import json, os, subprocess, sys, time, urllib.request, urllib.error

SERVER_URL = os.environ["SERVER_URL"].rstrip("/")
TOKEN = os.environ["TOKEN"]
POLL_BACKOFF = 2
CMD_TIMEOUT = 300


def _req(method, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        SERVER_URL + path, data=data, method=method,
        headers={"X-Token": TOKEN, "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        if r.status == 204:
            return None
        return json.loads(r.read() or b"{}")


def upload_file(filepath):
    filepath = os.path.expanduser(filepath)
    if not os.path.isfile(filepath):
        return {"stdout": "", "stderr": f"file not found: {filepath}", "rc": 1}
    fname = os.path.basename(filepath)
    try:
        with open(filepath, "rb") as f:
            data = f.read()
        req = urllib.request.Request(
            SERVER_URL + "/files/upload", data=data, method="POST",
            headers={
                "X-Token": TOKEN,
                "Content-Type": "application/octet-stream",
                "X-Filename": fname,
            },
        )
        with urllib.request.urlopen(req, timeout=120) as r:
            resp = json.loads(r.read() or b"{}")
        return {"stdout": f"uploaded {fname} ({len(data)} bytes) -> {resp.get('path','')}", "stderr": "", "rc": 0}
    except Exception as e:
        return {"stdout": "", "stderr": f"upload error: {e}", "rc": 1}


def run(cmd):
    if cmd.startswith("__upload__:"):
        return upload_file(cmd[len("__upload__:"):])
    try:
        p = subprocess.run(
            cmd, shell=True, capture_output=True, text=True,
            timeout=CMD_TIMEOUT,
        )
        return {"stdout": p.stdout, "stderr": p.stderr, "rc": p.returncode}
    except subprocess.TimeoutExpired as e:
        return {"stdout": e.stdout or "", "stderr": (e.stderr or "") +
                f"\n[timeout after {CMD_TIMEOUT}s]", "rc": 124}
    except Exception as e:
        return {"stdout": "", "stderr": f"agent error: {e}", "rc": 1}


def main():
    print(f"mac agent polling {SERVER_URL}")
    while True:
        try:
            task = _req("GET", "/tasks/next")
        except urllib.error.URLError as e:
            print(f"poll failed: {e}", file=sys.stderr)
            time.sleep(POLL_BACKOFF)
            continue
        except Exception as e:
            print(f"poll error: {e}", file=sys.stderr)
            time.sleep(POLL_BACKOFF)
            continue

        if not task:
            continue

        tid, cmd = task["id"], task["cmd"]
        print(f"task {tid}: {cmd}")
        result = run(cmd)
        try:
            _req("POST", f"/tasks/{tid}/result", result)
        except Exception as e:
            print(f"failed to post result for {tid}: {e}", file=sys.stderr)
            time.sleep(POLL_BACKOFF)


if __name__ == "__main__":
    main()
