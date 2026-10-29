from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_POST
from .models import CustomUser, StudentProfile, StaffProfile
from .forms import StudentRegistrationForm, StudentProfileUpdateForm

def custom_login_view(request):
    """
    Login page with university branding and one-click demo credentials.
    """
    if request.user.is_authenticated:
        return redirect('dashboard_redirect')

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '').strip()

        user = authenticate(request, username=username, password=password)
        if user is not None:
            if user.is_active:
                login(request, user)
                messages.success(request, f"Welcome back, {user.get_full_name() or user.username}!")
                return redirect('dashboard_redirect')
            else:
                messages.error(request, "Your account has been deactivated. Please contact the administrator.")
        else:
            messages.error(request, "Invalid username or password. Please try again.")

    return render(request, 'accounts/login.html')


def quick_demo_login(request, role_key):
    """
    1-Click Demo Login Switcher designed specifically for viva/professor evaluation.
    Logs into pre-seeded demo accounts instantly without manual typing.
    """
    user_mapping = {
        'admin': 'admin',
        'student_completed': 'student_aarav',
        'student_in_progress': 'student_priya',
        'student_with_dues': 'student_rohan',
        'student_new': 'student_ananya',
        'staff_library': 'staff_library',
        'staff_accounts': 'staff_accounts',
        'staff_hostel': 'staff_hostel',
        'staff_lab': 'staff_lab',
        'staff_sports': 'staff_sports',
        'staff_tp': 'staff_tp',
    }

    target_username = user_mapping.get(role_key)
    if not target_username:
        messages.error(request, "Demo profile not recognized.")
        return redirect('login')

    try:
        user = CustomUser.objects.get(username=target_username)
        # Login directly
        login(request, user, backend='django.contrib.auth.backends.ModelBackend')
        messages.success(request, f"Demo mode active: Signed in as {user.get_full_name() or user.username} ({user.get_role_display()})")
        return redirect('dashboard_redirect')
    except CustomUser.DoesNotExist:
        messages.error(request, f"Demo user '{target_username}' not found. Please run 'python manage.py seed_data' first.")
        return redirect('login')


def student_register_view(request):
    """
    Self-service student registration.
    """
    if request.user.is_authenticated:
        return redirect('dashboard_redirect')

    if request.method == 'POST':
        form = StudentRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            messages.success(request, f"Registration successful! Welcome to the University No Dues Portal, {user.first_name}.")
            return redirect('student_dashboard')
        else:
            messages.error(request, "Please correct the errors indicated below.")
    else:
        form = StudentRegistrationForm()

    return render(request, 'accounts/register.html', {'form': form})


@login_required
def dashboard_redirect_view(request):
    """
    Role-based dispatcher routing users to their designated portal.
    """
    user = request.user
    if user.is_university_admin:
        return redirect('admin_dashboard')
    elif user.is_department_staff:
        return redirect('department_dashboard')
    elif user.is_student:
        return redirect('student_dashboard')
    else:
        return redirect('login')


def logout_view(request):
    """
    Logs out the user and clears session.
    """
    logout(request)
    messages.info(request, "You have been logged out securely.")
    return redirect('login')


@login_required
def profile_view(request):
    """
    Student or Staff profile view and edit.
    """
    user = request.user
    student_profile = getattr(user, 'student_profile', None)
    staff_profile = getattr(user, 'staff_profile', None)

    if request.method == 'POST' and student_profile:
        form = StudentProfileUpdateForm(request.POST, instance=student_profile)
        if form.is_valid():
            form.save()
            user.first_name = request.POST.get('first_name', user.first_name)
            user.last_name = request.POST.get('last_name', user.last_name)
            user.email = request.POST.get('email', user.email)
            user.phone_number = request.POST.get('phone_number', user.phone_number)
            user.save()
            messages.success(request, "Profile updated successfully.")
            return redirect('profile')
    else:
        form = StudentProfileUpdateForm(instance=student_profile) if student_profile else None

    context = {
        'student_profile': student_profile,
        'staff_profile': staff_profile,
        'form': form,
    }
    return render(request, 'accounts/profile.html', context)
