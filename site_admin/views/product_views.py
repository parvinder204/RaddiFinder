from django.contrib import messages
from django.contrib.messages.views import SuccessMessageMixin
from django.db.models import ProtectedError
from django.urls import reverse_lazy
from django.views.generic import CreateView, ListView

from accounts.restriction import RestrictUserMixin
from common_models.models import Item
from common_models.utils import to_uuid
from site_admin.forms import ItemForm
from site_admin.pagination import PaginatedSearchMixin, redirect_to_list


class ManageProductsView(PaginatedSearchMixin, RestrictUserMixin, ListView):
    model = Item
    template_name = "site_admin/manage-products.html"
    login_url = reverse_lazy("site_admin:login")
    role_name = "Admin"
    search_fields = ("name", "unit", "description", "price")

    def get_queryset(self):
        return Item.objects.order_by("created", "pk")

    def post(self, request):
        if "update_submit" in request.POST:
            self._update(request)
        elif "delete_submit" in request.POST:
            self._delete(request)
        return redirect_to_list(request, "site_admin:manage-products")

    def _update(self, request):
        item_id = to_uuid(request.POST.get("id"))
        item = Item.objects.filter(pk=item_id).first() if item_id is not None else None
        if item is None:
            messages.error(request, "Product not found")
            return

        form = ItemForm(request.POST, request.FILES, instance=item)
        if form.is_valid():
            form.save()
            messages.success(request, "Products updated successfully")
            return

        for errors in form.errors.values():
            for error in errors:
                messages.error(request, error)

    def _delete(self, request):
        item_id = to_uuid(request.POST.get("delete_id"))
        deleted = 0
        if item_id is not None:
            try:
                deleted, _ = Item.objects.filter(pk=item_id).delete()
            except ProtectedError:
                messages.error(request, "Product is used in existing requests and cannot be deleted")
                return
        if deleted:
            messages.success(request, "Products deleted successfully")
        else:
            messages.error(request, "Product not found")


class AddProductView(RestrictUserMixin, SuccessMessageMixin, CreateView):
    model = Item
    form_class = ItemForm
    template_name = "site_admin/add-product.html"
    login_url = reverse_lazy("site_admin:login")
    role_name = "Admin"
    success_message = "Products successfully added"
    success_url = reverse_lazy("site_admin:manage-products")
