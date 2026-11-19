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

### List pages

The admin requests, notifications, pickup boys, products and service areas pages, and the customer history and notification pages, are paginated on the server. The browser only receives the rows for the page it is showing. The admin pages also search on the server.

| Part | Role |
| --- | --- |
| `common_models/pagination.py` | Reads `q`, `per_page` and `page` from the URL, filters and slices the queryset, and builds the template context |
| `PaginatedSearchMixin` | Adds the same behaviour to any class-based list view |
| `templates/site_admin/partials/list_toolbar.html` | Page-size selector and search box, a plain GET form. On phones the selector and the search box stay on one row; the words "entries" and "Search:" are hidden and the box shows a "Search..." placeholder. |
| `templates/site_admin/partials/list_pager.html` | "Showing x to y of z" and the page links. The buttons read `< 1 2 3 ... n >` on every screen size. On phones the text is centred above the buttons. |
| `static/css/list-controls.css` | Layout of the admin list toolbar and footer at every screen width |
| `templates/customer/partials/pager.html` | The `< 1 2 3 ... n >` links for the customer pages. Hidden when there is only one page. |
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

Customer history and notifications use the same URL parameters (`page`, and `per_page` if given) without a search box. Opening a notifications page, admin or customer, marks only the notifications on the visible page as read. The mobile API history endpoint still returns every order in one response.

### notifications

`Notifications` and `Recipients` models back the in-app notification list. `sms.py` talks to MSG91. `dispatch.py` runs sends in a small thread pool after the database transaction commits, so a slow provider never blocks a request and a rolled-back order never sends a message.

## Reference IDs

Every product, pickup boy and pickup request has a short, readable reference next to its UUID.

| Record | Reference | Example |
| --- | --- | --- |
| Product (`Item`) | `PROD_<n>` | `PROD_12` |
| Pickup boy (`PickupBoy`) | `SRPB_<n>` | `SRPB_3` |
| Pickup request (`Pickup`) | `PKRQ_<n>` | `PKRQ_204` |

The UUID stays the primary key. URLs, forms, foreign keys, the API and all create, update and delete operations still use the UUID. The reference is only a label for people.

- **Where it is shown:** the ID column of the admin tables, the admin request page, the customer history and order pages, in-app notifications, admin emails, the invoice and the API (`reference` field next to `pickup_id`). Hovering the ID cell in the admin tables shows the UUID.
- **Search:** the admin request, product and pickup boy searches also match the reference.
- **How numbers are assigned:** `common_models/models/reference_models.py` keeps one counter row per prefix. A number is taken inside the same transaction that saves the record, under a row lock, so two requests at the same moment never get the same number. Numbers are never reused after a delete, and a record keeps its reference for life.
- **Existing data:** migration `0005_backfill_references` numbers existing rows in order of creation and rewrites old notification texts that contained a UUID. `0004` and `0006` add the column and then make it required and unique.
- **Adding another prefix:** make the model inherit `ReferenceModel`, set `reference_prefix`, and add a migration pair like `0004` to `0006`. Code that creates rows with `bulk_create` skips `save()`, so create those rows one by one.
- **WhatsApp:** see the note in [deployment.md](deployment.md#whatsapp-templates-and-reference-ids).

## Front-end design layer

All three front ends (customer site, admin dashboard, error and sign-in pages) share one design layer. The brand colours stay the same: teal `#16d7aa` and navy `#17213d`.

| File | Role |
| --- | --- |
| `static/css/theme.css` | Design tokens (colours, radii, shadows, font), the page background, cards, buttons, form fields, tables, rounded pagination buttons, dropdowns and the product grid. Loaded by every page. |
| `static/customer/css/modern.css` | Customer navbar, sidebar and profile panel, footer |
| `static/css/admin-modern.css` | Admin top bar, sidebar, footer, product thumbnails and the admin date-picker dropdown |
| `static/css/calendar-picker.css`, `static/js/calendar-picker.js` | The custom calendar |
| `templates/customer/partials/` | `navbar`, `sidebar`, `profile_panel`, `footer` and `nav_items`, included by `customer/base.html` |

Behaviour worth knowing:

- **Background:** one gradient on `body`, light blue from the left to light orange on the right, fixed so it does not move while scrolling.
- **Hover effects:** buttons, cards, table rows, menu items, pagination buttons and dropdown items lift or gain a shadow on hover. The effects are turned off for touch devices and when the visitor prefers reduced motion.
- **Product grid:** items sit in a centred flex grid with at most four per row on wide screens, three on tablets and two on phones. One item or two items stay centred. Images sit in a square frame and are fitted with `object-fit: contain`.
- **Pagination:** page buttons have an 8px radius.
- **Sidebars:** the customer menu and profile panel close from their close button, the backdrop or the Escape key. The admin sidebar has a toggle button in the top bar that collapses it to icons.
- **Footer:** a slim bar with the line "© year RaddiFinder. All rights reserved." on both the customer site and the admin dashboard.
- **Dropdowns:** every single-choice `<select>` is replaced by a custom dropdown (`static/js/select-picker.js`, `static/css/select-picker.css`) with the same white card, teal hover and teal selected row as the calendar. The real `<select>` stays in the page but hidden, so forms, `required` checks, `change` handlers and scripts that read or set the value, or replace the options (for example the city list after choosing a state), work as before. Add `data-native` to a select to keep the browser's own dropdown.
- **Responsive sizing:** text, table cells, buttons, form fields and pagination buttons step down at 991px, 767px and 575px (`theme.css`). The customer history table, product captions and admin dashboard stat cards have their own smaller sizes. Sidebar items and stat headings stay on one line and are shortened with an ellipsis if they do not fit.
- **Calendar:** every `input[type="date"]` is turned into a text field that opens the custom calendar when clicked, focused or when Enter, Space or the down arrow is pressed. Typing is blocked, so the value can only come from the calendar. The value is still stored as `YYYY-MM-DD`, so form posts and scripts that read the field are unchanged. Past days are disabled. The admin reschedule field keeps bootstrap-datepicker, which already opens from anywhere in the field, and is restyled in `admin-modern.css`.

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
