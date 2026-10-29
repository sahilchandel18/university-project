from django.db import models
from django.contrib.auth.models import AbstractUser

class CustomUser(AbstractUser):
    ROLE_STUDENT = 'STUDENT'
    ROLE_STAFF = 'STAFF'
    ROLE_ADMIN = 'ADMIN'

    ROLE_CHOICES = [
        (ROLE_STUDENT, 'Student'),
        (ROLE_STAFF, 'Department Staff'),
        (ROLE_ADMIN, 'University Administrator'),
    ]

    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=ROLE_STUDENT)
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)

    @property
    def is_student(self):
        return self.role == self.ROLE_STUDENT

    @property
    def is_department_staff(self):
        return self.role == self.ROLE_STAFF

    @property
    def is_university_admin(self):
        return self.role == self.ROLE_ADMIN or self.is_superuser

    def __str__(self):
        full_name = self.get_full_name()
        return f"{full_name if full_name else self.username} ({self.get_role_display()})"


class StudentProfile(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='student_profile')
    roll_number = models.CharField(max_length=50, unique=True, verbose_name="Roll Number")
    registration_number = models.CharField(max_length=50, unique=True, verbose_name="Registration / Enrollment No.")
    course = models.CharField(max_length=100, default="B.Tech (Computer Science & Engineering)")
    branch = models.CharField(max_length=100, default="Computer Science & Engineering")
    semester = models.CharField(max_length=20, default="8th Semester")
    batch_year = models.CharField(max_length=30, default="2022 - 2026")
    academic_session = models.CharField(max_length=20, default="2025-2026")
    is_hostel_resident = models.BooleanField(default=False)
    hostel_details = models.CharField(max_length=100, blank=True, default="Day Scholar")
    father_name = models.CharField(max_length=100, blank=True)
    address = models.TextField(blank=True)
    contact_number = models.CharField(max_length=15, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.roll_number} - {self.user.get_full_name() or self.user.username}"


class StaffProfile(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='staff_profile')
    department = models.ForeignKey('departments.Department', on_delete=models.CASCADE, related_name='staff_members')
    employee_id = models.CharField(max_length=50, unique=True)
    designation = models.CharField(max_length=100, default="Clearance Verification Officer")
    cabin_office = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} - {self.department.name} ({self.designation})"
