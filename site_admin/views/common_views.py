import json
from datetime import timedelta
from decimal import Decimal

from django.db.models import Count, DecimalField, F, Q, Sum
from django.db.models.functions import Coalesce
from django.urls import reverse_lazy
from django.utils import timezone
from django.shortcuts import render
from django.views import View
from django.views.generic import TemplateView

from accounts.restriction import RestrictUserMixin
from common_models.models import Item, Pickup, PickupItems
from notifications.models import Recipients
from common_models.pagination import list_context, paginate

PENDING_STATUSES = ("Requested", "Approved")
PERIOD_DAYS = {"today": 0, "week": 7, "month": 30}
MONEY = DecimalField(max_digits=14, decimal_places=2)
ESTIMATED_AMOUNT = F("quantity") * F("item__price")
ACTUAL_AMOUNT = F("actual_quantity") * F("final_price")
REALISED_AMOUNT = Coalesce(ACTUAL_AMOUNT, ESTIMATED_AMOUNT, output_field=MONEY)


def _js_safe_json(data):
    return (
        json.dumps(data)
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("&", "\\u0026")
        .replace("'", "\\u0027")
    )


def _period_orders(period, today):
    days = PERIOD_DAYS[period]
    if days == 0:
        return Pickup.objects.filter(pickup_date=today)
    return Pickup.objects.filter(pickup_date__range=(today - timedelta(days=days), today))


def _period_stats(period, today):
    orders = _period_orders(period, today)
    counts = orders.aggregate(
        orders=Count("pickup_id"),
        pending=Count("pickup_id", filter=Q(status__in=PENDING_STATUSES)),
        received=Count("pickup_id", filter=Q(status="Picked-up")),
        cancelled=Count("pickup_id", filter=Q(status="Cancelled")),
    )
    amounts = PickupItems.objects.filter(pickup__in=orders).aggregate(
        total=Sum(ESTIMATED_AMOUNT, output_field=MONEY),
        received=Sum(
            REALISED_AMOUNT,
            filter=Q(pickup__status="Picked-up"),
            output_field=MONEY,
        ),
    )
    return {
        **counts,
        f"{period}_received_amount": amounts["received"] or Decimal(0),
        f"{period}_total_amount": amounts["total"] or Decimal(0),
    }


def top_items_by_value(limit=5):
    rows = (
        PickupItems.objects.filter(pickup__status="Picked-up")
        .values("item_id", "item__name")
        .annotate(total=Sum(REALISED_AMOUNT, output_field=MONEY))
        .order_by("-total", "item__name")[:limit]
    )
    return [{"name": row["item__name"], "total": row["total"]} for row in rows]


class DashboardView(RestrictUserMixin, TemplateView):
    template_name = "site_admin/dashboard.html"
    login_url = reverse_lazy("site_admin:login")
    role_name = "Admin"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = timezone.localdate()

        for period in PERIOD_DAYS:
            context[period] = _period_stats(period, today)

        context["latest_requests"] = Pickup.objects.select_related("customer")[:6]

        demand_items = Item.objects.annotate(instances=Count("pickupitems")).order_by("-instances")[:5]
        context["demand_items"] = [{"name": item.name, "count": item.instances} for item in demand_items]

        top_items = top_items_by_value()
        context["series"] = [float(row["total"]) for row in top_items]
        context["labels"] = _js_safe_json([row["name"] for row in top_items])
        return context


class NotificationView(RestrictUserMixin, View):
    role_name = "Admin"
    login_url = reverse_lazy("site_admin:login")

    def get(self, request):
        recipients = (
            Recipients.objects.filter(recipient=request.user)
            .select_related("notification")
            .order_by("-notification__created", "pk")
        )
        result = paginate(
            request,
            recipients,
            search_fields=("notification__subject", "notification__content"),
        )
        notifications = list(result.page.object_list)
        unread = [row.pk for row in notifications if not row.read]
        if unread:
            Recipients.objects.filter(pk__in=unread).update(read=True)
        context = {"notif_list": notifications, **list_context(result)}
        return render(request, "site_admin/notifications.html", context)
