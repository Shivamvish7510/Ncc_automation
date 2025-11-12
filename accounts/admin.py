from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, Officer, Cadet

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ['username', 'email', 'role', 'is_active', 'is_staff']
    list_filter = ['role', 'is_active', 'is_staff', 'created_at']
    search_fields = ['username', 'email', 'first_name', 'last_name']
    
    fieldsets = BaseUserAdmin.fieldsets + (
        ('NCC Info', {
            'fields': ('role', 'phone_number', 'profile_picture', 
                      'date_of_birth', 'address', 'is_active_member')
        }),
    )

@admin.register(Officer)
class OfficerAdmin(admin.ModelAdmin):
    list_display = ['employee_id', 'user', 'rank', 'unit', 'joining_date']
    list_filter = ['rank', 'unit', 'joining_date']
    search_fields = ['employee_id', 'user__username', 'user__first_name', 'user__last_name']
    raw_id_fields = ['user', 'unit']

@admin.register(Cadet)
class CadetAdmin(admin.ModelAdmin):
    list_display = ['enrollment_number', 'user', 'rank', 'unit', 'college_name', 'year_of_study']
    list_filter = ['rank', 'unit', 'year_of_study', 'enrollment_date']
    search_fields = ['enrollment_number', 'user__username', 'user__first_name', 
                    'user__last_name', 'college_name']
    raw_id_fields = ['user', 'unit', 'assigned_officer']
    
    fieldsets = (
        ('User Information', {
            'fields': ('user', 'rank', 'unit', 'enrollment_number', 'enrollment_date')
        }),
        ('Academic Information', {
            'fields': ('college_name', 'course', 'year_of_study', 'roll_number')
        }),
        ('Parent/Guardian Information', {
            'fields': ('parent_name', 'parent_phone', 'parent_email', 'emergency_contact')
        }),
        ('NCC Details', {
            'fields': ('blood_group', 'height', 'weight', 'assigned_officer')
        }),
    )