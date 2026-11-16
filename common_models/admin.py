from django.contrib import admin
from import_export.admin import ImportExportModelAdmin

from .models import Cancellation, City, Item, Pickup, PickupBoy, PickupItems, State


class StateAdmin(ImportExportModelAdmin):
    pass


class CityAdmin(ImportExportModelAdmin):
    pass


class ItemAdmin(ImportExportModelAdmin):
    pass


admin.site.register(State, StateAdmin)
admin.site.register(City, CityAdmin)
admin.site.register(Item, ItemAdmin)
admin.site.register(Pickup)
admin.site.register(PickupItems)
admin.site.register(Cancellation)
admin.site.register(PickupBoy)
