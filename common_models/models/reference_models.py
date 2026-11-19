from django.db import models, transaction


class ReferenceCounter(models.Model):
    prefix = models.CharField(max_length=10, primary_key=True)
    last_value = models.PositiveBigIntegerField(default=0)

    def __str__(self):
        return f"{self.prefix}_{self.last_value}"


def next_reference(prefix):
    with transaction.atomic():
        ReferenceCounter.objects.get_or_create(prefix=prefix)
        counter = ReferenceCounter.objects.select_for_update().get(prefix=prefix)
        counter.last_value += 1
        counter.save(update_fields=["last_value"])
    return f"{prefix}_{counter.last_value}"


class ReferenceModel(models.Model):
    reference_prefix = ""
    reference = models.CharField(max_length=20, unique=True, editable=False, blank=True)

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        if not self.reference:
            if not self.reference_prefix:
                raise ValueError(f"{type(self).__name__} must define reference_prefix.")
            self.reference = next_reference(self.reference_prefix)
            update_fields = kwargs.get("update_fields")
            if update_fields is not None:
                kwargs["update_fields"] = {*update_fields, "reference"}
        super().save(*args, **kwargs)
