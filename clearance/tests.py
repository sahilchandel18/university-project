import os
from decimal import Decimal
from django.test import TestCase, Client
from django.urls import reverse
from accounts.models import CustomUser, StudentProfile, StaffProfile
from departments.models import Department
from clearance.models import (
    NoDuesApplication, DepartmentClearance, ClearanceLog,
    NoDuesCertificate, Notification
)

class UniversityNoDuesSystemTests(TestCase):
    def setUp(self):
        self.client = Client()

        # 1. Create Admin
        self.admin_user = CustomUser.objects.create_user(
            username='admin_test',
            password='password123',
            email='admin@univ.edu',
            role=CustomUser.ROLE_ADMIN,
            is_staff=True,
            is_superuser=True
        )

        # 2. Create Departments
        self.dept_lib = Department.objects.create(
            name='Central Library',
            code='LIB',
            display_order=1,
            is_mandatory=True,
            is_active=True
        )
        self.dept_acc = Department.objects.create(
            name='Accounts Section',
            code='ACC',
            display_order=2,
            is_mandatory=True,
            is_active=True
        )

        # 3. Create Department Staff
        self.staff_lib_user = CustomUser.objects.create_user(
            username='staff_lib',
            password='password123',
            role=CustomUser.ROLE_STAFF,
            is_staff=True
        )
        self.staff_lib_profile = StaffProfile.objects.create(
            user=self.staff_lib_user,
            department=self.dept_lib,
            employee_id='EMP-001'
        )

        self.staff_acc_user = CustomUser.objects.create_user(
            username='staff_acc',
            password='password123',
            role=CustomUser.ROLE_STAFF,
            is_staff=True
        )
        self.staff_acc_profile = StaffProfile.objects.create(
            user=self.staff_acc_user,
            department=self.dept_acc,
            employee_id='EMP-002'
        )

        # 4. Create Student
        self.student_user = CustomUser.objects.create_user(
            username='student_test',
            password='password123',
            first_name='Dev',
            last_name='Sharma',
            role=CustomUser.ROLE_STUDENT
        )
        self.student_profile = StudentProfile.objects.create(
            user=self.student_user,
            roll_number='2022CSE999',
            registration_number='REG/2022/9999',
            course='B.Tech (CSE)',
            branch='Computer Science & Engineering',
            semester='8th Semester',
            batch_year='2022 - 2026',
            academic_session='2025-2026'
        )

    def test_student_application_submission_creates_all_department_clearances(self):
        """Test that submitting an application automatically dispatches clearance records to all active departments."""
        self.client.login(username='student_test', password='password123')
        response = self.client.post(reverse('student_apply'), {
            'purpose': 'DEGREE',
            'academic_session': '2025-2026',
            'current_semester': '8th Semester',
            'student_remarks': 'Testing submission',
            'declaration': 'on'
        })
        self.assertEqual(response.status_code, 302)

        app = NoDuesApplication.objects.filter(student=self.student_profile).first()
        self.assertIsNotNone(app)
        self.assertEqual(app.overall_status, NoDuesApplication.STATUS_SUBMITTED)
        self.assertEqual(app.department_clearances.count(), 2)

    def test_department_staff_clearance_approval_workflow(self):
        """Test department staff reviewing, setting dues, and clearing."""
        # Submit application
        app = NoDuesApplication.objects.create(
            application_no='ND-TEST-001',
            student=self.student_profile,
            purpose='DEGREE'
        )
        clr_lib = DepartmentClearance.objects.create(application=app, department=self.dept_lib, status='PENDING')
        clr_acc = DepartmentClearance.objects.create(application=app, department=self.dept_acc, status='PENDING')

        # Staff Library logs in and flags fine dues
        self.client.login(username='staff_lib', password='password123')
        response = self.client.post(reverse('department_review_clearance', kwargs={'clearance_id': clr_lib.id}), {
            'action': 'ACTION_REQUIRED',
            'dues_amount': '150.00',
            'dues_breakdown': 'Library late fee',
            'remarks': 'Pay Rs 150 at desk'
        })
        self.assertEqual(response.status_code, 302)

        clr_lib.refresh_from_db()
        app.refresh_from_db()
        self.assertEqual(clr_lib.status, DepartmentClearance.STATUS_ACTION_REQUIRED)
        self.assertEqual(clr_lib.dues_amount, Decimal('150.00'))
        self.assertEqual(app.overall_status, NoDuesApplication.STATUS_ACTION_REQUIRED)
        self.assertEqual(app.total_dues_amount, Decimal('150.00'))

        # Student clears fine -> Staff approves
        response = self.client.post(reverse('department_review_clearance', kwargs={'clearance_id': clr_lib.id}), {
            'action': 'APPROVE',
            'dues_amount': '0.00',
            'remarks': 'Book returned and fine cleared'
        })
        clr_lib.refresh_from_db()
        app.refresh_from_db()
        self.assertEqual(clr_lib.status, DepartmentClearance.STATUS_APPROVED)
        self.assertEqual(clr_lib.dues_amount, Decimal('0.00'))
        self.assertEqual(app.overall_status, NoDuesApplication.STATUS_IN_PROGRESS)

        # Accounts staff approves
        self.client.login(username='staff_acc', password='password123')
        response = self.client.post(reverse('department_review_clearance', kwargs={'clearance_id': clr_acc.id}), {
            'action': 'APPROVE',
            'dues_amount': '0.00',
            'remarks': 'Accounts verified'
        })
        clr_acc.refresh_from_db()
        app.refresh_from_db()

        # ALL mandatory departments approved -> Status must be COMPLETED & Certificate generated!
        self.assertEqual(app.overall_status, NoDuesApplication.STATUS_COMPLETED)
        self.assertTrue(hasattr(app, 'certificate'))
        self.assertTrue(app.certificate.is_valid)
        self.assertTrue(os.path.exists(app.certificate.pdf_file.path))

    def test_public_certificate_verification(self):
        """Test public certificate verification endpoint."""
        app = NoDuesApplication.objects.create(
            application_no='ND-TEST-002',
            student=self.student_profile,
            purpose='DEGREE'
        )
        cert = app.generate_or_update_certificate()

        # Public verification via UUID
        url = reverse('verify_certificate', kwargs={'verification_uuid': cert.verification_uuid})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, cert.certificate_no)
        self.assertContains(response, 'AUTHENTIC & DIGITALLY VERIFIED DOCUMENT')

    def test_admin_force_approve_override(self):
        """Test administrator override capability."""
        app = NoDuesApplication.objects.create(
            application_no='ND-TEST-003',
            student=self.student_profile,
            purpose='DEGREE'
        )
        clr_lib = DepartmentClearance.objects.create(application=app, department=self.dept_lib, status='PENDING')
        clr_acc = DepartmentClearance.objects.create(application=app, department=self.dept_acc, status='PENDING')

        self.client.login(username='admin_test', password='password123')
        response = self.client.post(reverse('admin_application_detail', kwargs={'app_no': app.application_no}), {
            'admin_action': 'FORCE_APPROVE_ALL',
            'admin_remarks': 'Approved under Dean authority'
        })
        self.assertEqual(response.status_code, 302)

        app.refresh_from_db()
        self.assertEqual(app.overall_status, NoDuesApplication.STATUS_COMPLETED)
        self.assertTrue(hasattr(app, 'certificate'))
