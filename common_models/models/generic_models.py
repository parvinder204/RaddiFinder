import uuid

from django.db import models
from django.utils.translation import gettext_lazy as _


class UUIDModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    class Meta:
        abstract = True


class TimeStampedModel(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class State(UUIDModel):
    name = models.CharField(_("Name"), max_length=50)

    class Meta:
        ordering = ("name",)

    def __str__(self):
        return self.name


class City(UUIDModel):
    state = models.ForeignKey(State, verbose_name=_("State"), on_delete=models.CASCADE)
    name = models.CharField(_("City name"), max_length=50)
    available = models.BooleanField(default=False)

    class Meta:
        ordering = ("name",)

    def __str__(self):
        return f"{self.name}, {self.state}, available - {self.available}"


class Location(models.Model):
    address = models.TextField(_("Address"), blank=True, null=True)
    city = models.ForeignKey(
        City, verbose_name=_("City"), on_delete=models.SET_NULL, blank=True, null=True
    )
    state = models.ForeignKey(
        State, verbose_name=_("State"), on_delete=models.SET_NULL, blank=True, null=True
    )
    pin_code = models.CharField(_("Zip Code"), max_length=6, blank=True, null=True)

    class Meta:
        abstract = True
