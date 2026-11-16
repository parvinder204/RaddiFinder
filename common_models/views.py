import mimetypes

from django.http import FileResponse, Http404, JsonResponse
from django.views.decorators.http import require_GET, require_POST

from accounts.roles import ADMIN_ROLES

from .models import City, Pickup
from .utils import to_uuid


@require_POST
def fetch_cities(request):
    state_id = to_uuid(request.POST.get("state_id"))
    if state_id is None:
        return JsonResponse([], safe=False, status=400)
    cities = list(City.objects.filter(state_id=state_id).values("id", "name", "available"))
    return JsonResponse(cities, safe=False)


@require_GET
def pickup_image(request, filename):
    if not request.user.is_authenticated:
        raise Http404

    pickup = Pickup.objects.filter(image=f"pickup_request/{filename}").first()
    if pickup is None:
        raise Http404
    if request.user.role not in ADMIN_ROLES and pickup.customer_id != request.user.pk:
        raise Http404

    try:
        file = pickup.image.open("rb")
    except (FileNotFoundError, ValueError):
        raise Http404

    content_type, _encoding = mimetypes.guess_type(filename)
    return FileResponse(file, content_type=content_type or "application/octet-stream")
