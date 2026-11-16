import uuid
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="State",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4, editable=False, primary_key=True, serialize=False
                    ),
                ),
                ("name", models.CharField(max_length=50, verbose_name="Name")),
            ],
            options={
                "ordering": ("name",),
            },
        ),
        migrations.CreateModel(
            name="City",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4, editable=False, primary_key=True, serialize=False
                    ),
                ),
                ("name", models.CharField(max_length=50, verbose_name="City name")),
                ("available", models.BooleanField(default=False)),
                (
                    "state",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="common_models.state",
                        verbose_name="State",
                    ),
                ),
            ],
            options={
                "ordering": ("name",),
            },
        ),
        migrations.CreateModel(
            name="Item",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4, editable=False, primary_key=True, serialize=False
                    ),
                ),
                ("created", models.DateTimeField(auto_now_add=True)),
                ("modified", models.DateTimeField(auto_now=True)),
                ("name", models.CharField(max_length=50, verbose_name="name")),
                (
                    "unit",
                    models.CharField(
                        blank=True,
                        choices=[("Kg", "Kg"), ("Unit", "Unit")],
                        max_length=6,
                        null=True,
                        verbose_name="unit",
                    ),
                ),
                ("description", models.TextField(verbose_name="description")),
                (
                    "price",
                    models.DecimalField(decimal_places=2, max_digits=10, verbose_name="price"),
                ),
                (
                    "image",
                    models.ImageField(
                        default="default.jpg", upload_to="items", verbose_name="image"
                    ),
                ),
            ],
            options={
                "ordering": ("created",),
            },
        ),
        migrations.CreateModel(
            name="PickupBoy",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4, editable=False, primary_key=True, serialize=False
                    ),
                ),
                ("created", models.DateTimeField(auto_now_add=True)),
                ("modified", models.DateTimeField(auto_now=True)),
                (
                    "employed",
                    models.BooleanField(default=True, verbose_name="Employment Status"),
                ),
                ("full_name", models.CharField(max_length=100, verbose_name="Full Name")),
                (
                    "phone",
                    models.CharField(max_length=10, unique=True, verbose_name="Phone Number"),
                ),
            ],
            options={
                "ordering": ("created",),
            },
        ),
    ]
