from django.contrib import admin
from .models import Achievement

@admin.register(Achievement)
class AchievementAdmin(admin.ModelAdmin):
    list_display = ['title', 'cadet', 'achievement_type', 'level', 'date_awarded', 'verified', 'verified_by']
    list_filter = ['achievement_type', 'level', 'verified', 'date_awarded']
    search_fields = ['title', 'cadet__user__first_name', 'cadet__user__last_name', 'description']
    date_hierarchy = 'date_awarded'
    readonly_fields = ['verified_by', 'verification_date']