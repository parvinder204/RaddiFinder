import pytest

from notifications import sms, utils
from notifications.models import Notifications


@pytest.fixture
def posted(monkeypatch):
    calls = []

    def fake_post(template_name, to, components):
        calls.append((template_name, to, components))
        return True

    monkeypatch.setattr(sms, "_post_template", fake_post)
    return calls


@pytest.fixture
def inline_background(monkeypatch):
    calls = []

    def run(function, *args):
        calls.append((function.__name__, args))

    monkeypatch.setattr(utils, "run_in_background", run)
    return calls


@pytest.mark.django_db
@pytest.mark.parametrize("kind", ["created", "cancelled", "rescheduled", "approved", "picked-up"])
def test_customer_notifications_use_the_reference(customer, pickup, inline_background, kind):
    notification = utils.create_notification(user=customer, pickup=pickup, notif_type=kind)
    assert pickup.reference in notification.content
    assert str(pickup.pickup_id) not in notification.content


@pytest.mark.django_db
def test_notification_link_keeps_the_uuid(customer, pickup, inline_background):
    notification = utils.create_notification(user=customer, pickup=pickup, notif_type="cancelled")
    assert str(pickup.pickup_id) in notification.url


@pytest.mark.django_db
def test_admin_notification_uses_the_reference(customer, admin_user, pickup, inline_background):
    utils.create_notification(user=customer, pickup=pickup, notif_type="created")
    admin_note = Notifications.objects.get(sent_to="Admin")
    assert pickup.reference in admin_note.content
    assert str(pickup.pickup_id) not in admin_note.content
    assert str(pickup.pickup_id) in admin_note.url


@pytest.mark.django_db
def test_created_notification_passes_the_reference_to_whatsapp(customer, pickup, inline_background):
    utils.create_notification(user=customer, pickup=pickup, notif_type="created")
    names = {name: args for name, args in inline_background}
    assert names["send_request_received"] == (customer.phone, pickup.reference)


def test_received_message_ignores_the_reference_by_default(posted, settings):
    settings.MSG91_RECEIVED_USES_REFERENCE = False
    sms.send_request_received("9876543210", "PKRQ_7")
    assert posted[0][2] == {}


def test_received_message_adds_the_reference_when_enabled(posted, settings):
    settings.MSG91_RECEIVED_USES_REFERENCE = True
    sms.send_request_received("9876543210", "PKRQ_7")
    assert posted[0][2] == {"body_1": {"type": "text", "value": "PKRQ_7"}}


def test_pickup_details_ignore_the_reference_by_default(posted, settings):
    settings.MSG91_PICKUP_USES_REFERENCE = False
    sms.send_pickup_details("9876543210", "Ravi", "9000000001", "PKRQ_7")
    assert set(posted[0][2]) == {"body_1", "body_2"}


def test_pickup_details_add_the_reference_when_enabled(posted, settings):
    settings.MSG91_PICKUP_USES_REFERENCE = True
    sms.send_pickup_details("9876543210", "Ravi", "9000000001", "PKRQ_7")
    assert posted[0][2]["body_3"] == {"type": "text", "value": "PKRQ_7"}


def test_old_call_signatures_still_work(posted):
    sms.send_request_received("9876543210")
    sms.send_pickup_details("9876543210", "Ravi", "9000000001")
    assert len(posted) == 2
