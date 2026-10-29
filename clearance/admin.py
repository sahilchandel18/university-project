from django.contrib import admin
from .models import NoDuesApplication, DepartmentClearance, ClearanceLog, NoDuesCertificate, Notification

class DepartmentClearanceInline(admin.TabularInline):
    model = DepartmentClearance
    extra = 0
    fields = ('department', 'status', 'dues_amount', 'reviewed_by', 'reviewed_at', 'remarks')
    readonly_fields = ('reviewed_at',)

@admin.register(NoDuesApplication)
class NoDuesApplicationAdmin(admin.ModelAdmin):
    list_display = ('application_no', 'student', 'purpose', 'overall_status', 'total_dues_amount', 'submitted_at', 'completed_at')
    list_filter = ('overall_status', 'purpose', 'academic_session', 'submitted_at')
    search_fields = ('application_no', 'student__roll_number', 'student__user__first_name', 'student__user__last_name')
    inlines = [DepartmentClearanceInline]
    readonly_fields = ('application_no', 'submitted_at', 'completed_at')

@admin.register(DepartmentClearance)
class DepartmentClearanceAdmin(admin.ModelAdmin):
    list_display = ('application', 'department', 'status', 'dues_amount', 'reviewed_by', 'reviewed_at')
    list_filter = ('status', 'department', 'reviewed_at')
    search_fields = ('application__application_no', 'application__student__roll_number', 'remarks')

@admin.register(ClearanceLog)
class ClearanceLogAdmin(admin.ModelAdmin):
    list_display = ('application', 'department', 'actor', 'action', 'new_status', 'dues_amount', 'timestamp')
    list_filter = ('action', 'department', 'timestamp')
    search_fields = ('application__application_no', 'remarks', 'actor__username')

@admin.register(NoDuesCertificate)
class NoDuesCertificateAdmin(admin.ModelAdmin):
    list_display = ('certificate_no', 'student', 'application', 'issue_date', 'is_valid')
    search_fields = ('certificate_no', 'student__roll_number', 'verification_uuid')
    list_filter = ('is_valid', 'issue_date')

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('recipient', 'title', 'is_read', 'created_at')
    list_filter = ('is_read', 'created_at')
