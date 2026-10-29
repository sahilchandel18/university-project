from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.custom_login_view, name='login'),
    path('demo-login/<str:role_key>/', views.quick_demo_login, name='quick_demo_login'),
    path('register/', views.student_register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard-redirect/', views.dashboard_redirect_view, name='dashboard_redirect'),
    path('profile/', views.profile_view, name='profile'),
]
