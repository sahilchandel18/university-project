import uuid
from decimal import Decimal
from django.db import models
from django.conf import settings
from django.utils import timezone
from accounts.models import CustomUser, StudentProfile
from departments.models import Department

class NoDuesApplication(models.Model):
    STATUS_DRAFT = 'DRAFT'
    STATUS_SUBMITTED = 'SUBMITTED'
    STATUS_IN_PROGRESS = 'IN_PROGRESS'
    STATUS_ACTION_REQUIRED = 'ACTION_REQUIRED'
    STATUS_ON_HOLD = 'ON_HOLD'
    STATUS_REJECTED = 'REJECTED'
    STATUS_COMPLETED = 'COMPLETED'

    STATUS_CHOICES = [
        (STATUS_DRAFT, 'Draft'),
        (STATUS_SUBMITTED, 'Submitted'),
        (STATUS_IN_PROGRESS, 'In Progress'),
        (STATUS_ACTION_REQUIRED, 'Action Required (Dues/Remarks)'),
        (STATUS_ON_HOLD, 'On Hold'),
        (STATUS_REJECTED, 'Rejected'),
        (STATUS_COMPLETED, 'Fully Approved / Completed'),
    ]

    PURPOSE_DEGREE = 'DEGREE'
    PURPOSE_SEMESTER = 'SEMESTER'
    PURPOSE_MIGRATION = 'MIGRATION'
    PURPOSE_INTERNSHIP = 'INTERNSHIP'
    PURPOSE_OTHER = 'OTHER'

    PURPOSE_CHOICES = [
        (PURPOSE_DEGREE, 'Final Degree / Course Completion Clearance'),
        (PURPOSE_SEMESTER, 'Semester End Registration Clearance'),
        (PURPOSE_MIGRATION, 'Transfer / Migration Certificate Clearance'),
        (PURPOSE_INTERNSHIP, 'Off-Campus Internship / Project Clearance'),
        (PURPOSE_OTHER, 'Other Institutional Clearance'),
    ]

    application_no = models.CharField(max_length=50, unique=True, db_index=True)
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name='applications')
    purpose = models.CharField(max_length=30, choices=PURPOSE_CHOICES, default=PURPOSE_DEGREE)
    other_purpose_details = models.CharField(max_length=255, blank=True)
    academic_session = models.CharField(max_length=20, default="2025-2026")
    current_semester = models.CharField(max_length=30, default="8th Semester")
    supporting_document = models.FileField(upload_to='application_docs/', blank=True, null=True)
    student_remarks = models.TextField(blank=True, help_text="Notes/Comments from student upon submission")
    
    overall_status = models.CharField(max_length=30, choices=STATUS_CHOICES, default=STATUS_SUBMITTED)
    total_dues_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    
    submitted_at = models.DateTimeField(default=timezone.now)
    completed_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-submitted_at']

    def __str__(self):
        return f"{self.application_no} - {self.student.roll_number} ({self.get_overall_status_display()})"

    @property
    def is_completed(self):
        return self.overall_status == self.STATUS_COMPLETED

    @property
    def approved_departments_count(self):
        return self.department_clearances.filter(status='APPROVED').count()

    @property
    def total_mandatory_count(self):
        return self.department_clearances.filter(department__is_mandatory=True).count()

    @property
    def progress_percentage(self):
        total = self.total_mandatory_count
        if total == 0:
            return 0
        approved = self.department_clearances.filter(department__is_mandatory=True, status='APPROVED').count()
        return int((approved / total) * 100)

    def recalculate_status(self, save=True):
        """
        Recalculates the overall application status based on each department's clearance record.
        Automatically issues a certificate if all mandatory departments have approved!
        """
        clearances = self.department_clearances.select_related('department').all()
        mandatory_clearances = [c for c in clearances if c.department.is_mandatory]

        # Calculate total dues
        total_dues = sum(c.dues_amount for c in clearances)
        self.total_dues_amount = total_dues

        if not mandatory_clearances:
            if save:
                self.save()
            return self.overall_status

        # Check for Rejection
        if any(c.status == DepartmentClearance.STATUS_REJECTED for c in mandatory_clearances):
            self.overall_status = self.STATUS_REJECTED
        # Check for On Hold
        elif any(c.status == DepartmentClearance.STATUS_ON_HOLD for c in mandatory_clearances):
            self.overall_status = self.STATUS_ON_HOLD
        # Check for Action Required / Pending Dues
        elif any(c.status == DepartmentClearance.STATUS_ACTION_REQUIRED or c.dues_amount > Decimal('0.00') for c in mandatory_clearances):
            self.overall_status = self.STATUS_ACTION_REQUIRED
        # Check if ALL mandatory departments are approved
        elif all(c.status == DepartmentClearance.STATUS_APPROVED for c in mandatory_clearances):
            self.overall_status = self.STATUS_COMPLETED
            if not self.completed_at:
                self.completed_at = timezone.now()
        # Check if partially approved
        elif any(c.status == DepartmentClearance.STATUS_APPROVED for c in mandatory_clearances):
            self.overall_status = self.STATUS_IN_PROGRESS
        else:
            self.overall_status = self.STATUS_SUBMITTED

        if save:
            self.save()

        # If completed, ensure certificate is generated
        if self.overall_status == self.STATUS_COMPLETED:
            self.generate_or_update_certificate()

        return self.overall_status

    def generate_or_update_certificate(self):
        """
        Generates or updates the NoDuesCertificate for this completed application.
        """
        from .pdf_generator import generate_certificate_pdf
        
        cert, created = NoDuesCertificate.objects.get_or_create(
            application=self,
            defaults={
                'student': self.student,
                'certificate_no': f"NDC-{timezone.now().year}-{self.student.roll_number.replace('/', '-')[-6:]}-{self.id:04d}",
                'issue_date': timezone.now().date(),
                'is_valid': True
            }
        )
        if not cert.certificate_no:
            cert.certificate_no = f"NDC-{timezone.now().year}-{self.id:05d}"
            cert.save()

        # Generate QR code & PDF file
        try:
            generate_certificate_pdf(cert)
        except Exception as e:
            print(f"Error generating PDF certificate: {e}")

        # Send notification to student
        Notification.objects.create(
            recipient=self.student.user,
            title="🎉 No Dues Certificate Issued!",
            message=f"All departments have cleared your dues. Your official No Dues Certificate ({cert.certificate_no}) is now available for download.",
            link=f"/student/application/{self.application_no}/"
        )
        return cert


