from django.contrib import admin
from .models import Training, TrainingEnrollment

@admin.register(Training)
class TrainingAdmin(admin.ModelAdmin):
    list_display = ['title', 'training_type', 'start_date', 'end_date', 'unit', 'instructor', 'status', 'get_enrollment_count']
    list_filter = ['training_type', 'status', 'start_date', 'unit']
    search_fields = ['title', 'description']
    date_hierarchy = 'start_date'

@admin.register(TrainingEnrollment)
class TrainingEnrollmentAdmin(admin.ModelAdmin):
    list_display = ['cadet', 'training', 'enrollment_date', 'completion_status', 'overall_score', 'grade']
    list_filter = ['completion_status', 'enrollment_date', 'training__training_type']
    search_fields = ['cadet__user__first_name', 'cadet__user__last_name', 'training__title']
