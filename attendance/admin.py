from django.contrib import admin
from .models import AttendanceSession, Attendance

@admin.register(AttendanceSession)
class AttendanceSessionAdmin(admin.ModelAdmin):
    list_display = ['title', 'session_type', 'date', 'unit', 'is_mandatory', 'is_active']
    list_filter = ['session_type', 'unit', 'is_mandatory', 'is_active', 'date']
    search_fields = ['title', 'location']
    date_hierarchy = 'date'
    raw_id_fields = ['unit', 'created_by']

@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ['cadet', 'session', 'status', 'marked_by', 'marked_at']
    list_filter = ['status', 'session__date']
    search_fields = ['cadet__user__first_name', 'cadet__user__last_name', 
                    'cadet__enrollment_number']
    date_hierarchy = 'marked_at'
    raw_id_fields = ['session', 'cadet', 'marked_by']