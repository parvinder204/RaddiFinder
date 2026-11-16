from django.urls import path

from customer_api.views import (
    Apigetpost,
    CityApi,
    ConfirmRequestApi,
    DashboardItemsApi,
    HistoryListApi,
    ItemAddApi,
    ItemDeleteApi,
    LogoutApi,
    RecipientNotificationApi,
    RegisterApi,
    ResendOtpApi,
    SendOtpApi,
    SetPasswordApi,
    StateApi,
    UpdateAccountSetting,
    UpdateAddressApi,
    VerifyOtpApi,
    ViewOrderListApi,
)

app_name = "customer_api"

urlpatterns = [
    path("api/update_setting", UpdateAccountSetting.as_view()),
    path("api/dashboard_items", DashboardItemsApi.as_view()),
    path("api/states", StateApi.as_view()),
    path("api/cities", CityApi.as_view()),
    path("api/history", HistoryListApi.as_view()),
    path("api/view-order/<view_id>", ViewOrderListApi.as_view()),
    path("api/logout", LogoutApi.as_view()),
    path("api/send-otp", SendOtpApi.as_view()),
    path("api/resend-otp", ResendOtpApi.as_view()),
    path("api/verify-otp", VerifyOtpApi.as_view()),
    path("api/password", SetPasswordApi.as_view()),
    path("api/register-details", RegisterApi.as_view()),
    path("api/confirm-request", ConfirmRequestApi.as_view()),
    path("api/recipient-notification", RecipientNotificationApi.as_view()),
    path("api/user-item-add", ItemAddApi.as_view()),
    path("api/user-item-delete/<uuid:pk>", ItemDeleteApi.as_view()),
    path("api/user-update-address/<requested_id>", UpdateAddressApi.as_view()),
    path("api/apigetpost", Apigetpost.as_view()),
]
