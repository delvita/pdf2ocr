# gunicorn_config.py
import os

# Server socket
bind = "0.0.0.0:5000"
backlog = 2048

# Worker processes
workers = 4
worker_class = "sync"  # Für CPU-intensive Tasks wie OCR
worker_connections = 1000

# Worker timeout (in seconds)
# Wichtig: OCR-Verarbeitung kann lange dauern (PDF zu Bild, OCR pro Seite, PDF-Erstellung).
# Ohne diese Werte nutzt Gunicorn standardmäßig 30s → WORKER TIMEOUT bei langer OCR.
# Per Umgebung überschreibbar (z. B. Coolify / docker-compose).
_default_timeout = int(os.environ.get("GUNICORN_TIMEOUT", "900"))
timeout = _default_timeout
graceful_timeout = int(os.environ.get("GUNICORN_GRACEFUL_TIMEOUT", str(_default_timeout)))
keepalive = 2  # Zeit, die Keep-Alive-Verbindungen aufrechterhalten werden

# Restart workers nach N Requests (um Memory Leaks zu vermeiden)
max_requests = 1000
max_requests_jitter = 100

# Logging
accesslog = "-"  # stdout
errorlog = "-"   # stderr
loglevel = "info"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Process naming
proc_name = "pdf2ocr"

# Server mechanics
daemon = False
pidfile = None
umask = 0
user = None
group = None
tmp_upload_dir = None

# Limits (für große Dateien)
limit_request_line = 8190
limit_request_fields = 100
limit_request_field_size = 8190

# SSL (falls später nötig)
# keyfile = None
# certfile = None

