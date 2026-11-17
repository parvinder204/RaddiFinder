# APIs

RaddiFinder exposes a JSON API for the mobile app under `/customer_api/` and token endpoints under `/accounts/`. When `API_DOCS_ENABLED` is on, interactive documentation is served at `/docs/` (Swagger) and `/redoc/`.

## Conventions

- Base URL: the value of `FDOMAIN`, for example `https://example.com`.
- Authenticated endpoints need the header `Authorization: Bearer <access token>`.
- Request bodies are JSON unless noted. File uploads use `multipart/form-data`.
- Phone numbers are 10-digit Indian mobile numbers without a country code.
- Access tokens last 5 minutes and refresh tokens last 1 day by default (`JWT_ACCESS_MINUTES`, `JWT_REFRESH_DAYS`).
- OTP endpoints are rate limited per client IP. Exceeding the limit returns `429`.

### Response shapes

The API has two response styles because older endpoints were kept compatible with the existing app.

| Style | Used by | Example |
| --- | --- | --- |
| Envelope | OTP, password, logout | `{"status": "success", "data": {...}}` or `{"status": "error", "data": "message"}` |
| Legacy string | Order endpoints | HTTP 200 with the body `{'success':'Request Successfully Updated'}` or `{'error':'message'}` as a plain string |

For legacy-style endpoints check for the words `success` or `error` in the string, not the HTTP status.

## Registration and sign-in

A new customer registers in four steps: send OTP, verify OTP, set password, save details.

### POST `/customer_api/api/send-otp`

Send a WhatsApp OTP to a new number. Numbers that already have an account are rejected.

```json
{ "phone": "9876543210" }
```

| Status | Meaning |
| --- | --- |
| 200 | `{"status": "success", "data": {"phone": "9876543210"}}` |
| 400 | Invalid number, or `phone already exist` |
| 429 | Rate limited |
| 503 | The OTP could not be delivered |

A new OTP is not sent while the previous one is inside the resend cooldown (`OTP_RESEND_COOLDOWN_SECONDS`, default 60).

### GET `/customer_api/api/resend-otp?phone=9876543210`

Sends a fresh OTP, subject to the same cooldown. Returns a plain string on success.

### POST `/customer_api/api/verify-otp`

```json
{ "phone": "9876543210", "otp": "12345" }
```

`phone` may be omitted if it was sent earlier in the same session.

| Status | Meaning |
| --- | --- |
| 200 | `{"status": "success", "data": {"otp": "12345"}}` |
| 400 | Wrong, expired or locked code. The code locks after `OTP_MAX_ATTEMPTS` failures (default 5). |

### POST `/customer_api/api/password`

Creates the account for a number whose OTP was verified, and signs the user in. The verified OTP is consumed, so this works once.

```json
{ "phone": "9876543210", "password": "a-strong-password" }
```

Passwords must be at least 8 characters and pass Django's password validators.

```json
{
  "status": "success",
  "data": { "phone": "9876543210", "refresh": "<jwt>", "access": "<jwt>" }
}
```

### PUT `/customer_api/api/register-details` (auth)

Saves the profile after registration. All fields are optional.

```json
{
  "first_name": "Asha",
  "last_name": "Verma",
  "email": "asha@example.com",
  "address": "House 12, Sector 70",
  "state": "<state uuid>",
  "city": "<city uuid>",
  "pin_code": "160055"
}
```

An empty `email` clears it. An email already used by another account returns `400` with `A user with that email already exists.`

### POST `/accounts/api/token/`

Sign in an existing user.

```json
{ "phone": "9876543210", "password": "a-strong-password" }
```

Returns `{"refresh": "...", "access": "..."}`.

### POST `/accounts/api/token/refresh/`

```json
{ "refresh": "<refresh token>" }
```

Returns a new `access` token.

### POST `/customer_api/api/logout`

Blacklists the refresh token.

```json
{ "refresh": "<refresh token>" }
```

## Account

### GET, PUT, PATCH `/customer_api/api/update_setting` (auth)

Read or update the signed-in customer. Updates are always partial. Send `multipart/form-data` when changing `image`.

Fields: `image`, `first_name`, `last_name`, `email`, `phone` (read only), `address`, `state`, `city`, `pin_code`.

### GET `/customer_api/api/recipient-notification` (auth)

Returns the customer's notifications as `[{"subject", "content", "url"}]`, or `{"error": "Empty notifications"}` when there are none.

## Catalogue

These endpoints need no authentication.

| Method and path | Returns |
| --- | --- |
| GET `/customer_api/api/dashboard_items` | Items with all model fields |
| GET `/customer_api/api/apigetpost` | `[{"id", "name", "price", "unit", "image"}]` with absolute image URLs and a placeholder when an item has no image |
| GET `/customer_api/api/states` | All states |
| GET `/customer_api/api/cities` | All cities, each with an `available` flag. Only available cities accept bookings. |

