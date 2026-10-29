from django.urls import path
from . import views

urlpatterns = [
    # Public & Verification
    path('', views.landing_page, name='landing_page'),
    path('verify/', views.public_verify_certificate, name='verify_certificate_query'),
    path('verify/<uuid:verification_uuid>/', views.public_verify_certificate, name='verify_certificate'),

    # Student Portal
    path('student/dashboard/', views.student_dashboard, name='student_dashboard'),
    path('student/apply/', views.student_apply, name='student_apply'),
    path('student/application/<str:app_no>/', views.student_application_detail, name='student_application_detail'),
    path('student/applications/', views.student_applications_list, name='student_applications_list'),
    path('student/certificate/<str:app_no>/', views.download_certificate_pdf, name='download_certificate_pdf'),

    # Department Staff Portal
    path('department/dashboard/', views.department_dashboard, name='department_dashboard'),
    path('department/applications/', views.department_applications_list, name='department_applications'),
    path('department/review/<int:clearance_id>/', views.department_review_clearance, name='department_review_clearance'),

    # Administrator Portal
    path('admin-portal/dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('admin-portal/applications/', views.admin_applications_list, name='admin_applications'),
    path('admin-portal/application/<str:app_no>/', views.admin_application_detail, name='admin_application_detail'),
    path('admin-portal/departments/', views.admin_departments_list, name='admin_departments'),
    path('admin-portal/staff/', views.admin_staff_list, name='admin_staff'),
    path('admin-portal/students/', views.admin_students_list, name='admin_students'),
    path('admin-portal/certificates/', views.admin_certificates_registry, name='admin_certificates'),
    path('admin-portal/reports/csv/', views.admin_export_reports_csv, name='admin_export_reports_csv'),

    # Notifications
    path('notifications/read/<int:notification_id>/', views.mark_notification_read, name='mark_notification_read'),
]
