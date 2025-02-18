from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.utils import timezone
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.views.generic import TemplateView, ListView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.http import HttpResponse, JsonResponse
from django.template.loader import render_to_string
from datetime import datetime
from io import BytesIO
import os
from django.conf import settings
from django.core.files.storage import default_storage

# PDF Generation
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch

# Excel Generation
from openpyxl import Workbook

# Local imports
from core.models import (
    ClearanceRequest, Clearance, Staff, Student, 
    Office, ProgramChair, User, Dean, Course,
    SEMESTER_CHOICES
)

# Basic Views

def user_logout(request):
    logout(request)
    return redirect('login')
def home(request):
    if request.user.is_authenticated:
        if hasattr(request.user, 'student'):
            return redirect('student_dashboard')
        elif hasattr(request.user, 'staff'):
            return redirect('staff_dashboard')
        elif request.user.is_superuser:
            return redirect('admin_dashboard')
    return render(request, 'home.html')

def user_login(request):
    if request.user.is_authenticated:
        if hasattr(request.user, 'student'):
            return redirect('student_dashboard')
        elif hasattr(request.user, 'staff'):
            return redirect('staff_dashboard')
        elif request.user.is_superuser:
            return redirect('admin_dashboard')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            if not user.is_active:
                messages.error(request, 'Your account is not yet approved. Please wait for admin approval.')
                return redirect('login')
            
            login(request, user)
            
            # Redirect based on user type
            if hasattr(user, 'student'):
                return redirect('student_dashboard')
            elif hasattr(user, 'staff'):
                return redirect('staff_dashboard')
            elif user.is_superuser:
                return redirect('admin_dashboard')
        else:
            messages.error(request, 'Invalid username or password.')
    
    return render(request, 'registration/login.html')

def register(request):
    if request.user.is_authenticated:
        return redirect('home')
    
    context = {
        'program_chairs': ProgramChair.objects.all(),
        'dormitory_owners': Staff.objects.filter(is_dormitory_owner=True)
    }
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        email = request.POST.get('email')
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        student_id = request.POST.get('student_id')
        program_chair_id = request.POST.get('program_chair')
        course_code = request.POST.get('course')
        year_level = request.POST.get('year_level')
        is_boarder = request.POST.get('is_boarder') == 'on'
        dormitory_owner_id = request.POST.get('dormitory_owner')
        
        if User.objects.filter(username=username).exists():
            messages.error(request, 'Username already exists.')
            return redirect('register')
            
        if User.objects.filter(email=email).exists():
            messages.error(request, 'Email already exists.')
            return redirect('register')
            
        try:
            # Create inactive user (pending approval)
            user = User.objects.create_user(
                username=username,
                password=password,
                email=email,
                first_name=first_name,
                last_name=last_name,
                is_active=False
            )
            
            # Get related objects
            program_chair = ProgramChair.objects.get(id=program_chair_id)
            course = Course.objects.get(code=course_code)
            dormitory_owner = Staff.objects.get(id=dormitory_owner_id) if is_boarder and dormitory_owner_id else None
            
            # Create student profile
            student = Student.objects.create(
                user=user,
                student_id=student_id,
                course=course,
                year_level=year_level,
                is_boarder=is_boarder,
                program_chair=program_chair,
                dormitory_owner=dormitory_owner
            )
            
            messages.success(request, 'Registration successful! Please wait for admin approval.')
            return redirect('login')
            
        except Exception as e:
            if user:
                user.delete()
            messages.error(request, f'Registration failed: {str(e)}')
            return redirect('register')
    
    return render(request, 'registration/register.html', context)

@login_required
def student_dashboard(request):
    try:
        student = request.user.student
        clearances = Clearance.objects.filter(student=student).order_by('-school_year', '-semester')
        
        context = {
            'student_info': student,
            'clearances': clearances,
        }
        return render(request, 'core/student_dashboard.html', context)
    except Student.DoesNotExist:
        messages.error(request, "Student profile not found.")
        return redirect('home')

@login_required
def student_profile(request):
    """
    Display and manage student profile information.
    """
    try:
        student = request.user.student
        return render(request, 'core/student_profile.html', {
            'student': student
        })
    except Student.DoesNotExist:
        messages.error(request, "Student profile not found.")
        return redirect('home')

@login_required
def delete_clearance(request, clearance_id):
    clearance = get_object_or_404(Clearance, id=clearance_id)
    if request.method == 'POST':
        clearance.delete()
        messages.success(request, 'Clearance deleted successfully.')
    return redirect('program_chair_dashboard')

