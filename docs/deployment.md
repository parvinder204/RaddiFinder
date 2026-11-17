# Deployment

A typical production setup is Ubuntu, PostgreSQL, gunicorn behind nginx, with HTTPS from Let's Encrypt. The same steps apply to other Linux hosts.

## Checklist

- [ ] A real `SECRET_KEY` of at least 32 random characters
- [ ] `DEBUG=0`
- [ ] `ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS` set to your domain
- [ ] `USE_HTTPS=1`, `SSL_REDIRECT=1` and `HSTS_SECONDS` set once HTTPS works
- [ ] Database created and migrated
- [ ] `collectstatic` run
- [ ] nginx serving `/static/` and `/media/`, except pickup photos
- [ ] Cron job installed
- [ ] MSG91 and SMTP credentials set
- [ ] Redis configured if you run more than one worker

## 1. Server packages

```bash
sudo apt update
sudo apt install -y python3-venv python3-dev libpq-dev nginx postgresql cron
```

## 2. Application

```bash
sudo mkdir -p /srv/raddifinder
sudo chown $USER /srv/raddifinder
cd /srv/raddifinder
git clone <your-repo-url> app
cd app
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt gunicorn
```

Add `redis` as well when using a Redis cache:

```bash
pip install redis
```

## 3. Environment

Create `/srv/raddifinder/app/.env` from `.env.example` and set at least:

```
SECRET_KEY=<64 random characters>
DEBUG=0
ALLOWED_HOSTS=example.com,www.example.com
CSRF_TRUSTED_ORIGINS=https://example.com,https://www.example.com
FDOMAIN=https://example.com
USE_HTTPS=1
SSL_REDIRECT=1
HSTS_SECONDS=31536000
TRUST_PROXY_SSL_HEADER=1
CLIENT_IP_HEADER=HTTP_X_REAL_IP
STATIC_ROOT=/srv/raddifinder/static
POSTGRESQLDATABASE=raddifinder
POSTGRESQLUSER=raddi
POSTGRESQLPASSWORD=<password>
CACHE_URL=redis://127.0.0.1:6379/1
OTP_CONSOLE_FALLBACK=0
```

Keep `.env` readable only by the application user:

```bash
chmod 600 .env
```

Turn on `SSL_REDIRECT` and `HSTS_SECONDS` only after HTTPS is working, otherwise you can lock yourself out.

### Environment variables

| Variable | Default | Purpose |
| --- | --- | --- |
| `SECRET_KEY` | none, required | Django secret. Must be strong when `DEBUG` is off. |
| `DEBUG` | `0` | Debug mode. Never enable in production. |
| `ALLOWED_HOSTS` | `localhost,127.0.0.1` | Comma-separated host names |
| `CSRF_TRUSTED_ORIGINS` | empty | Origins with scheme, for example `https://example.com` |
| `FDOMAIN` | empty | Public base URL used to build absolute image links in the API |
| `USE_HTTPS` | `0` | Marks session and CSRF cookies as Secure |
| `SSL_REDIRECT` | `0` | Redirect HTTP to HTTPS |
| `HSTS_SECONDS`, `HSTS_INCLUDE_SUBDOMAINS` | `0`, `0` | HTTP Strict Transport Security |
| `TRUST_PROXY_SSL_HEADER` | `0` | Trust `X-Forwarded-Proto` from the proxy |
| `CLIENT_IP_HEADER` | empty | Request header holding the real client IP, used for rate limits. Only set it to a header your proxy overwrites. |
| `API_DOCS_ENABLED` | same as `DEBUG` | Serve `/docs/` and `/redoc/` |
| `STATIC_ROOT` | `/var/www/RaddiFinder/static` | Where `collectstatic` writes |
| `CACHE_URL` | `locmemcache://` | Cache backend. Use Redis for multiple workers. |
| `LOG_LEVEL` | `INFO` | Root log level |
| `BACKGROUND_WORKERS` | `4` | Threads for sending notifications |
| `PICKUP_MIN_LEAD_DAYS` | `1` | Earliest bookable day, counted from today |
| `POSTGRESQLDATABASE`, `POSTGRESQLUSER`, `POSTGRESQLPASSWORD` | none, required | Database credentials |
| `POSTGRESQLHOST`, `POSTGRESQLPORT` | `localhost`, `5432` | Database address |
| `DB_CONN_MAX_AGE` | `60` | Persistent connection lifetime in seconds |
| `SESSION_IDLE_TIMEOUT_SECONDS` | `1800` | Sign out after this much inactivity |
| `SESSION_ABSOLUTE_TIMEOUT_SECONDS` | `43200` | Maximum session length |
| `SESSION_POLL_INTERVAL_SECONDS` | `30` | How often open tabs check the session |
| `SESSION_EXPIRE_AT_BROWSER_CLOSE` | `1` | Drop the session when the browser closes |
| `JWT_ACCESS_MINUTES`, `JWT_REFRESH_DAYS` | `5`, `1` | API token lifetimes |
| `EMAIL_BACKEND`, `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_USE_TLS`, `EMAIL_USE_SSL`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `EMAIL_TIMEOUT` | SMTP, port 587 with TLS | Outgoing mail |
| `DEFAULT_FROM_EMAIL`, `SERVER_EMAIL` | the SMTP user | Sender addresses |
| `ADMIN_NOTIFICATION_EMAILS` | empty | Comma-separated admins emailed on new requests |
| `MSG91_AUTH_KEY`, `MSG91_INTEGRATED_NUMBER`, `MSG91_NAMESPACE` | empty | MSG91 WhatsApp account |
| `MSG91_TEMPLATE_OTP`, `MSG91_TEMPLATE_PICKUP`, `MSG91_TEMPLATE_RECEIVED` | `raddi_finder`, `pickup_detail`, `received_raddifinder` | Approved template names |
| `MSG91_TIMEOUT` | `10` | Seconds before a send is abandoned |
| `OTP_CONSOLE_FALLBACK` | `0` | Print OTPs to the log instead of sending. Development only. |
| `OTP_LENGTH`, `OTP_EXPIRY_MINUTES`, `OTP_MAX_ATTEMPTS`, `OTP_RESEND_COOLDOWN_SECONDS` | `5`, `180`, `5`, `60` | OTP rules |
| `OTP_SEND_LIMIT`, `OTP_VERIFY_LIMIT`, `OTP_RATE_WINDOW_SECONDS` | `10`, `30`, `600` | Per-IP OTP rate limits |
| `SENTRY_DSN`, `SENTRY_TRACES_SAMPLE_RATE`, `SENTRY_SEND_PII` | empty, `0.0`, `0` | Error reporting |

