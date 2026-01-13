from django.contrib import admin
from .models import DeviceLedger

@admin.register(DeviceLedger)
class DeviceLedgerAdmin(admin.ModelAdmin):
    list_display = ('device', 'device_name', 'user', 'operation_type', 'operation_date', 'expected_return_date', 'actual_return_date', 'status_after_operation', 'operator')
    list_filter = ('operation_type', 'operation_date', 'status_after_operation', 'operator')
    search_fields = ('device__device_code', 'device_name', 'user__name', 'description')
    readonly_fields = ('created_at',)

    fieldsets = (
        ('基本信息', {
            'fields': ('device', 'device_name', 'user', 'operation_type', 'operation_date')
        }),
        ('借出归还信息', {
            'fields': ('expected_return_date', 'actual_return_date'),
            'classes': ('collapse',)
        }),
        ('状态信息', {
            'fields': ('status_after_operation', 'description', 'operator')
        }),
        ('系统信息', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )