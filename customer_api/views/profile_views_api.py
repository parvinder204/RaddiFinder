from django.db.models import F
from rest_framework.generics import RetrieveUpdateAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

from customer_api.serializer import RecipientNotificationSerializer, UpdateSettingSerializer
from notifications.models import Recipients


class UpdateAccountSetting(RetrieveUpdateAPIView):
    """
    Update the account details of a customer.
    """

    serializer_class = UpdateSettingSerializer

    def get_object(self):
        return self.request.user

    def update(self, request, *args, **kwargs):
        kwargs["partial"] = True
        return super().update(request, *args, **kwargs)


class RecipientNotificationApi(APIView):
    """
    Retreive notifications for customer.
    """

    def get(self, request, format=None):
        recipients = (
            Recipients.objects.filter(recipient=request.user)
            .select_related("notification")
            .annotate(subject=F("notification__subject"), content=F("notification__content"))
        )
        data = RecipientNotificationSerializer(recipients, many=True).data
        if data:
            return Response(data)
        return Response({"error": "Empty notifications"})
