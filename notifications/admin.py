from django.contrib import admin

from .models import Notifications, Recipients

admin.site.register(Notifications)
admin.site.register(Recipients)
