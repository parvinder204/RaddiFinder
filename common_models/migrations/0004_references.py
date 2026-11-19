from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("common_models", "0003_auditlog"),
    ]

    operations = [
        migrations.CreateModel(
            name="ReferenceCounter",
            fields=[
                ("prefix", models.CharField(max_length=10, primary_key=True, serialize=False)),
                ("last_value", models.PositiveBigIntegerField(default=0)),
            ],
        ),
        migrations.AddField(
            model_name="item",
            name="reference",
            field=models.CharField(blank=True, editable=False, max_length=20, null=True),
        ),
        migrations.AddField(
            model_name="pickup",
            name="reference",
            field=models.CharField(blank=True, editable=False, max_length=20, null=True),
        ),
        migrations.AddField(
            model_name="pickupboy",
            name="reference",
            field=models.CharField(blank=True, editable=False, max_length=20, null=True),
        ),
    ]
