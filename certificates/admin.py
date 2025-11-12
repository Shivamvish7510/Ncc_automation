from django.contrib import admin
from .models import Certificate

@admin.register(Certificate)
class CertificateAdmin(admin.ModelAdmin):
    list_display = ['certificate_number', 'cadet', 'certificate_type', 'issued_date', 'issued_by', 'status', 'grade']
    list_filter = ['certificate_type', 'status', 'issued_date']
    search_fields = ['certificate_number', 'cadet__user__first_name', 'cadet__user__last_name', 'title']
    date_hierarchy = 'issued_date'
    readonly_fields = ['certificate_number']