from django.urls import path
from django.contrib.auth.views import LogoutView
from . import views
from .views import ProgramChairDashboardView, unlock_permit_view, ProgramChairStudentsView, print_permit



urlpatterns = [
  path('', views.home, name='home'),  # Your home view
  path('dashboard/', views.dashboard, name='dashboard'),  # Add this line
  path('register/', views.register_view, name='register'),
  path('login/', views.login_view, name='login'),
  path('logout/', LogoutView.as_view(next_page='home'), name='logout'),
  path('student-dashboard/', views.student_dashboard, name='student_dashboard'),
  path('update/<int:request_id>/', views.update_clearance_request, name='update_clearance_request'),
  path('student/requests/', views.create_clearance_requests, name='clearance_requests'),
  path('office/dashboard/', views.office_dashboard, name='office_dashboard'),
  path('office/profile/', views.office_profile, name='office_profile'),
  path('office/settings/', views.office_settings, name='office_settings'),
  path('program-chair/dashboard/', ProgramChairDashboardView.as_view(), name='program_chair_dashboard'),
  path('program-chair/unlock/<int:clearance_id>/', unlock_permit_view, name='unlock_permit'),
  path('program-chair/students/', ProgramChairStudentsView.as_view(), name='program_chair_students'),
  path('re_request/<int:request_id>/', views.re_request_clearance, name='re_request_clearance'),
  path('print-permit/<int:clearance_id>/', views.print_permit, name='print_permit'),
  path('bh-owner-dashboard/', views.bh_owner_dashboard, name='bh_owner_dashboard'),
]

