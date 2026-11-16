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

PENDING_STATUSES = ("Requested", "Approved")
PERIOD_DAYS = {"today": 0, "week": 7, "month": 30}
MONEY = DecimalField(max_digits=14, decimal_places=2)


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
    estimated = F("quantity") * F("item__price")
    actual = F("actual_quantity") * F("final_price")
    amounts = PickupItems.objects.filter(pickup__in=orders).aggregate(
        total=Sum(estimated, output_field=MONEY),
        received=Sum(
            Coalesce(actual, estimated, output_field=MONEY),
            filter=Q(pickup__status="Picked-up"),
            output_field=MONEY,
        ),
    )
    return {
        **counts,
        f"{period}_received_amount": amounts["received"] or Decimal(0),
        f"{period}_total_amount": amounts["total"] or Decimal(0),
    }


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

        top_items = (
            Item.objects.filter(pickupitems__pickup__status="Picked-up")
            .annotate(
                grand_price=Sum(F("price") * F("pickupitems__quantity"), output_field=MONEY)
            )
            .order_by("-grand_price")[:5]
        )
        context["series"] = [float(item.grand_price) for item in top_items]
        context["labels"] = _js_safe_json([item.name for item in top_items])
        return context


class NotificationView(RestrictUserMixin, View):
    role_name = "Admin"
    login_url = reverse_lazy("site_admin:login")
    limit = 100

    def get(self, request):
        recipients = Recipients.objects.filter(recipient=request.user)
        notifications = list(
            recipients.select_related("notification").order_by("-notification__created")[: self.limit]
        )
        recipients.filter(read=False).update(read=True)
        return render(request, "site_admin/notifications.html", {"notif_list": notifications})
