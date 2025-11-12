from django.contrib import admin
from .models import Event, EventRegistration

@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ['title', 'event_type', 'start_date', 'status', 'unit', 'is_mandatory']
    list_filter = ['event_type', 'status', 'is_mandatory', 'start_date']
    search_fields = ['title', 'description', 'location']
    date_hierarchy = 'start_date'
    prepopulated_fields = {'slug': ('title',)}
    raw_id_fields = ['unit', 'organizer']

@admin.register(EventRegistration)
class EventRegistrationAdmin(admin.ModelAdmin):
    list_display = ['cadet', 'event', 'status', 'registration_date', 'approved_by']
    list_filter = ['status', 'registration_date']
    search_fields = ['cadet__user__first_name', 'cadet__user__last_name', 
                    'event__title']
    date_hierarchy = 'registration_date'
    raw_id_fields = ['event', 'cadet', 'approved_by']