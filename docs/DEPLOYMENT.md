# CONNECTBOOK – PRODUCTION DEPLOYMENT GUIDE

## 1. Production Architecture Overview
For production deployments on Linux/Windows VPS, ConnectBook operates via Daphne behind Nginx or Caddy with automated SSL certificate renewal (Let's Encrypt).

## 2. Environment Variables (.env)
```ini
SECRET_KEY=generate-a-strong-random-50-character-key
DEBUG=False
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
PORT=8002
```

## 3. SQLite Storage Guidelines
- **Persistent Storage:** SQLite requires direct POSIX filesystem persistence. Never deploy ConnectBook to ephemeral containers (like basic Heroku dynos) where the filesystem resets.
- **Single Process Instance:** SQLite should only be written to by a single application instance to prevent database lock contention.
- **InMemoryChannelLayer Limitation:** In production environments spanning multiple worker processes, Django Channels requires an external channel layer (e.g., Redis). For single-instance VPS setups, `InMemoryChannelLayer` continues to function efficiently.

## 4. Reverse Proxy Configuration (Nginx)
```nginx
server {
    server_name yourdomain.com;

    location /static/ {
        alias /var/www/connectbook/staticfiles/;
    }

    location /media/ {
        alias /var/www/connectbook/media/;
    }

    location /ws/ {
        proxy_pass http://127.0.0.1:8002;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_redirect off;
    }

    location / {
        proxy_pass http://127.0.0.1:8002;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## 5. Systemd Service (Daphne ASGI)
```ini
[Unit]
Description=ConnectBook Daphne ASGI Server
After=network.target

[Service]
User=www-data
WorkingDirectory=/var/www/connectbook
ExecStart=/var/www/connectbook/venv/bin/daphne -b 127.0.0.1 -p 8002 connectbook.asgi:application
Restart=always

[Install]
WantedBy=multi-user.target
```
