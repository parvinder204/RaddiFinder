from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.core.validators import RegexValidator
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from common_models.models import Location, TimeStampedModel, UUIDModel

from .managers import UserManager


phone_validator = RegexValidator(r"^\d{10}$", "Phone number must be exactly 10 digits.")


class Person(UUIDModel, AbstractBaseUser, PermissionsMixin, TimeStampedModel, Location):
    ROLE = (
        ("Customer", "Customer"),
        ("Admin", "Admin"),
        ("Pickup", "Pickup"),
        ("SuperUser", "SuperUser"),
    )

    first_name = models.CharField(_("first Name"), max_length=50, blank=True, null=True)
    last_name = models.CharField(_("last Name"), max_length=50, blank=True, null=True)
    email = models.EmailField(
        _("email"),
        max_length=254,
        unique=True,
        blank=True,
        null=True,
        error_messages={"unique": _("A user with that email already exists.")},
    )
    phone = models.CharField(
        _("phone Number"),
        max_length=10,
        unique=True,
        blank=True,
        null=True,
        validators=[phone_validator],
        error_messages={"unique": _("A user with that phone number already exists.")},
    )
    role = models.CharField(_("role of user"), choices=ROLE, max_length=50, blank=True, null=True)
    image = models.ImageField(_("profile Picture"), upload_to="user_images", null=True, blank=True)

    is_active = models.BooleanField(
        _("active"),
        default=True,
        help_text="Is set to True only for superusers,staffs and users with verified email/phone",
    )
    is_staff = models.BooleanField(
        _("staff"),
        default=False,
        help_text="Designates whether the user can log into this admin site.",
    )

    USERNAME_FIELD = "phone"
    EMAIL_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = UserManager()

    class Meta:
        verbose_name = _("user")
        verbose_name_plural = _("users")

    def get_full_name(self):
        return f"{self.first_name or ''} {self.last_name or ''}".strip()

    def formatted_phone_number(self):
        if self.phone:
            return f"{self.phone[:3]}-{self.phone[3:6]}-{self.phone[6:]}"
        return "XXX-XXX-XXXX"

    def __str__(self):
        return self.phone or self.email or str(self.pk)


class OTP(UUIDModel, TimeStampedModel):
    otp = models.CharField(_("OTP"), max_length=6)
    phone = models.CharField(_("Phone Number"), max_length=10, unique=True)
    correct = models.BooleanField(_("Is otp correct"), default=False)
    attempts = models.PositiveSmallIntegerField(_("Failed attempts"), default=0)
    last_sent = models.DateTimeField(_("Last sent"), default=timezone.now)

    def __str__(self):
        return self.phone
