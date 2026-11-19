import json
import os
import uuid

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from .generic_models import Location, TimeStampedModel, UUIDModel
from .reference_models import ReferenceModel


def pickup_image_path(instance, filename):
    extension = os.path.splitext(filename)[1].lower()
    return f"pickup_request/{uuid.uuid4().hex}{extension}"


class Item(ReferenceModel, UUIDModel, TimeStampedModel):
    reference_prefix = "PROD"

    UNIT = (
        ("Kg", "Kg"),
        ("Unit", "Unit"),
    )

    name = models.CharField(_("name"), max_length=50)
    unit = models.CharField(_("unit"), max_length=6, choices=UNIT, blank=True, null=True)
    description = models.TextField(_("description"))
    price = models.DecimalField(_("price"), max_digits=10, decimal_places=2)
    image = models.ImageField(_("image"), upload_to="items", default="default.jpg")

    class Meta:
        ordering = ("created",)

    def __str__(self):
        return self.name


class Pickup(ReferenceModel, Location, TimeStampedModel):
    reference_prefix = "PKRQ"

    STATUS = (
        ("Requested", "Requested"),
        ("Approved", "Approved"),
        ("Picked-up", "Picked-up and Paid"),
        ("Cancelled", "Cancelled"),
        ("Rescheduled", "Rescheduled"),
    )

    TIME_SLOTS = (
        ("9-10", "9 am-10 am"),
        ("10-11", "10 am-11 am"),
        ("11-12", "11 am-12  noon"),
        ("12-1", "12 noon-1 pm"),
        ("1-2", "1 pm-2 pm"),
        ("2-3", "2 pm-3 pm"),
        ("3-4", "3 pm-4 pm"),
        ("4-5", "4 pm-5 pm"),
        ("5-6", "5 pm-6 pm"),
    )

    pickup_id = models.UUIDField(
        _("unique_id"), default=uuid.uuid4, primary_key=True, unique=True, editable=False
    )
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("customer"),
        related_name="pickup",
        on_delete=models.CASCADE,
    )
    status = models.CharField(_("status"), choices=STATUS, max_length=11)
    pickup_boy = models.ForeignKey(
        "PickupBoy",
        verbose_name=_("Assigned Pickup boy"),
        related_name="pickup_boy",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
    )
    items = models.ManyToManyField(Item, verbose_name=_("items"), through="PickupItems")
    pickup_date = models.DateField(_("pickup_date"), auto_now=False, auto_now_add=False)
    time_slot = models.CharField(
        _("pickup time slot"), choices=TIME_SLOTS, blank=True, null=True, max_length=5
    )
    notes = models.TextField(_("Customer notes"), null=True, blank=True)
    additional_data = models.JSONField(
        _("additional data"),
        encoder=json.JSONEncoder,
        decoder=json.JSONDecoder,
        default=dict,
        blank=True,
        null=True,
    )
    payment = models.DecimalField(
        _("Paid Amount"), max_digits=8, decimal_places=2, blank=True, null=True
    )
    image = models.ImageField(
        _("Image for pickup items"), upload_to=pickup_image_path, null=True, blank=True
    )

    class Meta:
        ordering = ("-created",)

    def __str__(self):
        return self.reference or str(self.pickup_id)


class PickupItems(UUIDModel, TimeStampedModel):
    pickup = models.ForeignKey(Pickup, verbose_name=_("Order"), on_delete=models.CASCADE)
    item = models.ForeignKey(Item, verbose_name=_("Item"), on_delete=models.PROTECT)
    quantity = models.DecimalField(_("Quantity"), decimal_places=3, max_digits=6, null=True)
    actual_quantity = models.DecimalField(
        _("Actual Quantity"),
        decimal_places=2,
        max_digits=6,
        null=True,
        blank=True,
        help_text="Quantity when request is picked up",
    )
    final_price = models.DecimalField(
        _("Final Price"),
        decimal_places=2,
        max_digits=6,
        null=True,
        blank=True,
        help_text="Price when request is picked up",
    )

    class Meta:
        ordering = ("created",)
        constraints = [
            models.UniqueConstraint(fields=("pickup", "item"), name="unique_item_per_pickup")
        ]

    def __str__(self):
        return f"{self.pickup} - {self.item}"


class Cancellation(TimeStampedModel):
    pickup = models.OneToOneField(
        Pickup,
        verbose_name=_("Order"),
        related_name="cancellation",
        primary_key=True,
        on_delete=models.CASCADE,
    )
    reason = models.TextField(_("Reason"))

    def __str__(self):
        return self.pickup.reference or str(self.pickup.pickup_id)


class PickupBoy(ReferenceModel, UUIDModel, TimeStampedModel):
    reference_prefix = "SRPB"

    employed = models.BooleanField(_("Employment Status"), default=True)
    full_name = models.CharField(_("Full Name"), max_length=100)
    phone = models.CharField(_("Phone Number"), max_length=10, unique=True)

    class Meta:
        ordering = ("created",)

    def __str__(self):
        return f"{self.full_name} - {self.phone}"
