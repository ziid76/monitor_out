from django.contrib import admin
from .models import MonitorTarget, MonitoringLog

@admin.register(MonitorTarget)
class MonitorTargetAdmin(admin.ModelAdmin):
    list_display = ('name', 'url', 'check_interval', 'is_active', 'last_status', 'last_checked_at')
    list_filter = ('is_active', 'last_status')
    search_fields = ('name', 'url')
    filter_horizontal = ('recipients',)
    fieldsets = (
        ('기본 정보', {'fields': ('name', 'url', 'check_interval', 'is_active')}),
        ('시그니처 설정', {'fields': ('signature_title', 'signature_text', 'signature_dom')}),
        ('알림 설정', {'fields': ('recipients',)}),
        ('상태 정보', {'fields': ('last_status', 'last_checked_at'), 'classes': ('collapse',)}),
    )

@admin.register(MonitoringLog)
class MonitoringLogAdmin(admin.ModelAdmin):
    list_display = ('target', 'status', 'response_time', 'checked_at')
    list_filter = ('status', 'target')
    readonly_fields = ('target', 'status', 'response_time', 'error_message', 'checked_at')
