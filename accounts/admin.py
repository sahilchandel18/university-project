from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, StudentProfile, StaffProfile

@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'role', 'is_staff')
    list_filter = ('role', 'is_staff', 'is_superuser', 'is_active')
    fieldsets = UserAdmin.fieldsets + (
        ('Role & Verification Attributes', {'fields': ('role', 'phone_number', 'avatar')}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Role & Verification Attributes', {'fields': ('role', 'phone_number')}),
    )

@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    list_display = ('roll_number', 'user', 'registration_number', 'course', 'branch', 'semester', 'academic_session')
    search_fields = ('roll_number', 'registration_number', 'user__username', 'user__first_name', 'user__last_name')
    list_filter = ('course', 'branch', 'semester', 'academic_session', 'is_hostel_resident')

@admin.register(StaffProfile)
class StaffProfileAdmin(admin.ModelAdmin):
    list_display = ('employee_id', 'user', 'department', 'designation')
    search_fields = ('employee_id', 'user__username', 'user__first_name', 'department__name')
    list_filter = ('department', 'designation')
