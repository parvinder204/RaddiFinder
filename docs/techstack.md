# Tech stack

## Backend

| Area | Choice | Notes |
| --- | --- | --- |
| Language | Python 3.10+ | |
| Framework | Django 4.2 to 5.2 | Server-rendered pages for customers and admins. |
| REST API | Django REST Framework 3.15 | Used by the mobile app under `/customer_api/`. |
| API auth | djangorestframework-simplejwt 5.3 | Short-lived access tokens and blacklistable refresh tokens. |
| API docs | drf-yasg | Swagger UI and ReDoc, switched on by `API_DOCS_ENABLED`. |
| Config | django-environ | All settings come from `.env` or real environment variables. |
| Scheduling | django-crontab | One job that deletes expired OTPs. |
| Admin import/export | django-import-export | CSV import and export for states, cities and items in Django admin. |

## Data

| Area | Choice |
| --- | --- |
| Database | PostgreSQL through psycopg2 |
| Primary keys | UUIDs on every model |
| Cache | Django cache, local memory by default. Set `CACHE_URL` to Redis for shared rate limiting across processes. |
| Files | Local media directory for item images, profile pictures and pickup photos |

## Integrations

| Service | Used for |
| --- | --- |
| MSG91 WhatsApp | Sending OTPs, "request received" messages and pickup-boy details |
| SMTP | Emailing admins when a request arrives |
| Sentry | Error reporting, enabled when `SENTRY_DSN` is set |

## Documents and images

| Library | Used for |
| --- | --- |
| xhtml2pdf | Rendering invoice PDFs from an HTML template |
| Pillow | Validating and handling uploaded images |
| requests | Calling the MSG91 API |

## Front end

The front end is server-rendered Django templates with no build step. Static assets are committed under `static/`.

| Part | Libraries |
| --- | --- |
| Admin dashboard | Bootstrap 5, jQuery, ApexCharts, MetisMenu, SimpleBar, bootstrap-datepicker, bootstrap-timepicker, jQuery Validation, Parsley. Only the DataTables stylesheets remain, to style the server-side lists. |
| Customer site | Bootstrap, Font Awesome 4.7 and project scripts in `static/customer/js` |
| Admin lists | Server-side pagination and search, with `static/js/list-controls.js` for the search box and page-size selector |
| Shared | `static/js/session-sync.js` keeps tabs in sync when a session ends |

## Testing

| Tool | Purpose |
| --- | --- |
| pytest | Test runner |
| pytest-django | Database and Django settings integration |
| pytest-env | Test-only environment defaults, defined in `pyproject.toml` |

## Runtime in production

| Layer | Typical choice |
| --- | --- |
| WSGI server | gunicorn (install it separately, it is not in `requirements.txt`) |
| Reverse proxy | nginx, serving `/static/` and `/media/` |
| Process manager | systemd |
