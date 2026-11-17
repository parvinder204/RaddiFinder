# Workflow

How an order moves through RaddiFinder, from the customer's first visit to the invoice.

## Roles

| Role | Can do |
| --- | --- |
| Customer | Sign in with OTP, request pickups, edit open requests, view history, download invoices |
| Admin | Everything in the dashboard: requests, products, pickup staff, service areas |
| SuperUser | Same as Admin, plus Django admin |

## Order statuses

| Status | Meaning |
| --- | --- |
| Requested | Created by the customer, waiting for review |
| Approved | Accepted by an admin and assigned to a pickup boy |
| Rescheduled | Moved to a new date or time slot by an admin |
| Picked-up | Collected and paid. Shown to customers as "Picked-up and Paid". |
| Cancelled | Closed with a reason |

```
Requested ──> Approved ──> Picked-up
    │            │
    │            └──> Rescheduled ──> Approved ...
    └──> Cancelled (from any open status)
```

`Picked-up` and `Cancelled` orders are locked. Customers and admins can no longer add or remove items or change the address. Admins can still change a status from the request page.

## Customer journey

1. **Browse.** The home page lists the scrap items with their price per unit.
2. **Choose items.** The customer enters a quantity for each item (above 0 and below 1000, up to three decimals).
3. **Sign in.** The customer enters a phone number and receives a WhatsApp OTP.
   - The code expires after 180 minutes by default.
   - There is a 60 second resend cooldown.
   - Five wrong attempts lock the code, and a new one must be requested.
   - A first-time number creates a customer account automatically.
4. **Details.** First-time customers add their name, email (optional), address, state, city and PIN code.
5. **Pick a slot.** The customer picks a date and a one-hour slot between 9 am and 6 pm. The date must be at least `PICKUP_MIN_LEAD_DAYS` days ahead, so tomorrow or later by default. Only cities marked available are accepted.
6. **Confirm.** The request is saved as `Requested`. The customer gets a "request received" WhatsApp message and the admins are notified by email and in the dashboard.
7. **Track.** The history page lists orders with the estimated amount. While an order is open the customer can add items, remove items and change the address.
8. **After pickup.** Once paid, the order shows the actual weights, prices and total, and the customer can download the invoice PDF.

Customers can also close their account from the account page, which asks for an OTP first.

### Mobile app

The app follows the same steps through the API. It signs in with a phone number and password instead of an OTP, after registering once with OTP and a password. See [APIs.md](APIs.md).

## Admin journey

1. **New request.** A new request appears under **Manage Requests** and as a notification.
2. **Review.** The admin opens the request to see the customer, address, date, slot, items and any photo.
3. **Approve.** The admin picks an employed pickup boy and sets the status to `Approved`. The customer receives the pickup boy's details on WhatsApp. Changing the pickup boy on an approved order sends the update again.
4. **Reschedule, if needed.** The admin chooses a new date and slot. The earlier date and slot are saved in the order history and the customer is notified.
5. **Collect.** At pickup the pickup boy weighs each item. The admin enters the actual quantity and price per item, which can include items the customer did not list, then the payment amount, and sets the status to `Picked-up`.
6. **Cancel, if needed.** Setting `Cancelled` stores the admin's note as the cancellation reason and notifies the customer.
7. **Delete, rarely.** Admins can delete a request or one item of an open request. Each deletion is recorded in the audit log with the admin's account and a full snapshot.

Statuses `Approved`, `Rescheduled` and `Picked-up` require a pickup boy.

### Other admin work

| Task | Where |
| --- | --- |
| Add or edit scrap items and prices | Manage Product |
| Add pickup boys, mark them employed or not | Manage Pickup Boy |
| Open or close a city for bookings | Manage Service Areas |
| Read notifications | Notification |
| View totals, charts and top items | Home |

## Money

| Figure | Calculation |
| --- | --- |
| Estimated amount | quantity × catalogue price, summed over items |
| Final amount | actual quantity × final price, summed over items |
| Payment | The amount the admin records when marking an order `Picked-up` |
| Dashboard top items | Per item, actual quantity × final price where recorded, otherwise the estimate, for picked-up orders only |

## Notifications

| Event | Customer | Admin |
| --- | --- | --- |
| Request created | In-app and WhatsApp "received" | Email and in-app |
| Approved or pickup boy changed | In-app and WhatsApp with pickup boy details | |
| Rescheduled | In-app | |
| Picked up | In-app | |
| Cancelled | In-app | |

Messages are sent in the background after the order is saved. A failed send is logged and does not affect the order.

## Scheduled work

| Job | Schedule | Effect |
| --- | --- | --- |
| `customer_app.cron.delete_old_otps` | Every 3 hours | Deletes expired OTP rows |

## Session behaviour

Sessions end after 30 minutes without activity or after 12 hours in total. Open tabs poll the server and sign out together when a session ends.
