from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("common_models", "0005_backfill_references"),
    ]

    operations = [
        migrations.AlterField(
            model_name="item",
            name="reference",
            field=models.CharField(blank=True, editable=False, max_length=20, unique=True),
        ),
        migrations.AlterField(
            model_name="pickup",
            name="reference",
            field=models.CharField(blank=True, editable=False, max_length=20, unique=True),
        ),
        migrations.AlterField(
            model_name="pickupboy",
            name="reference",
            field=models.CharField(blank=True, editable=False, max_length=20, unique=True),
        ),
    ]
