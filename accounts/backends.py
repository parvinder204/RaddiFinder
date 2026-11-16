from django.contrib.auth.backends import ModelBackend
from django.db.models import Q

from .models import Person


class CustomPhoneEmailBackend(ModelBackend):
    def authenticate(self, request, password=None, **kwargs):
        identifier = kwargs.get("email") or kwargs.get("phone") or kwargs.get("username")
        if not identifier or not password:
            return None

        user = Person.objects.filter(Q(email=identifier) | Q(phone=identifier)).first()
        if user is None:
            Person().set_password(password)
            return None

        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