@login_required
def update_clearance_request(request, request_id):
    """
    Allows a staff member to approve or deny a clearance request.
    For dormitory clearances, ensures only the assigned dormitory owner can approve/deny.
    """
    clearance_request = get_object_or_404(ClearanceRequest, pk=request_id)
    
    try:
        staff_member = request.user.staff
        
        # Special handling for dormitory clearances
        if clearance_request.office.name == 'Dormitory':
            if not staff_member.is_dormitory_owner:
                messages.error(request, "Only dormitory owners can handle dormitory clearances.")
                return redirect('office_dashboard')
            if clearance_request.student.dormitory_owner != staff_member:
                messages.error(request, "You can only handle clearances for your assigned students.")
                return redirect('office_dashboard')
    except Staff.DoesNotExist:
        messages.error(request, "Staff access required.")
        return redirect('login')

    if request.method == 'POST':
        new_status = request.POST.get('status')
        remarks = request.POST.get('remarks', '')
        
        try:
            if new_status == 'approved':
                clearance_request.approve(staff_member)
            elif new_status == 'denied':
                clearance_request.deny(staff_member, remarks)
            
            # Check overall clearance status
            clearance = getattr(clearance_request.student, 'clearance', None)
            if clearance:
                clearance.check_clearance()
                
            messages.success(request, f"Clearance request {new_status} successfully.")

        except Exception as e:
            messages.error(request, f"Error processing request: {str(e)}")
            return redirect('office_dashboard')

    return redirect('office_dashboard')

# Class-based Views
class ManageStudentsView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    model = Student
    template_name = 'core/manage_students.html'
    context_object_name = 'students'
    
    def test_func(self):
        return self.request.user.is_superuser
    
    def get_queryset(self):
        return Student.objects.select_related(
            'user', 
            'course', 
            'program_chair', 
            'dormitory_owner'
        ).all()
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['courses'] = Course.objects.all()
        context['program_chairs'] = ProgramChair.objects.all()
        context['dormitory_owners'] = Staff.objects.filter(is_dormitory_owner=True)
        return context

@login_required
@user_passes_test(lambda u: u.is_superuser)
def admin_deans(request):
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'add':
            name = request.POST.get('name')
            description = request.POST.get('description')
            
            Dean.objects.create(
                name=name,
                description=description
            )
            messages.success(request, f'Dean {name} added successfully.')
        elif action == 'delete':
            dean_id = request.POST.get('dean_id')
            try:
                dean = Dean.objects.get(id=dean_id)
                dean.delete()
                messages.success(request, f'Dean {dean.name} deleted successfully.')
            except Dean.DoesNotExist:
                messages.error(request, 'Dean not found.')
            
    deans = Dean.objects.all()
    return render(request, 'admin/deans.html', {'deans': deans})

@login_required
@user_passes_test(lambda u: u.is_superuser)
def admin_dashboard(request):
    context = {
         'total_students': Student.objects.count(),
         'total_offices': Office.objects.count(),
         'total_staff': Staff.objects.count(),
         'total_program_chairs': ProgramChair.objects.count(),
         'courses_count': Course.objects.count(),
         'total_deans': Dean.objects.count(),
         # Add more context variables as needed.
    }
    return render(request, 'admin/dashboard.html', context)

@login_required
@user_passes_test(lambda u: u.is_superuser)
def admin_users(request):
    context = {
        'students': Student.objects.select_related('user', 'course').all(),
        'staff': Staff.objects.select_related('user', 'office').all(),
        'program_chairs': ProgramChair.objects.select_related('user').all(),
    }
    return render(request, 'admin/users.html', context)

@login_required
@user_passes_test(lambda u: u.is_superuser)
def admin_offices(request):
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'add':
            name = request.POST.get('name')
            description = request.POST.get('description')
            
            Office.objects.create(
                name=name,
                description=description
            )
            messages.success(request, f'Office {name} added successfully.')
            
    offices = Office.objects.annotate(
        staff_count=Count('staff'),
        pending_requests=Count('clearance_requests', 
                             filter=Q(clearance_requests__status='pending'))
    ).all()
    
    context = {
        'offices': offices,
    }
    return render(request, 'admin/offices.html', context)

@login_required
@user_passes_test(lambda u: u.is_superuser)
def admin_clearances(request):
    clearances = Clearance.objects.select_related('student').all().order_by('-school_year', '-semester')
    
    # Get clearance statistics
    clearance_stats = {
        'pending': ClearanceRequest.objects.filter(status='PENDING').count(),
        'approved': ClearanceRequest.objects.filter(status='APPROVED').count(),
        'denied': ClearanceRequest.objects.filter(status='DENIED').count(),
    }
    
    # Get recent clearances
    recent_clearances = Clearance.objects.select_related('student').order_by('-created_at')[:5]
    
    context = {
        'clearances': clearances,
        'clearance_stats': clearance_stats,
        'recent_clearances': recent_clearances,
    }
    return render(request, 'admin/clearances.html', context)

@login_required
@user_passes_test(lambda u: u.is_superuser)
def admin_courses(request):
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'add':
            code = request.POST.get('code')
            name = request.POST.get('name')
            dean_id = request.POST.get('dean')
            
            try:
                dean = Dean.objects.get(id=dean_id) if dean_id else None
                Course.objects.create(
                    code=code,
                    name=name,
                    dean=dean
                )
                messages.success(request, f'Course {code} added successfully.')
            except Exception as e:
                messages.error(request, f'Error adding course: {str(e)}')
                
        elif action == 'delete':
            course_id = request.POST.get('course_id')
            try:
                course = Course.objects.get(id=course_id)
                course.delete()
                messages.success(request, f'Course {course.code} deleted successfully.')
            except Course.DoesNotExist:
                messages.error(request, 'Course not found.')
            
    courses = Course.objects.select_related('dean').all()
    deans = Dean.objects.all()
    
    context = {
        'courses': courses,
        'deans': deans,
    }
    return render(request, 'admin/courses.html', context)