class DepartmentClearance(models.Model):
    STATUS_PENDING = 'PENDING'
    STATUS_APPROVED = 'APPROVED'
    STATUS_ACTION_REQUIRED = 'ACTION_REQUIRED'
    STATUS_ON_HOLD = 'ON_HOLD'
    STATUS_REJECTED = 'REJECTED'

    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending Verification'),
        (STATUS_APPROVED, 'Approved / No Dues'),
        (STATUS_ACTION_REQUIRED, 'Dues / Action Required'),
        (STATUS_ON_HOLD, 'Verification On Hold'),
        (STATUS_REJECTED, 'Clearance Rejected'),
    ]

    application = models.ForeignKey(NoDuesApplication, on_delete=models.CASCADE, related_name='department_clearances')
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='clearances')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    
    dues_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    dues_breakdown = models.TextField(blank=True, help_text="Itemized explanation of dues, book titles, fee heads")
    remarks = models.TextField(blank=True, help_text="Official verification comments and instructions to the student")
    internal_notes = models.TextField(blank=True, help_text="Internal staff notes not visible to student")
    
    checklist_data = models.JSONField(default=dict, blank=True)
    reviewed_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_clearances')
    reviewed_at = models.DateTimeField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('application', 'department')
        ordering = ['department__display_order']

    def __str__(self):
        return f"{self.application.application_no} - {self.department.code}: {self.get_status_display()}"


class ClearanceLog(models.Model):
    application = models.ForeignKey(NoDuesApplication, on_delete=models.CASCADE, related_name='logs')
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True)
    actor = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=100)
    previous_status = models.CharField(max_length=50, blank=True)
    new_status = models.CharField(max_length=50, blank=True)
    dues_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    remarks = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"[{self.timestamp.strftime('%Y-%m-%d %H:%M')}] {self.application.application_no} - {self.action}"


class NoDuesCertificate(models.Model):
    certificate_no = models.CharField(max_length=50, unique=True, db_index=True)
    application = models.OneToOneField(NoDuesApplication, on_delete=models.CASCADE, related_name='certificate')
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name='certificates')
    issue_date = models.DateField(default=timezone.now)
    verification_uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    qr_code = models.ImageField(upload_to='qr_codes/', blank=True, null=True)
    pdf_file = models.FileField(upload_to='certificates/', blank=True, null=True)
    is_valid = models.BooleanField(default=True)
    revocation_reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.certificate_no} - {self.student.roll_number}"

    def get_absolute_verification_url(self, request=None):
        path = f"/verify/{self.verification_uuid}/"
        if request:
            return request.build_absolute_uri(path)
        return path


class Notification(models.Model):
    recipient = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=200)
    message = models.TextField()
    link = models.CharField(max_length=255, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.recipient.username} - {self.title}"
