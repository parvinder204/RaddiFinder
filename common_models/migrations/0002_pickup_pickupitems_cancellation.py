import json
import uuid

import common_models.models.main_models
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("common_models", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Pickup",
            fields=[
                ("created", models.DateTimeField(auto_now_add=True)),
                ("modified", models.DateTimeField(auto_now=True)),
                (
                    "address",
                    models.TextField(blank=True, null=True, verbose_name="Address"),
                ),
                (
                    "pin_code",
                    models.CharField(
                        blank=True, max_length=6, null=True, verbose_name="Zip Code"
                    ),
                ),
                (
                    "pickup_id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                        unique=True,
                        verbose_name="unique_id",
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("Requested", "Requested"),
                            ("Approved", "Approved"),
                            ("Picked-up", "Picked-up and Paid"),
                            ("Cancelled", "Cancelled"),
                            ("Rescheduled", "Rescheduled"),
                        ],
                        max_length=11,
                        verbose_name="status",
                    ),
                ),
                ("pickup_date", models.DateField(verbose_name="pickup_date")),
                (
                    "time_slot",
                    models.CharField(
                        blank=True,
                        choices=[
                            ("9-10", "9 am-10 am"),
                            ("10-11", "10 am-11 am"),
                            ("11-12", "11 am-12  noon"),
                            ("12-1", "12 noon-1 pm"),
                            ("1-2", "1 pm-2 pm"),
                            ("2-3", "2 pm-3 pm"),
                            ("3-4", "3 pm-4 pm"),
                            ("4-5", "4 pm-5 pm"),
                            ("5-6", "5 pm-6 pm"),
                        ],
                        max_length=5,
                        null=True,
                        verbose_name="pickup time slot",
                    ),
                ),
                (
                    "notes",
                    models.TextField(blank=True, null=True, verbose_name="Customer notes"),
                ),
                (
                    "additional_data",
                    models.JSONField(
                        blank=True,
                        decoder=json.JSONDecoder,
                        default=dict,
                        encoder=json.JSONEncoder,
                        null=True,
                        verbose_name="additional data",
                    ),
                ),
                (
                    "payment",
                    models.DecimalField(
                        blank=True,
                        decimal_places=2,
                        max_digits=8,
                        null=True,
                        verbose_name="Paid Amount",
                    ),
                ),
                (
                    "image",
                    models.ImageField(
                        blank=True,
                        null=True,
                        upload_to=common_models.models.main_models.pickup_image_path,
                        verbose_name="Image for pickup items",
                    ),
                ),
                (
                    "city",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to="common_models.city",
                        verbose_name="City",
                    ),
                ),
                (
                    "customer",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="pickup",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="customer",
                    ),
                ),
                (
                    "pickup_boy",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="pickup_boy",
                        to="common_models.pickupboy",
                        verbose_name="Assigned Pickup boy",
                    ),
                ),
                (
                    "state",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to="common_models.state",
                        verbose_name="State",
                    ),
                ),
            ],
            options={
                "ordering": ("-created",),
            },
        ),
        migrations.CreateModel(
            name="PickupItems",
            fields=[
                ("created", models.DateTimeField(auto_now_add=True)),
                ("modified", models.DateTimeField(auto_now=True)),
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4, editable=False, primary_key=True, serialize=False
                    ),
                ),
                (
                    "quantity",
                    models.DecimalField(
                        decimal_places=3, max_digits=6, null=True, verbose_name="Quantity"
                    ),
                ),
                (
                    "actual_quantity",
                    models.DecimalField(
                        blank=True,
                        decimal_places=2,
                        help_text="Quantity when request is picked up",
                        max_digits=6,
                        null=True,
                        verbose_name="Actual Quantity",
                    ),
                ),
                (
                    "final_price",
                    models.DecimalField(
                        blank=True,
                        decimal_places=2,
                        help_text="Price when request is picked up",
                        max_digits=6,
                        null=True,
                        verbose_name="Final Price",
                    ),
                ),
                (
                    "item",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        to="common_models.item",
                        verbose_name="Item",
                    ),
                ),
                (
                    "pickup",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="common_models.pickup",
                        verbose_name="Order",
                    ),
                ),
            ],
            options={
                "ordering": ("created",),
            },
        ),
        migrations.AddField(
            model_name="pickup",
            name="items",
            field=models.ManyToManyField(
                through="common_models.PickupItems",
                to="common_models.item",
                verbose_name="items",
            ),
        ),
        migrations.AddConstraint(
            model_name="pickupitems",
            constraint=models.UniqueConstraint(
                fields=("pickup", "item"), name="unique_item_per_pickup"
            ),
        ),
        migrations.CreateModel(
            name="Cancellation",
            fields=[
                ("created", models.DateTimeField(auto_now_add=True)),
                ("modified", models.DateTimeField(auto_now=True)),
                (
                    "pickup",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        primary_key=True,
                        related_name="cancellation",
                        serialize=False,
                        to="common_models.pickup",
                        verbose_name="Order",
                    ),
                ),
                ("reason", models.TextField(verbose_name="Reason")),
            ],
            options={
                "abstract": False,
            },
        ),
    ]
