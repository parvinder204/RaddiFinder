import base64
import uuid
from io import BytesIO

from django.core.files.base import ContentFile
from django.http import HttpResponse
from django.template.loader import get_template
from PIL import Image
from xhtml2pdf import pisa

IMAGE_EXTENSIONS = {
    "image/jpeg": "jpg",
    "image/jpg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
    "image/gif": "gif",
}


def to_uuid(value):
    if isinstance(value, uuid.UUID):
        return value
    try:
        return uuid.UUID(str(value))
    except (AttributeError, TypeError, ValueError):
        return None


def is_valid_image(uploaded):
    try:
        position = uploaded.tell()
    except (AttributeError, OSError):
        position = 0
    try:
        with Image.open(uploaded) as image:
            image.verify()
    except (OSError, ValueError, SyntaxError):
        return False
    finally:
        uploaded.seek(position)
    return True


def is_ajax(request):
    return request.META.get("HTTP_X_REQUESTED_WITH") == "XMLHttpRequest"


def render_to_pdf(template_src, context_dict=None):
    html = get_template(template_src).render(context_dict or {})
    result = BytesIO()
    pdf = pisa.pisaDocument(BytesIO(html.encode("utf-8")), result, encoding="utf-8")
    if pdf.err:
        return None
    return HttpResponse(result.getvalue(), content_type="application/pdf")


def decode_file(data_uri):
    if not data_uri:
        return None
    try:
        header, payload = data_uri.split(";base64,", 1)
        extension = IMAGE_EXTENSIONS[header.split(":", 1)[-1].lower()]
        content = base64.b64decode(payload, validate=True)
    except (ValueError, KeyError):
        return None
    return ContentFile(content, name=f"{uuid.uuid4().hex}.{extension}")
