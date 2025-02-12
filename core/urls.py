from django.urls import path
from django.contrib.auth.views import LogoutView
from . import views
from .views import (
  ProgramChairDashboardView, unlock_permit_view, ProgramChairStudentsView, 
  print_permit, ManageStudentsView, GenerateReportsView, generate_report
)



urlpatterns = [
  path('', views.home, name='home'),  # Your home view
  path('register/', views.register_view, name='register'),
  path('login/', views.login_view, name='login'),
  path('logout/', LogoutView.as_view(next_page='home'), name='logout'),
  path('student-dashboard/', views.student_dashboard, name='student_dashboard'),
  path('update/<int:request_id>/', views.update_clearance_request, name='update_clearance_request'),
  path('student/requests/', views.create_clearance_requests, name='clearance_requests'),
  path('student/profile/', views.student_profile, name='student_profile'),
  path('student/clearance-status/', views.clearance_status, name='clearance_status'),
  path('office/dashboard/', views.office_dashboard, name='office_dashboard'),
  path('office/profile/', views.office_profile, name='office_profile'),
  path('office/settings/', views.office_settings, name='office_settings'),
  path('program-chair/dashboard/', ProgramChairDashboardView.as_view(), name='program_chair_dashboard'),
  path('program-chair/unlock/<int:clearance_id>/', unlock_permit_view, name='unlock_permit'),
  path('program-chair/students/', ProgramChairStudentsView.as_view(), name='program_chair_students'),
  path('program-chair/manage-students/', ManageStudentsView.as_view(), name='manage_students'),
  path('program-chair/generate-reports/', GenerateReportsView.as_view(), name='generate_reports'),
  path('program-chair/student/<int:student_id>/', views.student_detail, name='student_detail'),
  path('re_request/<int:request_id>/', views.re_request_clearance, name='re_request_clearance'),
  path('print-permit/<int:clearance_id>/', views.print_permit, name='print_permit'),
  path('bh-owner-dashboard/', views.bh_owner_dashboard, name='bh_owner_dashboard'),
  path('payment-dashboard/', views.payment_dashboard, name='payment_dashboard'),
  path('update-payment/<int:payment_id>/', views.update_payment, name='update_payment'),

  # Admin URLs
  path('dashboard/', views.admin_dashboard, name='admin_dashboard'),
  path('dashboard/users/', views.admin_users, name='admin_users'),
  path('dashboard/users/create/', views.admin_create_user, name='admin_create_user'),
  path('dashboard/users/edit/<int:user_id>/', views.admin_edit_user, name='admin_edit_user'),
  path('dashboard/offices/', views.admin_offices, name='admin_offices'),
  path('dashboard/clearances/', views.admin_clearances, name='admin_clearances'),
  
  # Admin approval URLs
  path('approve-user/<int:user_id>/', views.approve_user, name='approve_user'),
  path('reject-user/<int:user_id>/', views.reject_user, name='reject_user'),
  path('generate-report/', generate_report, name='generate_report'),
]