@login_required
@user_passes_test(lambda u: u.is_superuser)
def create_user(request):
    if request.method == 'POST':
        user_type = request.POST.get('user_type')
        username = request.POST.get('username')
        password = request.POST.get('password')
        email = request.POST.get('email')
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')

        try:
            # Create base user
            user = User.objects.create_user(
                username=username,
                password=password,
                email=email,
                first_name=first_name,
                last_name=last_name
            )

            if user_type == 'student':
                student_id = request.POST.get('student_id')
                course_id = request.POST.get('course')
                program_chair_id = request.POST.get('program_chair')
                year_level = request.POST.get('year_level')
                
                course = Course.objects.get(id=course_id)
                program_chair = ProgramChair.objects.get(id=program_chair_id)
                
                Student.objects.create(
                    user=user,
                    student_id=student_id,
                    course=course,
                    program_chair=program_chair,
                    year_level=year_level,
                    is_approved=True,
                    approval_date=timezone.now(),
                    approval_admin=request.user
                )
            
            elif user_type == 'staff':
                office_id = request.POST.get('office')
                is_dormitory_owner = request.POST.get('is_dormitory_owner') == 'on'
                
                office = Office.objects.get(id=office_id)
                Staff.objects.create(
                    user=user,
                    office=office,
                    is_dormitory_owner=is_dormitory_owner
                )
            
            elif user_type == 'program_chair':
                dean_id = request.POST.get('dean')
                dean = Dean.objects.get(id=dean_id)
                ProgramChair.objects.create(
                    user=user,
                    dean=dean
                )

            messages.success(request, f'User {username} created successfully.')
            return redirect('admin_users')

        except Exception as e:
            messages.error(request, f'Error creating user: {str(e)}')
            return redirect('create_user')

    context = {
        'courses': Course.objects.all(),
        'offices': Office.objects.all(),
        'program_chairs': ProgramChair.objects.all(),
        'deans': Dean.objects.all(),
    }
    return render(request, 'admin/create_user.html', context)

@login_required
def get_program_chairs(request, dean_id):
    program_chairs = ProgramChair.objects.filter(dean_id=dean_id).select_related('user')
    data = [{
        'id': pc.id,
        'user': {
            'full_name': f"{pc.user.first_name} {pc.user.last_name}"
        }
    } for pc in program_chairs]
    return JsonResponse(data, safe=False)

@login_required
def get_courses(request, dean_id):
    courses = Course.objects.filter(dean_id=dean_id)
    data = [{
        'id': course.id,
        'code': course.code
    } for course in courses]
    return JsonResponse(data, safe=False)

@login_required
def get_offices(request, dean_id):
    offices = Office.objects.filter(affiliated_dean_id=dean_id)
    data = [{
        'id': office.id,
        'name': office.name
    } for office in offices]
    return JsonResponse(data, safe=False)
@login_required
def program_chair_dashboard(request):
    try:
        program_chair = request.user.programchair
        # Get relevant data for the program chair's dashboard
        students = Student.objects.filter(program_chair=program_chair)
        clearances = Clearance.objects.filter(student__in=students).order_by('-school_year', '-semester')
        
        context = {
            'program_chair': program_chair,
            'students': students,
            'clearances': clearances,
        }
        return render(request, 'core/program_chair_dashboard.html', context)
    except ProgramChair.DoesNotExist:
        messages.error(request, "Program Chair profile not found.")
        return redirect('home')

@login_required
def generate_reports(request):
    if request.method == 'POST':
        # Handle report generation logic here
        pass
    
    context = {
        'school_years': get_school_years(),
        'semesters': SEMESTER_CHOICES,
    }
    return render(request, 'core/generate_reports.html', context)

@login_required
def generate_report(request):
    if request.method == 'POST':
        school_year = request.POST.get('school_year')
        semester = request.POST.get('semester')
        report_type = request.POST.get('report_type')
        
        # Add your report generation logic here
        if report_type == 'pdf':
            # Generate PDF report
            response = HttpResponse(content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="clearance_report_{school_year}_{semester}.pdf"'
            # Add PDF generation logic here
            return response
            
        elif report_type == 'excel':
            # Generate Excel report
            response = HttpResponse(content_type='application/vnd.ms-excel')
            response['Content-Disposition'] = f'attachment; filename="clearance_report_{school_year}_{semester}.xlsx"'
            # Add Excel generation logic here
            return response
            
        messages.success(request, 'Report generated successfully')
        
    return redirect('generate_reports')

def get_school_years():
    current_year = timezone.now().year
    return [f"{year}-{year + 1}" for year in range(current_year - 2, current_year + 1)]
