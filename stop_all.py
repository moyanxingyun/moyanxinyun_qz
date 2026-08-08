# -*- coding: utf-8 -*-
"""Stop site, data service and tunnel."""
import pathlib
import subprocess

ROOT = pathlib.Path(__file__).resolve().parent
PIDFILES = [
    ROOT / "server.pid",
    ROOT / "backend" / "server.pid",
    ROOT / "tunnel.pid",
]


def kill_pidfile(path):
    try:
        pid = int(path.read_text(encoding="utf-8").strip())
    except Exception:
        return
    try:
        subprocess.run(
            ["taskkill", "/PID", str(pid), "/F"],
            capture_output=True,
            timeout=10,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        print(f"[ok] 已停止 pid {pid}")
    except Exception:
        pass
    try:
        path.unlink()
    except Exception:
        pass


def main():
    print("停止全部服务…")
    for f in PIDFILES:
        kill_pidfile(f)
    try:
        subprocess.run(
            ["taskkill", "/IM", "ssh.exe", "/F"],
            capture_output=True,
            timeout=10,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
    except Exception:
        pass
    print("已全部停止。")


if __name__ == "__main__":
    main()
