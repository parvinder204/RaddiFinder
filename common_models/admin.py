from django.contrib import admin
from import_export.admin import ImportExportModelAdmin

from .models import AuditLog, Cancellation, City, Item, Pickup, PickupBoy, PickupItems, State


class StateAdmin(ImportExportModelAdmin):
    pass


class CityAdmin(ImportExportModelAdmin):
    pass


class ItemAdmin(ImportExportModelAdmin):
    readonly_fields = ("reference",)


class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("created", "actor", "action", "target_type", "target_id")
    list_filter = ("action", "target_type")
    search_fields = ("target_id", "actor__phone", "actor__email")
    readonly_fields = ("actor", "action", "target_type", "target_id", "snapshot", "created", "modified")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


admin.site.register(State, StateAdmin)
admin.site.register(City, CityAdmin)
admin.site.register(Item, ItemAdmin)
admin.site.register(Pickup)
admin.site.register(PickupItems)
admin.site.register(Cancellation)
admin.site.register(PickupBoy)
admin.site.register(AuditLog, AuditLogAdmin)
