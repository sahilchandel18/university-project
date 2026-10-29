from decimal import Decimal
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth import get_user_model
from accounts.models import CustomUser, StudentProfile, StaffProfile
from departments.models import Department
from clearance.models import (
    NoDuesApplication, DepartmentClearance, ClearanceLog,
    NoDuesCertificate, Notification
)
from clearance.pdf_generator import generate_certificate_pdf

class Command(BaseCommand):
    help = "Seed database with departments, staff, students, realistic applications, and demo data."

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("Seeding University No Dues System database..."))

        # 1. Create or update University Administrator
        admin_user, created = CustomUser.objects.get_or_create(
            username='admin',
            defaults={
                'email': 'admin@university.edu.in',
                'first_name': 'Dr. Vikram',
                'last_name': 'Seth',
                'role': CustomUser.ROLE_ADMIN,
                'is_staff': True,
                'is_superuser': True,
            }
        )
        admin_user.set_password('admin123')
        admin_user.role = CustomUser.ROLE_ADMIN
        admin_user.is_staff = True
        admin_user.is_superuser = True
        admin_user.save()
        self.stdout.write(self.style.SUCCESS("[OK] Admin created: admin / admin123"))

        # 2. Statutory University Departments
        departments_data = [
            {
                'name': 'Central University Library',
                'code': 'LIB',
                'description': 'Verification of returned books, reference materials, journals, and fine dues.',
                'icon': 'bi-book',
                'location': 'Dr. S.R. Ranganathan Memorial Library Building',
                'display_order': 1,
                'is_mandatory': True,
            },
            {
                'name': 'Accounts & Finance Division',
                'code': 'ACC',
                'description': 'Auditing of tuition fees, examination fees, hostel charges, security deposits, and university dues.',
                'icon': 'bi-cash-coin',
                'location': 'Administrative Block, Ground Floor',
                'display_order': 2,
                'is_mandatory': True,
            },
            {
                'name': 'Computer Science & Eng. Laboratory',
                'code': 'CSE_LAB',
                'description': 'Verification of lab development kits, IoT modules, servers, and departmental project submissions.',
                'icon': 'bi-cpu',
                'location': 'Computing Centre, Room CS-204',
                'display_order': 3,
                'is_mandatory': True,
            },
            {
                'name': 'Hostel & Mess Administration',
                'code': 'HOSTEL',
                'description': 'Room inventory physical clearance, mess bills settlement, and key handover confirmation.',
                'icon': 'bi-houses',
                'location': 'Chief Warden Office, Hostel Complex',
                'display_order': 4,
                'is_mandatory': True,
            },
            {
                'name': 'Sports Complex & Gymnasium',
                'code': 'SPORTS',
                'description': 'Physical education sports gear, kit return, and gym equipment clearance.',
                'icon': 'bi-trophy',
                'location': 'University Indoor Stadium',
                'display_order': 5,
                'is_mandatory': True,
            },
            {
                'name': 'Training & Placement / Alumni Cell',
                'code': 'TP_CELL',
                'description': 'Graduating student exit survey, corporate placement confirmation, and alumni registry onboarding.',
                'icon': 'bi-briefcase',
                'location': 'Career Development Centre, Block 3',
                'display_order': 6,
                'is_mandatory': True,
            },
            {
                'name': 'Examination & Degree Section',
                'code': 'EXAM',
                'description': 'Degree eligibility check, credit audit, mark-sheet archive, and migration certificate verification.',
                'icon': 'bi-award',
                'location': 'Office of the Controller of Examinations',
                'display_order': 7,
                'is_mandatory': True,
            },
        ]

        dept_objs = {}
        for d in departments_data:
            dept, _ = Department.objects.update_or_create(
                code=d['code'],
                defaults=d
            )
            dept_objs[d['code']] = dept

        self.stdout.write(self.style.SUCCESS(f"[OK] {len(dept_objs)} Statutory Departments verified."))

        # 3. Staff Accounts for each Department
        staff_data = [
            ('staff_library', 'Sunita', 'Menon', 'LIB', 'EMP-LIB-101', 'University Chief Librarian'),
            ('staff_accounts', 'Rajesh', 'Verma', 'ACC', 'EMP-ACC-202', 'Senior Accounts Officer'),
            ('staff_lab', 'Neha', 'Gupta', 'CSE_LAB', 'EMP-LAB-303', 'Lead Laboratory Superintendent'),
            ('staff_hostel', 'Amit', 'Bhargava', 'HOSTEL', 'EMP-HST-404', 'Chief Hostel Warden'),
            ('staff_sports', 'Kuldeep', 'Yadav', 'SPORTS', 'EMP-SPT-505', 'Sports Director & Physical Trainer'),
            ('staff_tp', 'Ritu', 'Saxena', 'TP_CELL', 'EMP-TPC-606', 'Head - Corporate Relations & Placements'),
        ]

        staff_users = {}
        for username, fname, lname, dept_code, emp_id, desig in staff_data:
            user, _ = CustomUser.objects.get_or_create(
                username=username,
                defaults={
                    'email': f"{username}@university.edu.in",
                    'first_name': fname,
                    'last_name': lname,
                    'role': CustomUser.ROLE_STAFF,
                    'is_staff': True
                }
            )
            user.set_password('password123')
            user.role = CustomUser.ROLE_STAFF
            user.is_staff = True
            user.save()

            StaffProfile.objects.update_or_create(
                user=user,
                defaults={
                    'department': dept_objs[dept_code],
                    'employee_id': emp_id,
                    'designation': desig,
                    'cabin_office': f"{dept_objs[dept_code].name} Desk A"
                }
            )
            staff_users[dept_code] = user

        self.stdout.write(self.style.SUCCESS("[OK] Department Staff accounts created (password: password123)."))

        # 4. Realistic Student Accounts & Application Scenarios
        students_info = [
            {
                'username': 'student_aarav',
                'name': ('Aarav', 'Patel'),
                'roll': '2022CSE001',
                'reg': 'REG/2022/8901',
                'branch': 'Computer Science & Engineering',
                'hostel': True,
                'hostel_details': 'Tagore Hall - Room 314',
                'scenario': 'COMPLETED'
            },
            {
                'username': 'student_priya',
                'name': ('Priya', 'Sharma'),
                'roll': '2022CSE024',
                'reg': 'REG/2022/8924',
                'branch': 'Computer Science & Engineering',
                'hostel': False,
                'hostel_details': 'Day Scholar',
                'scenario': 'IN_PROGRESS'
            },
            {
                'username': 'student_rohan',
                'name': ('Rohan', 'Das'),
                'roll': '2022CSE058',
                'reg': 'REG/2022/8958',
                'branch': 'Computer Science & Engineering',
                'hostel': True,
                'hostel_details': 'Bhabha Hostel - Room 102',
                'scenario': 'ACTION_REQUIRED'
            },
            {
                'username': 'student_ananya',
                'name': ('Ananya', 'Iyer'),
                'roll': '2022CSE089',
                'reg': 'REG/2022/8989',
                'branch': 'Computer Science & Engineering',
                'hostel': False,
                'hostel_details': 'Day Scholar',
                'scenario': 'FRESH'
            },
        ]

        for s in students_info:
            user, _ = CustomUser.objects.get_or_create(
                username=s['username'],
                defaults={
                    'email': f"{s['username']}@university.edu.in",
                    'first_name': s['name'][0],
                    'last_name': s['name'][1],
                    'role': CustomUser.ROLE_STUDENT
                }
            )
            user.set_password('student123')
            user.role = CustomUser.ROLE_STUDENT
            user.save()

            stud_prof, _ = StudentProfile.objects.update_or_create(
                user=user,
                defaults={
                    'roll_number': s['roll'],
                    'registration_number': s['reg'],
                    'course': 'B.Tech (Computer Science & Engineering)',
                    'branch': s['branch'],
                    'semester': '8th Semester (Final Year)',
                    'batch_year': '2022 - 2026',
                    'academic_session': '2025-2026',
                    'is_hostel_resident': s['hostel'],
                    'hostel_details': s['hostel_details'],
                    'father_name': f"Mr. {s['name'][1]}",
                    'address': 'Flat 402, Green Avenue, University City',
                    'contact_number': '+91 98765 43210'
                }
            )

            # Build applications according to scenario
            if s['scenario'] == 'FRESH':
                # Ananya has no application submitted yet, ready for live testing
                continue

            app_no = f"ND-2026-{s['roll'][-4:]}-01"
            app, _ = NoDuesApplication.objects.update_or_create(
                application_no=app_no,
                defaults={
                    'student': stud_prof,
                    'purpose': NoDuesApplication.PURPOSE_DEGREE,
                    'academic_session': '2025-2026',
                    'current_semester': '8th Semester (Final Year)',
                    'student_remarks': 'Applying for final degree and provisional certificate clearance.',
                    'submitted_at': timezone.now() - timezone.timedelta(days=7),
                }
            )

            # Create clearances for all departments
            for dept in Department.objects.all():
                clr, _ = DepartmentClearance.objects.get_or_create(
                    application=app,
                    department=dept
                )

                reviewer = staff_users.get(dept.code, admin_user)

                if s['scenario'] == 'COMPLETED':
                    # All departments approved!
                    clr.status = DepartmentClearance.STATUS_APPROVED
                    clr.dues_amount = Decimal('0.00')
                    clr.remarks = f"No dues pending in {dept.name}. Verified and cleared."
                    clr.reviewed_by = reviewer
                    clr.reviewed_at = timezone.now() - timezone.timedelta(days=2)
                    clr.save()

                elif s['scenario'] == 'IN_PROGRESS':
                    # 4 departments approved, 3 pending
                    if dept.code in ['LIB', 'CSE_LAB', 'SPORTS', 'TP_CELL']:
                        clr.status = DepartmentClearance.STATUS_APPROVED
                        clr.dues_amount = Decimal('0.00')
                        clr.remarks = f"Clearance approved by {dept.name} officer."
                        clr.reviewed_by = reviewer
                        clr.reviewed_at = timezone.now() - timezone.timedelta(days=1)
                    else:
                        clr.status = DepartmentClearance.STATUS_PENDING
                        clr.remarks = "Pending review by department."
                    clr.save()

                elif s['scenario'] == 'ACTION_REQUIRED':
                    # Library has ₹250 fine, Accounts has ₹500 fee, others pending or approved
                    if dept.code == 'LIB':
                        clr.status = DepartmentClearance.STATUS_ACTION_REQUIRED
                        clr.dues_amount = Decimal('250.00')
                        clr.dues_breakdown = "Overdue fine for book: 'Computer Networks 5th Ed' (15 days overdue @ Rs 10/day + Rs 100 late handling)"
                        clr.remarks = "Please pay Rs. 250 at the central library circulation desk and return book."
                        clr.reviewed_by = reviewer
                        clr.reviewed_at = timezone.now() - timezone.timedelta(days=3)
                    elif dept.code == 'ACC':
                        clr.status = DepartmentClearance.STATUS_ACTION_REQUIRED
                        clr.dues_amount = Decimal('500.00')
                        clr.dues_breakdown = "Semester 7 Late Registration administrative surcharge"
                        clr.remarks = "Pay Rs. 500 online through student fee portal or at Cash Counter 2."
                        clr.reviewed_by = reviewer
                        clr.reviewed_at = timezone.now() - timezone.timedelta(days=3)
                    elif dept.code == 'HOSTEL':
                        clr.status = DepartmentClearance.STATUS_ON_HOLD
                        clr.remarks = "Room key handover pending. Physical room inspection scheduled tomorrow 11 AM."
                        clr.reviewed_by = reviewer
                        clr.reviewed_at = timezone.now() - timezone.timedelta(days=2)
                    elif dept.code in ['CSE_LAB', 'SPORTS']:
                        clr.status = DepartmentClearance.STATUS_APPROVED
                        clr.dues_amount = Decimal('0.00')
                        clr.remarks = "Lab & sports assets returned in sound condition."
                        clr.reviewed_by = reviewer
                        clr.reviewed_at = timezone.now() - timezone.timedelta(days=4)
                    else:
                        clr.status = DepartmentClearance.STATUS_PENDING
                        clr.remarks = "Under review."
                    clr.save()

            # Recalculate application overall status
            app.recalculate_status(save=True)

            # If completed, generate official certificate and PDF
            if s['scenario'] == 'COMPLETED':
                cert = app.generate_or_update_certificate()
                self.stdout.write(self.style.SUCCESS(f"[OK] Certificate {cert.certificate_no} generated for {s['roll']}"))

        self.stdout.write(self.style.SUCCESS("\n========================================================"))
        self.stdout.write(self.style.SUCCESS("SYSTEM SEEDED SUCCESSFULLY! DEMO CREDENTIALS:"))
        self.stdout.write("--------------------------------------------------------")
        self.stdout.write("1. University Admin:      admin / admin123")
        self.stdout.write("2. Department Staff:       staff_library / password123")
        self.stdout.write("                          staff_accounts / password123")
        self.stdout.write("                          staff_hostel / password123")
        self.stdout.write("                          staff_lab / password123")
        self.stdout.write("3. Student (Completed):    student_aarav / student123")
        self.stdout.write("4. Student (In Progress):  student_priya / student123")
        self.stdout.write("5. Student (With Dues):    student_rohan / student123")
        self.stdout.write("6. Student (Fresh - Apply):student_ananya / student123")
        self.stdout.write("========================================================\n")
