from django.contrib.auth.password_validation import validate_password as run_password_validators
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError, transaction
from rest_framework import serializers

from accounts.models import Person
from accounts.services import consume_verified_otp
from accounts.utils import ProfileValidationError, ensure_email_available
from common_models.models import City, Item, Pickup, State
from notifications.models import Notifications, Recipients

PHONE_PATTERN = r"^\d{10}$"


class EmailValidationMixin:
    def validate_email(self, value):
        email = (value or "").strip()
        if not email:
            return None
        try:
            ensure_email_available(email, self.instance)
        except ProfileValidationError as exc:
            raise serializers.ValidationError(str(exc))
        return email


class UpdateSettingSerializer(EmailValidationMixin, serializers.ModelSerializer):
    class Meta:
        model = Person
        fields = ("image", "first_name", "last_name", "email", "phone", "address", "state", "city", "pin_code")
        read_only_fields = ("phone",)
        extra_kwargs = {"email": {"validators": []}}


class DashboardItemsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Item
        fields = "__all__"


class StatesSerializer(serializers.ModelSerializer):
    class Meta:
        model = State
        fields = "__all__"


class CitiesSerializer(serializers.ModelSerializer):
    class Meta:
        model = City
        fields = "__all__"


class HistoryListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Pickup
        fields = ("pickup_id", "reference", "pickup_date", "status")


class ViewOrderListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Pickup
        fields = (
            "pickup_id",
            "reference",
            "created",
            "pickup_date",
            "time_slot",
            "address",
            "city",
            "state",
            "pin_code",
            "status",
            "pickup_boy",
            "payment",
        )


class SendOtpSerializer(serializers.Serializer):
    phone = serializers.RegexField(PHONE_PATTERN, max_length=10)

    def validate_phone(self, value):
        if Person.objects.filter(phone=value).exists():
            raise serializers.ValidationError("phone already exist")
        return value


class ResendOtpSerializer(serializers.Serializer):
    phone = serializers.RegexField(PHONE_PATTERN, max_length=10)


class VerifyOtpSerializer(serializers.Serializer):
    phone = serializers.RegexField(PHONE_PATTERN, max_length=10, required=False)
    otp = serializers.CharField(max_length=6)


class SetPasswordSerializer(serializers.Serializer):
    phone = serializers.RegexField(PHONE_PATTERN, max_length=10)
    password = serializers.CharField(write_only=True, min_length=8, max_length=200)

    def validate_password(self, value):
        try:
            run_password_validators(value)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(list(exc.messages))
        return value

    def create(self, validated_data):
        phone = validated_data["phone"]
        try:
            with transaction.atomic():
                if not consume_verified_otp(phone):
                    raise serializers.ValidationError({"phone": "Phone number is not verified."})
                return Person.objects.create_user(
                    phone=phone, role="Customer", password=validated_data["password"]
                )
        except IntegrityError:
            raise serializers.ValidationError({"phone": "This number already exists"})
        except ValueError as exc:
            raise serializers.ValidationError({"phone": str(exc)})


class RegisterSerializer(EmailValidationMixin, serializers.ModelSerializer):
    class Meta:
        model = Person
        fields = ("first_name", "last_name", "email", "address", "state", "city", "pin_code")
        extra_kwargs = {"email": {"validators": []}}


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notifications
        fields = ("subject", "content", "url")


class RecipientNotificationSerializer(serializers.ModelSerializer):
    notification = NotificationSerializer(many=False, read_only=True)

    class Meta:
        model = Recipients
        exclude = ("id",)
