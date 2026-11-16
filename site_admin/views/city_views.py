from django.contrib import messages
from django.db import transaction
from django.shortcuts import redirect, render

from accounts.decorators import role_required
from common_models.models import City, State
from common_models.utils import to_uuid

NAME_MAX_LENGTH = 50


@role_required("Admin", login_url="site_admin:login")
def avail_city_view(request, del_pk=None):
    if del_pk is not None:
        if City.objects.filter(pk=del_pk).update(available=False):
            messages.success(request, "City removed as service-able area.")
    elif request.method == "POST":
        city_id = to_uuid(request.POST.get("city_id"))
        if city_id is not None and City.objects.filter(pk=city_id).update(available=True):
            messages.success(request, "City added as service-able area.")

    context = {
        "avail_city": City.objects.filter(available=True),
        "states": State.objects.all(),
    }
    return render(request, "site_admin/add-city-available.html", context)


@role_required("Admin", login_url="site_admin:login")
def add_new_city_view(request):
    if request.method != "POST":
        return redirect("site_admin:avail_city")

    state_name = request.POST.get("state_name", "").strip()
    city_name = request.POST.get("city_name", "").strip()

    if not state_name or not city_name:
        messages.error(request, "State and City name are required.")
        return redirect("site_admin:avail_city")
    if len(state_name) > NAME_MAX_LENGTH or len(city_name) > NAME_MAX_LENGTH:
        messages.error(request, f"Names cannot exceed {NAME_MAX_LENGTH} characters.")
        return redirect("site_admin:avail_city")

    with transaction.atomic():
        state, _state_created = State.objects.get_or_create(name=state_name)
        city, created = City.objects.get_or_create(name=city_name, state=state)
        city.available = True
        city.save()

    if created:
        messages.success(request, f"New city '{city_name.title()}' added and marked as serviceable.")
    else:
        messages.success(
            request, f"'{city_name.title()}' already existed and is now marked as serviceable."
        )
    return redirect("site_admin:avail_city")