## 4. Database and static files

```bash
sudo -u postgres psql -c "CREATE USER raddi WITH PASSWORD '<password>';"
sudo -u postgres psql -c "CREATE DATABASE raddifinder OWNER raddi;"

source .venv/bin/activate
python manage.py migrate
python manage.py import_states_cities
python manage.py createsuperuser
python manage.py collectstatic --noinput
mkdir -p media
```

## 5. gunicorn with systemd

`/etc/systemd/system/raddifinder.service`:

```ini
[Unit]
Description=RaddiFinder gunicorn
After=network.target postgresql.service

[Service]
User=www-data
Group=www-data
WorkingDirectory=/srv/raddifinder/app
ExecStart=/srv/raddifinder/app/.venv/bin/gunicorn RaddiFinder.wsgi:application --bind 127.0.0.1:8000 --workers 3 --timeout 60
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

Give the service user access to the app and media directories, then start it:

```bash
sudo chown -R www-data:www-data /srv/raddifinder/app/media
sudo systemctl daemon-reload
sudo systemctl enable --now raddifinder
```

Notifications run in a thread pool inside each worker, so no separate worker process is needed.

## 6. nginx

`/etc/nginx/sites-available/raddifinder`:

```nginx
server {
    listen 80;
    server_name example.com www.example.com;
    client_max_body_size 10M;

    location /static/ {
        alias /srv/raddifinder/static/;
        expires 30d;
    }

    location /media/pickup_request/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /media/ {
        alias /srv/raddifinder/app/media/;
        expires 7d;
    }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Pickup photos must go through Django, which checks that the viewer owns the order. The `/media/pickup_request/` block has to stay above the general `/media/` block.

Enable the site and add HTTPS:

```bash
sudo ln -s /etc/nginx/sites-available/raddifinder /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d example.com -d www.example.com
```

## 7. Scheduled jobs

```bash
cd /srv/raddifinder/app
source .venv/bin/activate
python manage.py crontab add
python manage.py crontab show
```

This installs the job that removes expired OTPs every three hours into the crontab of the user who ran it. Run `crontab add` as the same user each time, and again after upgrades that change `CRONJOBS`.

## 8. Updating

```bash
cd /srv/raddifinder/app
git pull
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py crontab add
sudo systemctl restart raddifinder
```

## Operations

| Task | How |
| --- | --- |
| View logs | `journalctl -u raddifinder -f` |
| Back up the database | `pg_dump -Fc raddifinder > raddifinder.dump` |
| Back up uploads | Copy the `media/` directory |
| Review deletions | Django admin at `/admin/`, section **Audit logs** (read only) |
| Error tracking | Set `SENTRY_DSN` |

## Scaling notes

- With more than one gunicorn worker or server, OTP and login rate limits only work correctly if `CACHE_URL` points to a shared cache such as Redis. With the default local-memory cache each worker keeps its own counters.
- Uploaded media lives on local disk. Behind several servers, put `media/` on shared storage.
- Set `CLIENT_IP_HEADER` only when a trusted proxy sets that header. Otherwise clients can fake their IP and dodge rate limits.
