import re

from django.contrib.auth.base_user import BaseUserManager

PHONE_PATTERN = re.compile(r"[0-9]{10}")


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, password, **extra_fields):
        email = extra_fields.get("email")
        if email:
            extra_fields["email"] = self.normalize_email(email)
        user = self.model(**extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, password=None, **extra_fields):
        email = extra_fields.get("email")
        phone = extra_fields.get("phone")

        if not email and not phone:
            raise ValueError("Either email or phone is required")
        if not password:
            raise ValueError("Password is required")
        if phone and not PHONE_PATTERN.fullmatch(str(phone)):
            raise ValueError("Phone number needs to be a 10 digit number")

        extra_fields.update(is_superuser=False, is_staff=False, is_active=True)
        return self._create_user(password, **extra_fields)

    def create_superuser(self, password, **extra_fields):
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_active", True)
        extra_fields.setdefault("role", "SuperUser")

        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")
        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")

        return self._create_user(password, **extra_fields)
