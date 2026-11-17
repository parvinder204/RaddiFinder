# Architecture

RaddiFinder is a single Django project made of small apps. Customers and admins use server-rendered pages. The mobile app uses a JSON API that shares the same business logic.

## High-level view

```
 Customer browser ─┐                       ┌─> PostgreSQL
 Admin browser ────┼──> Django project ────┼─> Media files (images)
 Mobile app ───────┘   (views + services)  ├─> MSG91 WhatsApp (OTP, pickup details)
                                           ├─> SMTP (admin emails)
                                           └─> Sentry (errors)
```

## Project layout

```
RaddiFinder/          project settings, root URLs, WSGI and ASGI
accounts/             users, roles, OTP, rate limiting, session timeout
common_models/        catalogue and order models plus order business logic
customer_app/         customer web pages
customer_api/         JSON API for the mobile app
site_admin/           admin dashboard
notifications/        in-app notifications, admin email, WhatsApp
templates/            Django templates for all three front ends
static/               CSS, JS, images and front-end libraries
tests/                pytest suite, one folder per app
docs/                 this documentation
```

## Apps

### accounts

| Piece | Role |
| --- | --- |
| `Person` | The custom user. The phone number is the login ID. Roles are `Customer`, `Admin` and `SuperUser`. |
| `OTP` | One row per phone number with the code, failed attempts, last-sent time and a verified flag. |
| `services.py` | Issues, verifies and consumes OTPs. Handles expiry, attempt lockout and resend cooldown inside database transactions. |
| `throttling.py` | Per-IP rate limits for OTP send and verify, for both web and API. |
| `middleware.py` | Idle and absolute session timeouts, and `no-store` cache headers. |
| `backends.py` | Lets a user sign in with phone or email plus password. |
| `decorators.py`, `restriction.py`, `roles.py` | Role checks for views. Admin-only views reject customers with `403`. |
| `utils.py` | Input cleaning for names, emails and PIN codes, email uniqueness, safe redirects. |

### common_models

| Model | Purpose |
| --- | --- |
| `State`, `City` | Locations. A city has an `available` flag that controls whether bookings are accepted. |
| `Item` | A scrap type with unit and price per unit. |
| `Pickup` | An order: customer, status, date, time slot, address, pickup boy, payment and a JSON field for admin notes and reschedule history. |
| `PickupItems` | A line on an order with the estimated `quantity` and the `actual_quantity` and `final_price` recorded at pickup. |
| `Cancellation` | The reason for a cancelled order. Kept in sync with the order status. |
| `PickupBoy` | Staff who collect orders. |
| `AuditLog` | Who deleted what, with a JSON snapshot of the deleted order or order item. |

`services.py` holds the order rules: parsing and validating item quantities, creating requests, checking the pickup date and time slot, locking `Cancelled` and `Picked-up` orders against edits, adding and removing items, and updating addresses. Both the web views and the API call these functions, so the rules exist in one place.

`audit.py` writes audit entries and builds the snapshots.

### customer_app

Server-rendered customer flow: sign in with OTP, choose items, enter details, confirm a request, track orders, download invoices, manage the account. `cron.py` holds the OTP cleanup job.

### customer_api

DRF views and serializers for the mobile app. Registration is OTP then password then profile. Order endpoints call `common_models.services`. Some responses keep a legacy string format for compatibility with the shipped app.

### site_admin

The admin dashboard. Admins review requests, approve them with a pickup boy, reschedule, record actual weights and prices, mark orders as picked up and paid, cancel with a reason, and manage products, staff and service areas. The dashboard aggregates totals and the top items by realised value.

### Admin list pages

The requests, notifications, pickup boys, products and service areas pages are paginated and searched on the server. The browser only receives the rows for the page it is showing.

| Part | Role |
| --- | --- |
| `site_admin/pagination.py` | Reads `q`, `per_page` and `page` from the URL, filters and slices the queryset, and builds the template context |
| `PaginatedSearchMixin` | Adds the same behaviour to any class-based list view |
| `templates/site_admin/partials/list_toolbar.html` | Page-size selector and search box, a plain GET form |
| `templates/site_admin/partials/list_pager.html` | "Showing x to y of z" and the page links |
| `static/js/list-controls.js` | Submits the form when the page size changes or after a short pause in typing, and puts the cursor back in the search box |

The whole list state lives in the URL, for example `/site_admin/manage-requests?q=asha&per_page=25&page=2`. Refreshing, bookmarking or sharing the link shows the same page. Changing the search or page size starts again from page 1. A page number past the end shows the last page, and an invalid one shows page 1.

Edit, delete and add actions return to the same list with the same `q`, `per_page` and `page`, so the admin stays where they were.

Search words are combined with AND, and each word can match any of the page's search fields:

| Page | Search matches |
| --- | --- |
| Requests | Order ID, customer name, customer phone, pickup boy name, status words (`approved`, `cancelled`, `raised`, `paid` and so on) and dates written as `dd-mm-yyyy` |
| Notifications | Subject and content |
| Pickup boys | Name and phone |
| Products | Name, unit, description and price |
| Service areas | City and state |

Opening the notifications page marks only the notifications on the visible page as read.

### notifications

`Notifications` and `Recipients` models back the in-app notification list. `sms.py` talks to MSG91. `dispatch.py` runs sends in a small thread pool after the database transaction commits, so a slow provider never blocks a request and a rolled-back order never sends a message.

## Request lifecycle

1. The request passes through the standard Django middleware, then `SessionTimeoutMiddleware` which signs out idle or expired sessions, and `NoStoreMiddleware`.
2. A view checks the role, validates input and calls a function in a `services` module.
3. The service changes the database inside `transaction.atomic()` and raises a domain error on invalid input.
4. The view turns the result into a page, a redirect with a message, or JSON.
5. Notifications are queued with `transaction.on_commit`.

## Data model

```
Person 1───* Pickup *───1 City *───1 State
                │
                ├───* PickupItems *───1 Item
                ├───1 Cancellation (only for cancelled orders)
                └───0..1 PickupBoy

Person 1───* AuditLog (actor, set to null if the user is removed)
OTP: one row per phone number, not linked to Person
```

## Security design

| Concern | Approach |
| --- | --- |
| Sign-in | OTP for customers on the web, password for admins and the mobile API |
| OTP abuse | Constant-time comparison, attempt lockout, resend cooldown, expiry and per-IP rate limits |
| Sessions | Idle and absolute timeouts, HttpOnly and SameSite cookies, optional Secure cookies |
| Access control | Customers can only read their own orders, invoices and pickup photos. Admin views require an admin role. |
| Secrets | Everything from environment variables. The app refuses to start with a weak `SECRET_KEY` when `DEBUG` is off. |
| Audit | Deleting an order or an order item writes an `AuditLog` row |

## Testing

Tests live in `tests/`, one folder per app, with shared fixtures in `tests/conftest.py`. They cover OTP rules, email uniqueness, order validation, the audit log, the API serializers and the admin delete and dashboard logic.
