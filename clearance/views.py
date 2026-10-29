import os
import csv
from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, Http404, JsonResponse, FileResponse
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.utils import timezone
from django.db.models import Count, Q, Sum
from accounts.models import CustomUser, StudentProfile, StaffProfile
from departments.models import Department
from .models import (
    NoDuesApplication, DepartmentClearance, ClearanceLog,
    NoDuesCertificate, Notification
)
from .pdf_generator import generate_certificate_pdf

# Role check decorators
def student_required(view_func):
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        if not request.user.is_student:
            messages.warning(request, "Access restricted to Student accounts.")
            return redirect('dashboard_redirect')
        return view_func(request, *args, **kwargs)
    return wrapper

def staff_required(view_func):
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        if not (request.user.is_department_staff or request.user.is_university_admin):
            messages.warning(request, "Access restricted to Department Staff.")
            return redirect('dashboard_redirect')
        return view_func(request, *args, **kwargs)
    return wrapper

def admin_required(view_func):
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        if not request.user.is_university_admin:
            messages.warning(request, "Access restricted to University Administrators.")
            return redirect('dashboard_redirect')
        return view_func(request, *args, **kwargs)
    return wrapper


# -------------------------------------------------------------
# PUBLIC / CORE VIEWS
# -------------------------------------------------------------

def landing_page(request):
    """
    Public University Landing Page with portal overview, process workflow, and quick search.
    """
    total_apps = NoDuesApplication.objects.count()
    completed_apps = NoDuesApplication.objects.filter(overall_status=NoDuesApplication.STATUS_COMPLETED).count()
    total_departments = Department.objects.filter(is_active=True).count()
    total_students = StudentProfile.objects.count()

    context = {
        'total_apps': total_apps,
        'completed_apps': completed_apps,
        'total_departments': total_departments,
        'total_students': total_students,
        'active_departments': Department.objects.filter(is_active=True).order_by('display_order'),
    }
    return render(request, 'clearance/landing.html', context)


def public_verify_certificate(request, verification_uuid=None):
    """
    Public Certificate Verification Portal.
    Allows students, employers, and officials to scan a QR code or enter
    Certificate ID / UUID to verify authenticity.
    """
    cert = None
    searched = False
    error_message = None

    if verification_uuid:
        searched = True
        try:
            cert = NoDuesCertificate.objects.select_related('student__user', 'application').get(verification_uuid=verification_uuid)
        except (NoDuesCertificate.DoesNotExist, ValueError):
            error_message = "Certificate with this verification token was not found or is invalid."
    elif request.method == 'GET' and 'query' in request.GET:
        searched = True
        query = request.GET.get('query', '').strip()
        if query:
            try:
                cert = NoDuesCertificate.objects.select_related('student__user', 'application').filter(
                    Q(certificate_no__iexact=query) |
                    Q(student__roll_number__iexact=query) |
                    Q(verification_uuid__iexact=query)
                ).first()
                if not cert:
                    error_message = f"No authentic certificate found matching query: '{query}'"
            except Exception:
                error_message = "Invalid search query parameter."

    department_clearances = []
    if cert and cert.application:
        department_clearances = cert.application.department_clearances.select_related('department', 'reviewed_by').order_by('department__display_order')

    context = {
        'cert': cert,
        'searched': searched,
        'error_message': error_message,
        'department_clearances': department_clearances,
    }
    return render(request, 'clearance/verify_certificate.html', context)


# -------------------------------------------------------------
# STUDENT PORTAL VIEWS
# -------------------------------------------------------------

@student_required
def student_dashboard(request):
    """
    Student Dashboard with live clearance status, progress bar, dues alerts, and certificate link.
    """
    student = request.user.student_profile
    active_application = student.applications.first() # most recent

    all_applications = student.applications.all()
    notifications = request.user.notifications.all()[:10]

    department_records = []
    if active_application:
        department_records = active_application.department_clearances.select_related('department', 'reviewed_by').order_by('department__display_order')

    context = {
        'student': student,
        'application': active_application,
        'department_records': department_records,
        'all_applications': all_applications,
        'notifications': notifications,
    }
    return render(request, 'clearance/student/dashboard.html', context)


