from django.urls import path
from . import views
from .views import ManageStudentsView

urlpatterns = [
    path('', views.home, name='home'),
    path('profile/', views.student_profile, name='student_profile'),
    path('student/dashboard/', views.student_dashboard, name='student_dashboard'),
    path('dashboard/admin/', views.admin_dashboard, name='admin_dashboard'),
    path('dashboard/admin/users/', views.admin_users, name='admin_users'),
    path('dashboard/admin/offices/', views.admin_offices, name='admin_offices'),
    path('dashboard/admin/clearances/', views.admin_clearances, name='admin_clearances'),
    path('dashboard/admin/deans/', views.admin_deans, name='admin_deans'),
    path('dashboard/admin/courses/', views.admin_courses, name='admin_courses'),
    path('dashboard/manage-students/', ManageStudentsView.as_view(), name='manage_students'),
    path('clearance/<int:clearance_id>/delete/', views.delete_clearance, name='delete_clearance'),
    path('clearance-request/<int:request_id>/update/', views.update_clearance_request, name='update_clearance_request'),
    path('logout/', views.user_logout, name='logout'),
    path('dashboard/create/users/', views.create_user, name='create_user'),
    path('login/', views.user_login, name='login'),
    path('register/', views.register, name='register'),

]







































