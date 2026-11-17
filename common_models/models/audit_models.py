from django.conf import settings
from django.core.serializers.json import DjangoJSONEncoder
from django.db import models

from .generic_models import TimeStampedModel, UUIDModel


class AuditLog(UUIDModel, TimeStampedModel):
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="audit_logs",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    action = models.CharField(max_length=50)
    target_type = models.CharField(max_length=50)
    target_id = models.CharField(max_length=64)
    snapshot = models.JSONField(default=dict, blank=True, encoder=DjangoJSONEncoder)

    class Meta:
        ordering = ("-created",)
        indexes = [models.Index(fields=["target_type", "target_id"], name="auditlog_target_idx")]

    def __str__(self):
        return f"{self.action} {self.target_type} {self.target_id}"
