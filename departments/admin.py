from django.contrib import admin
from .models import Department

@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'display_order', 'is_mandatory', 'is_active', 'location', 'active_staff_count', 'pending_verifications_count')
    list_editable = ('display_order', 'is_mandatory', 'is_active')
    search_fields = ('name', 'code', 'description')
    list_filter = ('is_mandatory', 'is_active')
