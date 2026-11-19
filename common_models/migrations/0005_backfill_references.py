from django.db import migrations, models
from django.db.models import F, Func, Value

REFERENCE_PREFIXES = (
    ("Item", "PROD"),
    ("PickupBoy", "SRPB"),
    ("Pickup", "PKRQ"),
)


def backfill_references(apps, schema_editor):
    Counter = apps.get_model("common_models", "ReferenceCounter")
    for model_name, prefix in REFERENCE_PREFIXES:
        Model = apps.get_model("common_models", model_name)
        keys = list(Model.objects.order_by("created", "pk").values_list("pk", flat=True))
        for number, key in enumerate(keys, start=1):
            Model.objects.filter(pk=key).update(reference=f"{prefix}_{number}")
        Counter.objects.update_or_create(prefix=prefix, defaults={"last_value": len(keys)})


def rewrite_notifications(apps, schema_editor):
    Pickup = apps.get_model("common_models", "Pickup")
    Notifications = apps.get_model("notifications", "Notifications")
    for key, reference in Pickup.objects.values_list("pk", "reference"):
        Notifications.objects.filter(content__contains=str(key)).update(
            content=Func(
                F("content"),
                Value(str(key)),
                Value(reference),
                function="REPLACE",
                output_field=models.TextField(),
            )
        )


class Migration(migrations.Migration):
    dependencies = [
        ("common_models", "0004_references"),
        ("notifications", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(backfill_references, migrations.RunPython.noop),
        migrations.RunPython(rewrite_notifications, migrations.RunPython.noop),
    ]
