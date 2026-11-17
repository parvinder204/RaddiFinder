# Setup

Local development setup for RaddiFinder.

## Requirements

- Python 3.10 or newer
- PostgreSQL 13 or newer
- pip and venv

## 1. Get the code and create a virtual environment

```bash
git clone <your-repo-url> RaddiFinder
cd RaddiFinder
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

On Windows activate with `.venv\Scripts\activate`.

## 2. Create the database

```sql
CREATE DATABASE raddifinder;
CREATE USER raddi WITH PASSWORD 'change-this';
GRANT ALL PRIVILEGES ON DATABASE raddifinder TO raddi;
```

On PostgreSQL 15 and newer also run `GRANT ALL ON SCHEMA public TO raddi;` while connected to the new database.

## 3. Configure the environment

```bash
cp .env.example .env
```

Fill in at least these values:

| Variable | Purpose |
| --- | --- |
| `SECRET_KEY` | Any long random string. Required. With `DEBUG` off it must be at least 32 characters and not a placeholder. |
| `DEBUG` | Set `1` for local development. |
| `POSTGRESQLDATABASE`, `POSTGRESQLUSER`, `POSTGRESQLPASSWORD` | Database credentials. |
| `POSTGRESQLHOST`, `POSTGRESQLPORT` | Default to `localhost` and `5432`. |
| `OTP_CONSOLE_FALLBACK` | Set `1` locally so OTPs print to the console instead of being sent through MSG91. |

Generate a secret key with:

```bash
python -c "from django.core.management.utils import get_random_secret_key as g; print(g())"
```

The full list of variables is in [deployment.md](deployment.md#environment-variables).

## 4. Prepare the database

```bash
python manage.py migrate
python manage.py import_states_cities
python manage.py createsuperuser
```

`import_states_cities` loads the Indian states and cities from `common_models/indian_states.csv` and `common_models/indian_cities.csv`. Pass `--states` and `--cities` to use other files.

`createsuperuser` asks for a phone number or email and a password. The account gets the `SuperUser` role and signs in at `/site_admin/`.

## 5. Mark cities as serviceable

Customers can only book in cities flagged as available. Sign in to the admin dashboard and use **Manage Service Areas**, or toggle `available` on a city in Django admin at `/admin/`.

## 6. Add items

Use **Manage Product** in the admin dashboard to create the scrap items (name, unit, price, image) that customers choose from.

## 7. Run the server

```bash
python manage.py runserver
```

| URL | What it is |
| --- | --- |
| `http://localhost:8000/` | Customer site |
| `http://localhost:8000/site_admin/` | Admin dashboard login |
| `http://localhost:8000/admin/` | Django admin |
| `http://localhost:8000/docs/` | Swagger UI, only when `API_DOCS_ENABLED` is on (default: same as `DEBUG`) |

## Running the tests

```bash
pip install -r requirements-dev.txt
pytest
```

The tests use PostgreSQL, so the database credentials in `.env` must work. pytest-django creates and removes its own `test_` database. Test defaults for `SECRET_KEY` and the cache are set in `pyproject.toml` and only apply when your environment does not already define them.

## Optional: scheduled cleanup

Expired OTPs are purged by a cron job every three hours.

```bash
python manage.py crontab add
python manage.py crontab show
```

Run `crontab add` again after every deploy that changes `CRONJOBS`.

## Common problems

| Symptom | Fix |
| --- | --- |
| `ImproperlyConfigured: SECRET_KEY must be a unique value...` | Set a real `SECRET_KEY` in `.env`, or set `DEBUG=1` for local work. |
| `django.core.exceptions.ImproperlyConfigured: Set the POSTGRESQL... environment variable` | A database variable is missing from `.env`. |
| OTP never arrives | Set `OTP_CONSOLE_FALLBACK=1` locally, or configure the `MSG91_*` variables. |
| Customer cannot pick a city | The city is not marked available. |
| Pickup date rejected | The earliest bookable date is set by `PICKUP_MIN_LEAD_DAYS` (default 1, so tomorrow). |
