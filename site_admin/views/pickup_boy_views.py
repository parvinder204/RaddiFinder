from django.contrib import messages
from django.contrib.messages.views import SuccessMessageMixin
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import CreateView, ListView

from accounts.restriction import RestrictUserMixin
from common_models.models import PickupBoy
from common_models.utils import to_uuid
from site_admin.forms import PickupBoyForm
from common_models.pagination import PaginatedSearchMixin, redirect_to_list

PHONE_EXISTS_MESSAGE = "Phone Number already exists."


def _report_form_errors(request, form):
    if form.has_error("phone", code="unique"):
        messages.error(request, PHONE_EXISTS_MESSAGE)
        return
    for errors in form.errors.values():
        for error in errors:
            messages.error(request, error)


class ManagePickupBoyView(PaginatedSearchMixin, RestrictUserMixin, ListView):
    model = PickupBoy
    template_name = "site_admin/manage-pickup-boy.html"
    login_url = reverse_lazy("site_admin:login")
    role_name = "Admin"
    search_fields = ("full_name", "phone")

    def get_queryset(self):
        return PickupBoy.objects.filter(employed=True).order_by("created", "pk")

    def post(self, request):
        if "update_submit" in request.POST:
            self._update(request)
        elif "delete_submit" in request.POST:
            self._delete(request)
        return redirect_to_list(request, "site_admin:manage-pickup-boy")

    def _get_boy(self, raw_id):
        boy_id = to_uuid(raw_id)
        return PickupBoy.objects.filter(pk=boy_id).first() if boy_id is not None else None

    def _update(self, request):
        boy = self._get_boy(request.POST.get("id"))
        if boy is None:
            messages.error(request, "Pickup boy not found")
            return

        form = PickupBoyForm(
            {
                "full_name": request.POST.get("name", ""),
                "phone": request.POST.get("phone", ""),
                "employed": boy.employed,
            },
            instance=boy,
        )
        if form.is_valid():
            form.save()
            messages.success(request, "Pickup boy updated successfully")
        else:
            _report_form_errors(request, form)

    def _delete(self, request):
        boy = self._get_boy(request.POST.get("delete_id"))
        if boy is None:
            messages.error(request, "Pickup boy not found")
            return
        boy.employed = False
        boy.save()
        messages.success(request, "Pickup boy deleted successfully")


class AddPickupView(RestrictUserMixin, SuccessMessageMixin, CreateView):
    model = PickupBoy
    form_class = PickupBoyForm
    template_name = "site_admin/add-pickupboy.html"
    login_url = reverse_lazy("site_admin:login")
    role_name = "Admin"
    success_message = "Pickup boy successfully added"
    success_url = reverse_lazy("site_admin:manage-pickup-boy")

    def form_invalid(self, form):
        _report_form_errors(self.request, form)
        return redirect("site_admin:add-pickup")