## Orders

All order endpoints need authentication and only touch the caller's own orders.

### POST `/customer_api/api/confirm-request`

Creates a pickup request.

| Field | Notes |
| --- | --- |
| `date` | `YYYY-MM-DD`. Must be at least `PICKUP_MIN_LEAD_DAYS` days ahead (default 1, so tomorrow or later). |
| `time-slot` | One of `9-10`, `10-11`, `11-12`, `12-1`, `1-2`, `2-3`, `3-4`, `4-5`, `5-6` |
| `notes` | Optional text |
| `address` | Required |
| `state`, `city` | UUIDs. The city must be available. |
| `pin-code` | 6 digits |
| `data-list` | Items as `[{"id": "<item uuid>", "quantity": "2.5"}]`. Quantities must be above 0 and below 1000. Repeated ids are summed. |

On success the body is `{'success': 'Request successfully created'}` (legacy string) and the admins are notified.

### GET `/customer_api/api/history`

Returns the customer's orders:

```json
[
  {
    "pickup_id": "<uuid>",
    "pickup_date": "2026-11-20",
    "status": "Requested",
    "estimated_amount": "120.00",
    "total_amount": null
  }
]
```

When there are none the body is `{"error": "History is blank"}`.

### GET `/customer_api/api/view-order/<pickup_id>`

Returns one order with its items, `expected_amount` (from catalogue prices), `final_amount` (from the actual weights and prices recorded at pickup) and `customer_name`. Returns `404` for orders that belong to someone else.

### POST `/customer_api/api/user-item-add`

Adds items to an open order. Quantities of an item already on the order are added together.

```json
{ "pickup_id": "<uuid>", "items": [{ "id": "<item uuid>", "quantity": "1.5" }] }
```

Older clients may send `checks` and `quantity` lists instead of `items`.

### DELETE `/customer_api/api/user-item-delete/<order item uuid>`

Removes one line from an open order.

### PUT `/customer_api/api/user-update-address/<pickup_id>`

```json
{ "address": "New address", "state": "<uuid>", "city": "<uuid>", "pin_code": "160055" }
```

Orders that are `Cancelled` or `Picked-up` cannot be changed. Item and address endpoints return `{'error':'...'}` for them.

## Web endpoints used by the site

These are server-rendered pages and form posts, not part of the mobile API. They are listed for reference.

### Customer site (`/`)

| Path | Purpose |
| --- | --- |
| `/` | Redirects to item selection |
| `/select-items` | Choose scrap items |
| `/phone-number`, `/popup-login` | OTP sign-in |
| `/create-otp`, `/check-otp` | AJAX endpoints that send and check an OTP |
| `/forgot-password`, `/forgot-new` | Password reset by OTP |
| `/details` | Address details after sign-in |
| `/confirm-request` | Review and submit a request |
| `/history`, `/view-order/<id>` | Order list and detail |
| `/get-invoice/<id>` | Invoice PDF for a picked-up order |
| `/account-settings`, `/account-deactivation` | Profile and account closure |
| `/notifications` | Notification list |

### Admin dashboard (`/site_admin/`)

| Path | Purpose |
| --- | --- |
| `/` | Admin sign-in |
| `/dashboard` | Totals, charts and top items |
| `/manage-requests`, `/view-request/<id>` | List requests and change their status |
| `/update-request-address` | Edit a request's address |
| `/delete-pickup-item` | Remove an item from an open request. Recorded in the audit log. |
| `/order_delete` | Delete a request. Recorded in the audit log. |
| `/manage-products`, `/add-product` | Catalogue |
| `/manage-pickup-boy`, `/add-pickup` | Pickup staff |
| `/avail_city`, `/add_new_city` | Service areas |
| `/notifications` | Admin notifications |

Admin endpoints require a user with the `Admin` or `SuperUser` role. Non-admins are redirected or receive `403`.

### List page parameters

The pages `/manage-requests`, `/notifications`, `/manage-pickup-boy`, `/manage-products` and `/avail_city` are paginated and searched on the server. They all accept the same query parameters.

| Parameter | Values | Default |
| --- | --- | --- |
| `page` | Page number. A number past the end returns the last page and an invalid number returns page 1. | `1` |
| `per_page` | `10`, `25`, `50` or `100`. Other values fall back to the default. | `10` |
| `q` | Search text, up to 100 characters. Words are combined with AND. | empty |

Example: `/site_admin/manage-requests?q=approved&per_page=25&page=2`.

Posting an edit or delete to one of these pages, or to `/order_delete` and `/avail_city/<id>`, with the same query string redirects back to the list with those parameters kept.

### Other

| Path | Purpose |
| --- | --- |
| `/admin/` | Django admin, including the read-only audit log |
| `/media/pickup_request/<file>` | Pickup photos, served only to the owning customer and admins |
| `/utilities/fetch-cities` | Returns the cities of a state for the city drop-downs |
