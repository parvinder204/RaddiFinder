from django.test import RequestFactory

from RaddiFinder.views import devtools_probe


def test_devtools_probe_answers_without_content():
    response = devtools_probe(RequestFactory().get("/.well-known/appspecific/com.chrome.devtools.json"))
    assert response.status_code == 204
    assert response.content == b""
