from django.urls import path

from .views import (
    AddPickupView,
    AddProductView,
    DashboardView,
    ManagePickupBoyView,
    ManageProductsView,
    ManageRequestsView,
    NotificationView,
    Order_delete,
    RequestRespondView,
    add_new_city_view,
    avail_city_view,
    delete_pickup_item,
    site_admin_login,
    update_request_address,
)

app_name = "site_admin"

urlpatterns = [
    path("", site_admin_login, name="login"),
    path("dashboard", DashboardView.as_view(), name="dashboard"),
    path("manage-products", ManageProductsView.as_view(), name="manage-products"),
    path("add-product", AddProductView.as_view(), name="add-product"),
    path("manage-requests", ManageRequestsView.as_view(), name="manage-requests"),
    path("view-request/<str:pk>", RequestRespondView.as_view(), name="view-request"),
    path("update-request-address", update_request_address, name="update-request-address"),
    path("delete-pickup-item", delete_pickup_item, name="delete-pickup-item"),
    path("manage-pickup-boy", ManagePickupBoyView.as_view(), name="manage-pickup-boy"),
    path("add-pickup", AddPickupView.as_view(), name="add-pickup"),
    path("avail_city", avail_city_view, name="avail_city"),
    path("add_new_city", add_new_city_view, name="add_new_city"),
    path("avail_city/<uuid:del_pk>", avail_city_view, name="avail_city_del"),
    path("notifications", NotificationView.as_view(), name="notifications"),
    path("order_delete", Order_delete, name="order_delete"),
]
