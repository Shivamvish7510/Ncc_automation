from django.contrib import admin
from .models import Notification, BulkNotification

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['title', 'recipient', 'notification_type', 'priority', 'is_read', 'created_at']
    list_filter = ['notification_type', 'priority', 'is_read', 'created_at']
    search_fields = ['title', 'message', 'recipient__username']
    date_hierarchy = 'created_at'

@admin.register(BulkNotification)
class BulkNotificationAdmin(admin.ModelAdmin):
    list_display = ['title', 'target_audience', 'recipients_count', 'sent_by', 'sent_at']
    list_filter = ['target_audience', 'notification_type', 'sent_at']
    search_fields = ['title', 'message']
    date_hierarchy = 'sent_at'