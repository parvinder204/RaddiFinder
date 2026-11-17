import pytest

from accounts.models import Person
from accounts.utils import EMAIL_IN_USE_MESSAGE, ProfileValidationError, ensure_email_available


@pytest.mark.django_db
def test_blank_email_is_always_available():
    ensure_email_available("")
    ensure_email_available(None)


@pytest.mark.django_db
def test_duplicate_email_is_rejected_ignoring_case():
    Person.objects.create(phone="9876543210", email="Taken@Example.com")
    with pytest.raises(ProfileValidationError) as error:
        ensure_email_available("taken@example.com")
    assert str(error.value) == EMAIL_IN_USE_MESSAGE


@pytest.mark.django_db
def test_own_email_is_available_to_its_owner():
    owner = Person.objects.create(phone="9876543210", email="me@example.com")
    ensure_email_available("me@example.com", owner)


@pytest.mark.django_db
def test_free_email_is_available():
    Person.objects.create(phone="9876543210", email="a@example.com")
    ensure_email_available("b@example.com")
