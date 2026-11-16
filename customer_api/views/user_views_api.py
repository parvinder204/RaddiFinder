from django.conf import settings
from django.http import JsonResponse
from rest_framework import generics, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from accounts.services import OTPDeliveryError, OTPError, is_valid_phone, issue_otp, verify_otp
from accounts.throttling import OTPSendThrottle, OTPVerifyThrottle
from common_models.models import Item
from customer_api.serializer import (
    RegisterSerializer,
    ResendOtpSerializer,
    SendOtpSerializer,
    SetPasswordSerializer,
    VerifyOtpSerializer,
)


def get_tokens_for_user(user):
    refresh = RefreshToken.for_user(user)
    return {
        "refresh": str(refresh),
        "access": str(refresh.access_token),
    }


class PublicAPIView(APIView):
    authentication_classes = ()
    permission_classes = (AllowAny,)


class SendOtpApi(PublicAPIView):
    """
    Endpoint used for sending OTP to phone number
    """

    serializer_class = SendOtpSerializer
    throttle_classes = (OTPSendThrottle,)

    def post(self, request):
        serializer = SendOtpSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"status": "error", "data": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )
        phone = serializer.validated_data["phone"]
        try:
            issue_otp(phone)
        except OTPDeliveryError as exc:
            return Response(
                {"status": "error", "data": exc.message},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        request.session["phone"] = phone
        return Response({"status": "success", "data": {"phone": phone}}, status=status.HTTP_200_OK)


class ResendOtpApi(PublicAPIView):
    """
    Resend an OTP
    """

    serializer_class = ResendOtpSerializer
    throttle_classes = (OTPSendThrottle,)

    def get(self, request):
        serializer = ResendOtpSerializer(data=request.query_params)
        if not serializer.is_valid():
            return Response(
                {"status": "error", "data": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )
        phone = serializer.validated_data["phone"]
        try:
            issue_otp(phone)
        except OTPDeliveryError as exc:
            return Response(
                {"status": "error", "data": exc.message},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        return Response(f"New otp sent successfully to {phone}")


class VerifyOtpApi(PublicAPIView):
    """
    Verify if an OTP is correct
    """

    serializer_class = VerifyOtpSerializer
    throttle_classes = (OTPVerifyThrottle,)

    def post(self, request):
        serializer = VerifyOtpSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"status": "error", "data": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        phone = serializer.validated_data.get("phone") or request.session.get("phone", "")
        if not is_valid_phone(phone):
            return Response(
                {"status": "error", "data": "Phone number is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            verify_otp(phone, serializer.validated_data["otp"])
        except OTPError as exc:
            return Response(
                {"status": "error", "data": exc.message},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(
            {"status": "success", "data": {"otp": serializer.validated_data["otp"]}},
            status=status.HTTP_200_OK,
        )


class SetPasswordApi(PublicAPIView):
    """
    Set password for a customer
    """

    serializer_class = SetPasswordSerializer

    def post(self, request):
        serializer = SetPasswordSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        user = serializer.save()
        data = {"phone": user.phone, **get_tokens_for_user(user)}
        return Response({"status": "success", "data": data}, status=status.HTTP_200_OK)


class RegisterApi(generics.GenericAPIView):
    """
    Provide details of customer after registration
    """

    serializer_class = RegisterSerializer

    def put(self, request, format=None):
        serializer = self.get_serializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)


class Apigetpost(generics.GenericAPIView):
    authentication_classes = ()
    permission_classes = (AllowAny,)

    def get(self, request):
        placeholder = f"{settings.FDOMAIN}/static/images/item_placeholder.png"
        items = []
        for item in Item.objects.all():
            try:
                image = f"{settings.FDOMAIN}{item.image.url}"
            except ValueError:
                image = placeholder
            items.append(
                {
                    "id": item.id,
                    "name": item.name,
                    "price": item.price,
                    "unit": item.unit,
                    "image": image,
                }
            )
        return JsonResponse(items, status=200, safe=False)


class LogoutApi(PublicAPIView):
    """
    Blacklist a refresh token so it can no longer be used
    """

    def post(self, request):
        refresh = request.data.get("refresh")
        if not refresh:
            return Response(
                {"status": "error", "data": "refresh token is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            RefreshToken(refresh).blacklist()
        except TokenError:
            return Response(
                {"status": "error", "data": "Invalid or expired token"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response({"status": "success"}, status=status.HTTP_200_OK)