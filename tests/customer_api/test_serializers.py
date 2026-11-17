import pytest

from accounts.models import Person
from accounts.utils import EMAIL_IN_USE_MESSAGE
from customer_api.serializer import RegisterSerializer, UpdateSettingSerializer

SERIALIZERS = [RegisterSerializer, UpdateSettingSerializer]


@pytest.mark.django_db
@pytest.mark.parametrize("serializer_class", SERIALIZERS)
def test_blank_email_is_stored_as_null(customer, serializer_class):
    serializer = serializer_class(customer, data={"email": ""}, partial=True)
    assert serializer.is_valid(), serializer.errors
    assert serializer.validated_data["email"] is None


@pytest.mark.django_db
@pytest.mark.parametrize("serializer_class", SERIALIZERS)
def test_two_users_can_both_have_no_email(customer, other_customer, serializer_class):
    for user in (customer, other_customer):
        serializer = serializer_class(user, data={"email": ""}, partial=True)
        assert serializer.is_valid(), serializer.errors
        serializer.save()
    assert Person.objects.filter(email__isnull=True).count() == 2


@pytest.mark.django_db
@pytest.mark.parametrize("serializer_class", SERIALIZERS)
def test_duplicate_email_is_rejected_ignoring_case(customer, other_customer, serializer_class):
    other_customer.email = "Taken@Example.com"
    other_customer.save()
    serializer = serializer_class(customer, data={"email": "taken@example.com"}, partial=True)
    assert not serializer.is_valid()
    assert str(serializer.errors["email"][0]) == EMAIL_IN_USE_MESSAGE


@pytest.mark.django_db
@pytest.mark.parametrize("serializer_class", SERIALIZERS)
def test_user_can_keep_their_own_email(customer, serializer_class):
    customer.email = "me@example.com"
    customer.save()
    serializer = serializer_class(customer, data={"email": "me@example.com"}, partial=True)
    assert serializer.is_valid(), serializer.errors


@pytest.mark.django_db
@pytest.mark.parametrize("serializer_class", SERIALIZERS)
def test_email_is_stripped(customer, serializer_class):
    serializer = serializer_class(customer, data={"email": "new@example.com"}, partial=True)
    assert serializer.is_valid(), serializer.errors
    assert serializer.validated_data["email"] == "new@example.com"