@student_required
def student_apply(request):
    """
    Submit a new No Dues application.
    Automatically assigns clearance records to all active mandatory departments.
    """
    student = request.user.student_profile

    # Check if student already has a pending or in-progress application
    existing_active = student.applications.filter(
        overall_status__in=[
            NoDuesApplication.STATUS_SUBMITTED,
            NoDuesApplication.STATUS_IN_PROGRESS,
            NoDuesApplication.STATUS_ACTION_REQUIRED,
            NoDuesApplication.STATUS_ON_HOLD
        ]
    ).first()

    if existing_active:
        messages.warning(
            request,
            f"You already have an active application ({existing_active.application_no}) currently in status '{existing_active.get_overall_status_display()}'. You cannot create a new one until this is resolved."
        )
        return redirect('student_application_detail', app_no=existing_active.application_no)

    if request.method == 'POST':
        purpose = request.POST.get('purpose', NoDuesApplication.PURPOSE_DEGREE)
        other_purpose_details = request.POST.get('other_purpose_details', '').strip()
        academic_session = request.POST.get('academic_session', student.academic_session)
        current_semester = request.POST.get('current_semester', student.semester)
        student_remarks = request.POST.get('student_remarks', '').strip()
        supporting_doc = request.FILES.get('supporting_document')

        # Generate unique application number: ND-YEAR-RANDOM
        app_count = NoDuesApplication.objects.count() + 1
        year_str = timezone.now().strftime("%Y")
        app_no = f"ND-{year_str}-{student.roll_number.replace('/', '-')[-4:]}-{app_count:04d}"

        app = NoDuesApplication.objects.create(
            application_no=app_no,
            student=student,
            purpose=purpose,
            other_purpose_details=other_purpose_details,
            academic_session=academic_session,
            current_semester=current_semester,
            supporting_document=supporting_doc,
            student_remarks=student_remarks,
            overall_status=NoDuesApplication.STATUS_SUBMITTED,
            submitted_at=timezone.now()
        )

        # Create DepartmentClearance for every active department
        active_departments = Department.objects.filter(is_active=True).order_by('display_order')
        for dept in active_departments:
            DepartmentClearance.objects.create(
                application=app,
                department=dept,
                status=DepartmentClearance.STATUS_PENDING,
                remarks="Pending verification by department staff."
            )

        # Log action
        ClearanceLog.objects.create(
            application=app,
            actor=request.user,
            action="APPLICATION_SUBMITTED",
            previous_status="",
            new_status=NoDuesApplication.STATUS_SUBMITTED,
            remarks=f"Application submitted for purpose: {app.get_purpose_display()}"
        )

        # Notify student
        Notification.objects.create(
            recipient=request.user,
            title="Application Submitted Successfully",
            message=f"Your No Dues Application ({app.application_no}) has been dispatched to all {active_departments.count()} university departments for verification.",
            link=f"/student/application/{app.application_no}/"
        )

        messages.success(request, f"Application {app.application_no} submitted successfully! Your clearance pipeline is now active.")
        return redirect('student_application_detail', app_no=app.application_no)

    context = {
        'student': student,
        'purposes': NoDuesApplication.PURPOSE_CHOICES,
        'active_departments': Department.objects.filter(is_active=True).order_by('display_order'),
    }
    return render(request, 'clearance/student/apply.html', context)


@student_required
def student_application_detail(request, app_no):
    """
    Detailed tracker for a student's No Dues application.
    Displays department-by-department clearance timeline, dues breakdown, remarks, and certificate.
    """
    student = request.user.student_profile
    app = get_object_or_404(NoDuesApplication, application_no=app_no, student=student)
    clearances = app.department_clearances.select_related('department', 'reviewed_by').order_by('department__display_order')
    logs = app.logs.select_related('department', 'actor').order_by('-timestamp')

    context = {
        'application': app,
        'clearances': clearances,
        'logs': logs,
        'student': student,
    }
    return render(request, 'clearance/student/application_detail.html', context)


@student_required
def student_applications_list(request):
    """
    List of all applications submitted by the logged-in student.
    """
    student = request.user.student_profile
    applications = student.applications.all()
    return render(request, 'clearance/student/applications_list.html', {'applications': applications, 'student': student})


