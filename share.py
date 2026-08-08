# -*- coding: utf-8 -*-
"""One-click share: start services + public tunnel, copy URL, open browser."""
import pathlib
import re
import subprocess
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parent
SITE_PID = ROOT / "server.pid"
API_PID = ROOT / "backend" / "server.pid"
TUNNEL_PID = ROOT / "tunnel.pid"
TUNNEL_URL = ROOT / "tunnel_url.txt"


def read_pid(path):
    try:
        return int(path.read_text(encoding="utf-8").strip())
    except Exception:
        return None


def process_alive(pid):
    if not pid:
        return False
    try:
        out = subprocess.check_output(
            ["tasklist", "/FI", f"PID eq {pid}"],
            text=True,
            timeout=10,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        return str(pid) in out
    except Exception:
        return False


def start(script, pidfile, label):
    if pidfile and process_alive(read_pid(pidfile)):
        print(f"[ok] {label} 已在运行")
        return
    p = subprocess.Popen(
        [sys.executable, str(script)],
        cwd=str(script.parent),
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
    if pidfile:
        pidfile.write_text(str(p.pid), encoding="utf-8")
    print(f"[ok] {label} 已启动 (pid {p.pid})")


def wait_tunnel_url(timeout=45):
    deadline = time.time() + timeout
    pattern = re.compile(r"https://[a-z0-9]+\.lhr\.life")
    while time.time() < deadline:
        try:
            text = TUNNEL_URL.read_text(encoding="utf-8").strip()
            m = pattern.search(text)
            if m:
                return m.group(0)
        except Exception:
            pass
        time.sleep(2)
    return None


def main():
    print("=" * 52)
    print("  校招情报终端 · 一键分享")
    print("=" * 52)

    start(ROOT / "site_server.py", SITE_PID, "网站服务  (localhost:8000)")
    start(ROOT / "backend" / "server.py", API_PID, "数据服务  (localhost:8001)")

    if process_alive(read_pid(TUNNEL_PID)):
        print("[ok] 公开隧道 已在运行")
    else:
        p = subprocess.Popen(
            [sys.executable, str(ROOT / "_tunnel.py")],
            cwd=str(ROOT),
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        TUNNEL_PID.write_text(str(p.pid), encoding="utf-8")
        print("[ok] 公开隧道 正在建立…")

    url = wait_tunnel_url()
    if not url:
        print("[!!] 未能获取公开地址，请检查网络后重试。")
        return

    print()
    print("  公开地址：" + url)
    print("  说明：电脑和此窗口保持开启期间，任何人都可通过该链接访问。")
    print()

    try:
        subprocess.run(
            ["powershell", "-NoProfile", "-Command", f"Set-Clipboard -Value '{url}'"],
            capture_output=True,
            timeout=15,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        print("[ok] 地址已复制到剪贴板")
    except Exception:
        pass

    try:
        subprocess.Popen(
            ["powershell", "-NoProfile", "-Command", f"Start-Process '{url}'"],
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        print("[ok] 已在浏览器中打开")
    except Exception:
        pass

    print()
    print("  关闭此窗口 = 停止分享；再次运行本脚本可重新生成地址。")


if __name__ == "__main__":
    main()
