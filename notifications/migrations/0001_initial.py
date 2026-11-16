import uuid
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Notifications",
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
                    "sent_to",
                    models.CharField(
                        choices=[("Customer", "Customer"), ("Admin", "Admin")],
                        max_length=50,
                        verbose_name="Sent to",
                    ),
                ),
                ("subject", models.CharField(max_length=50, verbose_name="Subject")),
                ("content", models.TextField(verbose_name="Content")),
                ("url", models.CharField(max_length=200, verbose_name="Url")),
            ],
            options={
                "ordering": ("-created",),
            },
        ),
        migrations.CreateModel(
            name="Recipients",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4, editable=False, primary_key=True, serialize=False
                    ),
                ),
                ("read", models.BooleanField(default=False, verbose_name="Read Status")),
                (
                    "notification",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="notifications.notifications",
                        verbose_name="Notification",
                    ),
                ),
                (
                    "recipient",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Recipient",
                    ),
                ),
            ],
        ),
        migrations.AddField(
            model_name="notifications",
            name="recipient_list",
            field=models.ManyToManyField(
                through="notifications.Recipients",
                to=settings.AUTH_USER_MODEL,
                verbose_name="Recipients",
            ),
        ),
    ]
