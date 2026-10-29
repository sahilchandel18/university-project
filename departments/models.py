from django.db import models

class Department(models.Model):
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=20, unique=True, help_text="e.g. LIB, ACC, HOSTEL, LAB, SPORTS, TPC, EXAM")
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=50, default="bi-building", help_text="Bootstrap 5 icon class, e.g. bi-book, bi-cash-coin")
    location = models.CharField(max_length=150, blank=True, default="Main Administrative Block")
    contact_email = models.EmailField(blank=True)
    contact_phone = models.CharField(max_length=20, blank=True)
    is_mandatory = models.BooleanField(default=True, help_text="Required for student to get final No Dues Certificate")
    display_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['display_order', 'name']

    def __str__(self):
        return f"{self.name} ({self.code})"

    @property
    def active_staff_count(self):
        return self.staff_members.count()

    @property
    def pending_verifications_count(self):
        return self.clearances.filter(status='PENDING').count()
