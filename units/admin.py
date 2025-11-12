from django.contrib import admin
from .models import Unit

@admin.register(Unit)
class UnitAdmin(admin.ModelAdmin):
    list_display = ['name', 'wing', 'unit_code', 'location', 'is_active', 'established_date']
    list_filter = ['wing', 'is_active']
    search_fields = ['name', 'unit_code', 'location']
    date_hierarchy = 'created_at'