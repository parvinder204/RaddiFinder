from django.urls import path

from .views import (
    AccountSettingsView,
    ConfirmRequest,
    CustomerDetailsPage,
    DashboardView,
    HistoryView,
    NotificationView,
    SelectView,
    ViewOrderView,
    account_deactivation,
    check_otp,
    create_otp,
    customer_forgot_password,
    customer_phone_number,
    forgot_new_password,
    invoice_gen,
    popup_login,
)

app_name = "customer"

urlpatterns = [
    path("", DashboardView.as_view(), name="dashboard"),
    path("select-items", SelectView.as_view(), name="select-items"),
    path("forgot-password", customer_forgot_password, name="forgot-password"),
    path("forgot-new", forgot_new_password, name="forgot-new"),
    path("popup-login", popup_login, name="popup-login"),
    path("phone-number", customer_phone_number, name="phone-number"),
    path("account-deactivation", account_deactivation, name="account_deactivation"),
    path("create-otp", create_otp, name="create-otp"),
    path("check-otp", check_otp, name="check-otp"),
    path("details", CustomerDetailsPage.as_view(), name="details"),
    path("confirm-request", ConfirmRequest.as_view(), name="confirm-request"),
    path("get-invoice/<slug:uuid>", invoice_gen, name="get-invoice"),
    path("account-settings", AccountSettingsView.as_view(), name="account-settings"),
    path("notifications", NotificationView.as_view(), name="notifications"),
    path("history", HistoryView.as_view(), name="history"),
    path("view-order/<slug:pk>", ViewOrderView.as_view(), name="view-order"),
]
