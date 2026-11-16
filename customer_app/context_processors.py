from django.db.models import DecimalField, F, Sum

from common_models.models import City, PickupItems
from notifications.models import Recipients

AMOUNT = DecimalField(max_digits=14, decimal_places=2)


def total_sales(request):
    if not request.user.is_authenticated:
        return {"amount__sum": None}
    return PickupItems.objects.filter(
        pickup__customer=request.user, pickup__status="Picked-up"
    ).aggregate(
        amount__sum=Sum(F("actual_quantity") * F("final_price"), output_field=AMOUNT)
    )


def notif_count(request):
    if not request.user.is_authenticated:
        return {"notif_count": None}
    return {"notif_count": Recipients.objects.filter(recipient=request.user, read=False).count()}


def notif_list(request):
    if not request.user.is_authenticated:
        return {"notif_list": None}
    unread = (
        Recipients.objects.filter(recipient=request.user, read=False)
        .select_related("notification")
        .order_by("-notification__created")
    )
    return {"notif_list": unread[:3]}


def avail_cities(request):
    names = City.objects.filter(available=True).values_list("name", flat=True)
    return {"avl_cities": ", ".join(names)}