@login_required
def download_certificate_pdf(request, app_no):
    """
    Secure download endpoint for the official No Dues Certificate PDF.
    Accessible by student owner, department staff, or admin.
    """
    app = get_object_or_404(NoDuesApplication, application_no=app_no)

    # Permission check
    if not (request.user.is_university_admin or request.user.is_department_staff or (request.user.is_student and app.student.user == request.user)):
        raise Http404("You do not have permission to view this certificate.")

    if not app.is_completed:
        messages.error(request, "The No Dues certificate is only generated after all mandatory departments have cleared the application.")
        return redirect('student_application_detail', app_no=app_no)

    cert = getattr(app, 'certificate', None)
    if not cert:
        cert = app.generate_or_update_certificate()

    # Re-generate if PDF doesn't exist on disk
    if not cert.pdf_file or not os.path.exists(cert.pdf_file.path):
        generate_certificate_pdf(cert)

    response = FileResponse(open(cert.pdf_file.path, 'rb'), content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="NoDuesCertificate_{cert.certificate_no}.pdf"'
    return response


# -------------------------------------------------------------
# DEPARTMENT STAFF PORTAL VIEWS
# -------------------------------------------------------------

@staff_required
def department_dashboard(request):
    """
    Department Staff Dashboard showing department KPIs, pending student verifications, and recent actions.
    """
    user = request.user
    if user.is_department_staff:
        staff_profile = user.staff_profile
        department = staff_profile.department
    else: # admin viewing staff dashboard
        department = Department.objects.first()
        staff_profile = None

    if not department:
        messages.error(request, "No department configured.")
        return redirect('admin_dashboard')

    # Department Clearances
    dept_clearances = department.clearances.select_related('application__student__user', 'reviewed_by').all()
    
    total_assigned = dept_clearances.count()
    pending_count = dept_clearances.filter(status=DepartmentClearance.STATUS_PENDING).count()
    action_req_count = dept_clearances.filter(status=DepartmentClearance.STATUS_ACTION_REQUIRED).count()
    on_hold_count = dept_clearances.filter(status=DepartmentClearance.STATUS_ON_HOLD).count()
    rejected_count = dept_clearances.filter(status=DepartmentClearance.STATUS_REJECTED).count()
    approved_count = dept_clearances.filter(status=DepartmentClearance.STATUS_APPROVED).count()

    recent_pending = dept_clearances.filter(status=DepartmentClearance.STATUS_PENDING).order_by('-application__submitted_at')[:10]

    context = {
        'department': department,
        'staff_profile': staff_profile,
        'total_assigned': total_assigned,
        'pending_count': pending_count,
        'action_req_count': action_req_count,
        'on_hold_count': on_hold_count,
        'rejected_count': rejected_count,
        'approved_count': approved_count,
        'recent_pending': recent_pending,
    }
    return render(request, 'clearance/department/dashboard.html', context)


@staff_required
def department_applications_list(request):
    """
    Searchable, filterable list of clearance requests for this staff member's department.
    """
    user = request.user
    if user.is_department_staff:
        department = user.staff_profile.department
    else:
        dept_id = request.GET.get('dept_id')
        if dept_id:
            department = get_object_or_404(Department, id=dept_id)
        else:
            department = Department.objects.first()

    tab = request.GET.get('tab', 'pending') # 'pending', 'action_required', 'on_hold', 'rejected', 'approved', 'all'
    search_query = request.GET.get('q', '').strip()

    qs = department.clearances.select_related('application__student__user', 'reviewed_by').order_by('-application__submitted_at')

    if tab == 'pending':
        qs = qs.filter(status=DepartmentClearance.STATUS_PENDING)
    elif tab == 'action_required':
        qs = qs.filter(status=DepartmentClearance.STATUS_ACTION_REQUIRED)
    elif tab == 'on_hold':
        qs = qs.filter(status=DepartmentClearance.STATUS_ON_HOLD)
    elif tab == 'rejected':
        qs = qs.filter(status=DepartmentClearance.STATUS_REJECTED)
    elif tab == 'approved':
        qs = qs.filter(status=DepartmentClearance.STATUS_APPROVED)

    if search_query:
        qs = qs.filter(
            Q(application__application_no__icontains=search_query) |
            Q(application__student__roll_number__icontains=search_query) |
            Q(application__student__registration_number__icontains=search_query) |
            Q(application__student__user__first_name__icontains=search_query) |
            Q(application__student__user__last_name__icontains=search_query)
        )

    # Counts for tab badges
    base_qs = department.clearances
    counts = {
        'all': base_qs.count(),
        'pending': base_qs.filter(status=DepartmentClearance.STATUS_PENDING).count(),
        'action_required': base_qs.filter(status=DepartmentClearance.STATUS_ACTION_REQUIRED).count(),
        'on_hold': base_qs.filter(status=DepartmentClearance.STATUS_ON_HOLD).count(),
        'rejected': base_qs.filter(status=DepartmentClearance.STATUS_REJECTED).count(),
        'approved': base_qs.filter(status=DepartmentClearance.STATUS_APPROVED).count(),
    }

    context = {
        'department': department,
        'clearances': qs,
        'current_tab': tab,
        'search_query': search_query,
        'counts': counts,
    }
    return render(request, 'clearance/department/applications_list.html', context)


@staff_required
def department_review_clearance(request, clearance_id):
    """
    Department Staff Review Action Page & Modal handler.
    Staff can:
    1. Approve clearance (NIL dues)
    2. Mark pending dues with exact amount & breakdown
    3. Put on hold with justification
    4. Reject with mandatory explanation
    """
    clearance = get_object_or_404(DepartmentClearance.objects.select_related('application__student__user', 'department'), id=clearance_id)
    department = clearance.department

    # Verify authorization
    if request.user.is_department_staff:
        if request.user.staff_profile.department != department:
            messages.error(request, "You are not authorized to review applications for other departments.")
            return redirect('department_dashboard')

    application = clearance.application
    student = application.student

    if request.method == 'POST':
        action = request.POST.get('action') # 'APPROVE', 'ACTION_REQUIRED', 'ON_HOLD', 'REJECT'
        dues_amount_str = request.POST.get('dues_amount', '0.00').strip()
        dues_breakdown = request.POST.get('dues_breakdown', '').strip()
        remarks = request.POST.get('remarks', '').strip()
        internal_notes = request.POST.get('internal_notes', '').strip()

        try:
            dues_amount = Decimal(dues_amount_str) if dues_amount_str else Decimal('0.00')
            if dues_amount < Decimal('0.00'):
                dues_amount = Decimal('0.00')
        except Exception:
            dues_amount = Decimal('0.00')

        prev_status = clearance.status

        if action == 'APPROVE':
            clearance.status = DepartmentClearance.STATUS_APPROVED
            clearance.dues_amount = Decimal('0.00')
            clearance.dues_breakdown = ""
            clearance.remarks = remarks or "All departmental obligations cleared. No dues pending."
            msg_title = f"{department.name}: Clearance Approved ✓"
            msg_body = f"{department.name} has approved your No Dues clearance. Remarks: {clearance.remarks}"
        elif action == 'ACTION_REQUIRED':
            if dues_amount == Decimal('0.00') and not remarks:
                messages.error(request, "Please specify the pending dues amount or describe the action required by the student.")
                return redirect('department_review_clearance', clearance_id=clearance.id)
            clearance.status = DepartmentClearance.STATUS_ACTION_REQUIRED
            clearance.dues_amount = dues_amount
            clearance.dues_breakdown = dues_breakdown
            clearance.remarks = remarks or f"Outstanding dues of ₹{dues_amount} required to be cleared."
            msg_title = f"{department.name}: Action Required / Dues Flagged ⚠️"
            msg_body = f"{department.name} flagged dues of ₹{dues_amount}. Details: {clearance.remarks}"
        elif action == 'ON_HOLD':
            if not remarks:
                messages.error(request, "A remark explaining why the application is placed on hold is required.")
                return redirect('department_review_clearance', clearance_id=clearance.id)
            clearance.status = DepartmentClearance.STATUS_ON_HOLD
            clearance.remarks = remarks
            msg_title = f"{department.name}: Clearance Placed On Hold ⏳"
            msg_body = f"{department.name} placed your clearance on hold. Reason: {remarks}"
        elif action == 'REJECT':
            if not remarks:
                messages.error(request, "A mandatory rejection reason must be provided.")
                return redirect('department_review_clearance', clearance_id=clearance.id)
            clearance.status = DepartmentClearance.STATUS_REJECTED
            clearance.remarks = remarks
            msg_title = f"{department.name}: Clearance Rejected ❌"
            msg_body = f"{department.name} has rejected clearance. Explanation: {remarks}"
        else:
            messages.error(request, "Invalid action selected.")
            return redirect('department_review_clearance', clearance_id=clearance.id)

        clearance.internal_notes = internal_notes
        clearance.reviewed_by = request.user
        clearance.reviewed_at = timezone.now()
        clearance.save()

        # Recalculate overall status & trigger certificate if all approved
        application.recalculate_status(save=True)

        # Audit log
        ClearanceLog.objects.create(
            application=application,
            department=department,
            actor=request.user,
            action=f"STAFF_{action}",
            previous_status=prev_status,
            new_status=clearance.status,
            dues_amount=clearance.dues_amount,
            remarks=clearance.remarks
        )

        # Notify student
        Notification.objects.create(
            recipient=student.user,
            title=msg_title,
            message=msg_body,
            link=f"/student/application/{application.application_no}/"
        )

        messages.success(request, f"Updated clearance for {student.roll_number} ({student.user.get_full_name() or student.user.username}) to '{clearance.get_status_display()}'.")
        return redirect('department_applications')

    # History logs for this application & department
    logs = application.logs.filter(department=department).order_by('-timestamp')

    context = {
        'clearance': clearance,
        'department': department,
        'application': application,
        'student': student,
        'logs': logs,
    }
    return render(request, 'clearance/department/review_modal.html', context)


# -------------------------------------------------------------
# ADMINISTRATOR PORTAL VIEWS
# -------------------------------------------------------------

@admin_required
def admin_dashboard(request):
    """
    University Admin Master Dashboard.
    Visual KPI summary, clearance bottlenecks, department breakdown, recent activity.
    """
    total_apps = NoDuesApplication.objects.count()
    completed_apps = NoDuesApplication.objects.filter(overall_status=NoDuesApplication.STATUS_COMPLETED).count()
    in_progress_apps = NoDuesApplication.objects.filter(overall_status__in=[NoDuesApplication.STATUS_IN_PROGRESS, NoDuesApplication.STATUS_SUBMITTED]).count()
    action_req_apps = NoDuesApplication.objects.filter(overall_status=NoDuesApplication.STATUS_ACTION_REQUIRED).count()
    on_hold_apps = NoDuesApplication.objects.filter(overall_status=NoDuesApplication.STATUS_ON_HOLD).count()
    rejected_apps = NoDuesApplication.objects.filter(overall_status=NoDuesApplication.STATUS_REJECTED).count()

    total_pending_dues = DepartmentClearance.objects.aggregate(total=Sum('dues_amount'))['total'] or Decimal('0.00')

    departments = Department.objects.annotate(
        assigned_count=Count('clearances'),
        approved_count=Count('clearances', filter=Q(clearances__status=DepartmentClearance.STATUS_APPROVED)),
        pending_count=Count('clearances', filter=Q(clearances__status=DepartmentClearance.STATUS_PENDING)),
        action_count=Count('clearances', filter=Q(clearances__status=DepartmentClearance.STATUS_ACTION_REQUIRED)),
        hold_count=Count('clearances', filter=Q(clearances__status=DepartmentClearance.STATUS_ON_HOLD)),
        reject_count=Count('clearances', filter=Q(clearances__status=DepartmentClearance.STATUS_REJECTED)),
    ).order_by('display_order')

    recent_logs = ClearanceLog.objects.select_related('application__student__user', 'department', 'actor').order_by('-timestamp')[:15]
    recent_applications = NoDuesApplication.objects.select_related('student__user').order_by('-submitted_at')[:8]

    # Chart data calculations
    chart_dept_labels = [d.name for d in departments]
    chart_dept_approved = [d.approved_count for d in departments]
    chart_dept_pending = [d.pending_count + d.action_count for d in departments]

    context = {
        'total_apps': total_apps,
        'completed_apps': completed_apps,
        'in_progress_apps': in_progress_apps,
        'action_req_apps': action_req_apps,
        'on_hold_apps': on_hold_apps,
        'rejected_apps': rejected_apps,
        'total_pending_dues': total_pending_dues,
        'departments': departments,
        'recent_logs': recent_logs,
        'recent_applications': recent_applications,
        'chart_dept_labels': chart_dept_labels,
        'chart_dept_approved': chart_dept_approved,
        'chart_dept_pending': chart_dept_pending,
    }
    return render(request, 'clearance/admin_portal/dashboard.html', context)


@admin_required
def admin_applications_list(request):
    """
    University-wide application management with comprehensive filtering.
    """
    status_filter = request.GET.get('status', '')
    purpose_filter = request.GET.get('purpose', '')
    search_query = request.GET.get('q', '').strip()

    qs = NoDuesApplication.objects.select_related('student__user').order_by('-submitted_at')

    if status_filter:
        qs = qs.filter(overall_status=status_filter)
    if purpose_filter:
        qs = qs.filter(purpose=purpose_filter)
    if search_query:
        qs = qs.filter(
            Q(application_no__icontains=search_query) |
            Q(student__roll_number__icontains=search_query) |
            Q(student__registration_number__icontains=search_query) |
            Q(student__user__first_name__icontains=search_query) |
            Q(student__user__last_name__icontains=search_query)
        )

    context = {
        'applications': qs,
        'status_filter': status_filter,
        'purpose_filter': purpose_filter,
        'search_query': search_query,
        'status_choices': NoDuesApplication.STATUS_CHOICES,
        'purpose_choices': NoDuesApplication.PURPOSE_CHOICES,
    }
    return render(request, 'clearance/admin_portal/applications_list.html', context)


@admin_required
def admin_application_detail(request, app_no):
    """
    Full Administrative view of a student's No Dues application, with department breakdown
    and Admin Override capability.
    """
    app = get_object_or_404(NoDuesApplication.objects.select_related('student__user'), application_no=app_no)
    clearances = app.department_clearances.select_related('department', 'reviewed_by').order_by('department__display_order')
    logs = app.logs.select_related('department', 'actor').order_by('-timestamp')

    if request.method == 'POST' and 'admin_action' in request.POST:
        action = request.POST.get('admin_action')
        admin_remarks = request.POST.get('admin_remarks', '').strip()

        if action == 'FORCE_APPROVE_ALL':
            for c in clearances:
                c.status = DepartmentClearance.STATUS_APPROVED
                c.dues_amount = Decimal('0.00')
                c.remarks = f"Admin Expedited Approval: {admin_remarks or 'Approved under Dean / Registrar authority'}"
                c.reviewed_by = request.user
                c.reviewed_at = timezone.now()
                c.save()

            app.recalculate_status(save=True)
            ClearanceLog.objects.create(
                application=app,
                actor=request.user,
                action="ADMIN_FORCE_APPROVE_ALL",
                new_status=NoDuesApplication.STATUS_COMPLETED,
                remarks=admin_remarks or "All departments approved by Admin Override"
            )
            messages.success(request, f"Admin Override: Application {app.application_no} marked fully completed!")
            return redirect('admin_application_detail', app_no=app.application_no)

    context = {
        'application': app,
        'student': app.student,
        'clearances': clearances,
        'logs': logs,
    }
    return render(request, 'clearance/admin_portal/application_detail.html', context)


@admin_required
def admin_departments_list(request):
    """
    Manage university departments.
    """
    departments = Department.objects.all().order_by('display_order')

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        code = request.POST.get('code', '').strip().upper()
        icon = request.POST.get('icon', 'bi-building').strip()
        location = request.POST.get('location', '').strip()
        is_mandatory = 'is_mandatory' in request.POST
        display_order = int(request.POST.get('display_order', 0))

        if name and code:
            Department.objects.create(
                name=name,
                code=code,
                icon=icon,
                location=location,
                is_mandatory=is_mandatory,
                display_order=display_order,
                is_active=True
            )
            messages.success(request, f"Department '{name}' created successfully.")
            return redirect('admin_departments')
        else:
            messages.error(request, "Name and code are required.")

    return render(request, 'clearance/admin_portal/departments_list.html', {'departments': departments})


@admin_required
def admin_staff_list(request):
    """
    Manage department staff assignments.
    """
    staff_members = StaffProfile.objects.select_related('user', 'department').all().order_by('department__name')
    departments = Department.objects.filter(is_active=True).order_by('name')

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '').strip()
        dept_id = request.POST.get('department_id')
        employee_id = request.POST.get('employee_id', '').strip()
        designation = request.POST.get('designation', '').strip()

        if username and password and dept_id and employee_id:
            dept = get_object_or_404(Department, id=dept_id)
            user = CustomUser.objects.create_user(
                username=username,
                password=password,
                email=email,
                first_name=first_name,
                last_name=last_name,
                role=CustomUser.ROLE_STAFF,
                is_staff=True
            )
            StaffProfile.objects.create(
                user=user,
                department=dept,
                employee_id=employee_id,
                designation=designation or "Clearance Officer"
            )
            messages.success(request, f"Staff account for {user.get_full_name() or user.username} assigned to {dept.name}.")
            return redirect('admin_staff')
        else:
            messages.error(request, "Please fill in all required fields.")

    context = {
        'staff_members': staff_members,
        'departments': departments,
    }
    return render(request, 'clearance/admin_portal/staff_list.html', context)


