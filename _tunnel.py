import subprocess
import sys
import re

log = open("tunnel_log.txt", "w", encoding="utf-8", buffering=1)
url_file = open("tunnel_url.txt", "w", encoding="utf-8")
p = subprocess.Popen(
    [
        "ssh",
        "-o", "StrictHostKeyChecking=accept-new",
        "-o", "ServerAliveInterval=60",
        "-o", "ExitOnForwardFailure=yes",
        "-R", "80:localhost:8000",
        "nokey@localhost.run",
    ],
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    stdin=subprocess.PIPE,
    text=True,
    encoding="utf-8",
    errors="replace",
    bufsize=1,
)

url_pattern = re.compile(r"https://[a-z0-9]+\.lhr\.life")
for line in p.stdout:
    log.write(line)
    log.flush()
    m = url_pattern.search(line)
    if m:
        url_file.write(m.group(0) + "\n")
        url_file.flush()
log.close()
url_file.close()
p.wait()
sys.exit(p.returncode)
