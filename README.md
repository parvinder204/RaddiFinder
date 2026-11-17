# RaddiFinder

RaddiFinder is a scrap ("raddi") pickup service. Customers choose the scrap they want to sell, book a date and time slot, and a pickup boy collects it. Admins approve requests, record the actual weights and prices at pickup, and customers receive an invoice.

## Features

- Customer sign-in with a WhatsApp OTP, no password needed on the web
- Item catalogue with prices per unit, booking by city, date and one-hour slot
- Editable open requests: add or remove items and change the address
- Admin dashboard for requests, products, pickup staff, service areas and sales totals
- Status flow: Requested, Approved, Rescheduled, Picked-up, Cancelled
- Invoice PDFs, in-app notifications, WhatsApp messages through MSG91 and admin emails
- JSON API with JWT authentication for the mobile app
- Audit log of deleted orders and order items
- Session timeouts, OTP lockout and per-IP rate limiting

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py import_states_cities
python manage.py createsuperuser
python manage.py runserver
```

Before running, edit `.env`: set `SECRET_KEY`, the `POSTGRESQL*` credentials, and `DEBUG=1` and `OTP_CONSOLE_FALLBACK=1` for local work. See [docs/Setup.md](docs/Setup.md) for the full walkthrough.

## Documentation

| Document | What is in it |
| --- | --- |
| [docs/Setup.md](docs/Setup.md) | Local installation, first-run tasks, running the tests |
| [docs/architecture.md](docs/architecture.md) | Apps, data model, request lifecycle, security design |
| [docs/APIs.md](docs/APIs.md) | Every mobile API endpoint with request and response examples, plus the web routes |
| [docs/workflow.md](docs/workflow.md) | Customer and admin journeys, order statuses, notifications |
| [docs/techstack.md](docs/techstack.md) | Languages, frameworks, services and front-end libraries |
| [docs/deployment.md](docs/deployment.md) | Production setup, environment variables, nginx and gunicorn, updates |

## Project layout

```
RaddiFinder/     settings and root URLs
accounts/        users, roles, OTP, throttling, session timeout
common_models/   catalogue and order models, order rules, audit log
customer_app/    customer web pages
customer_api/    mobile JSON API
site_admin/      admin dashboard
notifications/   in-app, email and WhatsApp notifications
templates/       Django templates
static/          CSS, JS, images and the front-end libraries in use
tests/           pytest suite
docs/            documentation
```

## Tests

```bash
pip install -r requirements-dev.txt
pytest
```

The tests need a PostgreSQL server reachable with the credentials in `.env`.

## Entry points

| URL | Purpose |
| --- | --- |
| `/` | Customer site |
| `/site_admin/` | Admin dashboard |
| `/admin/` | Django admin |
| `/docs/`, `/redoc/` | API documentation when `API_DOCS_ENABLED` is on |
