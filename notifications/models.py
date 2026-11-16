from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from common_models.models import TimeStampedModel, UUIDModel


class Notifications(UUIDModel, TimeStampedModel):
    SENT_TO = (
        ("Customer", "Customer"),
        ("Admin", "Admin"),
    )

    sent_to = models.CharField(_("Sent to"), choices=SENT_TO, max_length=50)
    subject = models.CharField(_("Subject"), max_length=50)
    content = models.TextField(_("Content"))
    url = models.CharField(_("Url"), max_length=200)
    recipient_list = models.ManyToManyField(
        settings.AUTH_USER_MODEL, verbose_name=_("Recipients"), through="Recipients"
    )

    class Meta:
        ordering = ("-created",)

    def __str__(self):
        return self.subject or f"Notification {self.pk}"


class Recipients(UUIDModel):
    notification = models.ForeignKey(
        Notifications, verbose_name=_("Notification"), on_delete=models.CASCADE
    )
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name=_("Recipient"), on_delete=models.CASCADE
    )
    read = models.BooleanField(_("Read Status"), default=False)

    def __str__(self):
        return self.notification.subject