@admin_required
def admin_students_list(request):
    """
    View all registered students in the system.
    """
    search_query = request.GET.get('q', '').strip()
    students = StudentProfile.objects.select_related('user').order_by('-created_at')

    if search_query:
        students = students.filter(
            Q(roll_number__icontains=search_query) |
            Q(registration_number__icontains=search_query) |
            Q(user__first_name__icontains=search_query) |
            Q(user__last_name__icontains=search_query) |
            Q(course__icontains=search_query)
        )

    return render(request, 'clearance/admin_portal/students_list.html', {'students': students, 'search_query': search_query})


@admin_required
def admin_certificates_registry(request):
    """
    Master registry of all issued No Dues certificates with verification status.
    """
    certificates = NoDuesCertificate.objects.select_related('student__user', 'application').order_by('-issue_date')
    return render(request, 'clearance/admin_portal/certificates_registry.html', {'certificates': certificates})


@admin_required
def admin_export_reports_csv(request):
    """
    Export clearance data to CSV for university academic affairs and convocation auditing.
    """
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="University_No_Dues_Report_{timezone.now().strftime("%Y%m%d_%H%M")}.csv"'

    writer = csv.writer(response)
    writer.writerow([
        'Application No', 'Roll Number', 'Registration No', 'Student Name',
        'Course', 'Branch', 'Batch Year', 'Purpose', 'Status',
        'Total Pending Dues (INR)', 'Submitted Date', 'Completed Date', 'Certificate No'
    ])

    apps = NoDuesApplication.objects.select_related('student__user', 'certificate').all().order_by('-submitted_at')
    for a in apps:
        cert_no = a.certificate.certificate_no if hasattr(a, 'certificate') else 'N/A'
        writer.writerow([
            a.application_no,
            a.student.roll_number,
            a.student.registration_number,
            a.student.user.get_full_name() or a.student.user.username,
            a.student.course,
            a.student.branch,
            a.student.batch_year,
            a.get_purpose_display(),
            a.get_overall_status_display(),
            str(a.total_dues_amount),
            a.submitted_at.strftime('%Y-%m-%d %H:%M'),
            a.completed_at.strftime('%Y-%m-%d %H:%M') if a.completed_at else 'In Progress',
            cert_no
        ])

    return response


@login_required
def mark_notification_read(request, notification_id):
    """
    Mark a notification as read.
    """
    notif = get_object_or_404(Notification, id=notification_id, recipient=request.user)
    notif.is_read = True
    notif.save()
    if notif.link:
        return redirect(notif.link)
    return redirect('dashboard_redirect')
