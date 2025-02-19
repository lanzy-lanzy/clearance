from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.utils import timezone
from django.core.paginator import Paginator
from django.db.models import Q
from django.views.generic import TemplateView, ListView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.http import HttpResponse, JsonResponse
from django.template.loader import render_to_string
from datetime import datetime
from io import BytesIO
import os
from django.conf import settings
from django.core.files.storage import default_storage
from django.views.decorators.http import require_POST
from django.db.models import Count
# Add Office to the imports
from .models import (
    Student, Staff, ProgramChair, Course, 
    Clearance, ClearanceRequest, Office
)

def user_logout(request):
    logout(request)
    return redirect('login')
def home(request):
    if request.user.is_authenticated:
        if hasattr(request.user, 'programchair'):
            return redirect('program_chair_dashboard')
        elif hasattr(request.user, 'student'):
            return redirect('student_dashboard')
        elif request.user.is_superuser:
            return redirect('admin_dashboard')
    return render(request, 'home.html')

def user_login(request):
    if request.user.is_authenticated:
        if hasattr(request.user, 'student'):
            return redirect('student_dashboard')
        elif hasattr(request.user, 'programchair'):  # Changed from staff to programchair
            return redirect('program_chair_dashboard')
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
            elif hasattr(user, 'programchair'):  # Changed from staff to programchair
                return redirect('program_chair_dashboard')
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
    Staff can only handle clearance requests for their assigned office.
    Special handling for dormitory clearances.
    """
    clearance_request = get_object_or_404(ClearanceRequest, pk=request_id)
    
    try:
        staff_member = request.user.staff
        
        # Check if staff member belongs to the office of the clearance request
        if staff_member.office != clearance_request.office:
            messages.error(
                request, 
                f"You don't have permission to handle clearance requests for {clearance_request.office.name}. "
                f"You can only handle requests for {staff_member.office.name}."
            )
            return redirect('office_dashboard')

        # Special handling for dormitory clearances
        if clearance_request.office.name == "DORMITORY":
            if not staff_member.is_dormitory_owner:
                messages.error(request, "Only dormitory owners can handle dormitory clearances.")
                return redirect('office_dashboard')
            if clearance_request.student.dormitory_owner != staff_member:
                messages.error(request, "You can only handle clearances for your assigned students.")
                return redirect('office_dashboard')

        # Special handling for SSB offices
        if clearance_request.office.name.startswith('SSB'):
            # Check if the student belongs to the correct school
            student_dean = clearance_request.student.course.dean
            if clearance_request.office.affiliated_dean != student_dean:
                messages.error(
                    request, 
                    "You can only handle SSB clearances for students from your school."
                )
                return redirect('office_dashboard')

    except Staff.DoesNotExist:
        messages.error(request, "Staff access required.")
        return redirect('login')

    if request.method == 'POST':
        action = request.POST.get('action')
        remarks = request.POST.get('remarks', '')
        
        try:
            if action == 'approve':
                clearance_request.approve(staff_member)
                messages.success(
                    request, 
                    f"Clearance request approved for {clearance_request.student.full_name}"
                )
            elif action == 'deny':
                if not remarks:
                    messages.error(request, "Remarks are required when denying a clearance request.")
                    return redirect('office_dashboard')
                clearance_request.deny(staff_member, remarks)
                messages.success(
                    request, 
                    f"Clearance request denied for {clearance_request.student.full_name}"
                )
            else:
                messages.error(request, "Invalid action specified.")
                return redirect('office_dashboard')

        except PermissionError as e:
            messages.error(request, str(e))
        except Exception as e:
            messages.error(request, f"Error processing request: {str(e)}")
        
        # Refresh the student's overall clearance status
        clearance = Clearance.objects.get(
            student=clearance_request.student,
            school_year=clearance_request.school_year,
            semester=clearance_request.semester
        )
        clearance.check_clearance()

    return redirect('office_dashboard')

# Class-based Views
class ManageStudentsView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    model = Student
    template_name = 'core/manage_students.html'
    context_object_name = 'students'
    
    def test_func(self):
        return hasattr(self.request.user, 'programchair')  # Changed from is_superuser
    
    def get_queryset(self):
        program_chair = self.request.user.programchair
        return Student.objects.filter(course__dean=program_chair.dean).select_related(
            'user', 'course', 'program_chair'
        )

    def handle_no_permission(self):
        messages.error(self.request, "You don't have permission to access this page.")
        return redirect('home')

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
    # Get pending student registrations
    pending_approvals = Student.objects.filter(
        is_approved=False,
        user__is_active=False
    ).select_related('user', 'course').order_by('-user__date_joined')

    context = {
        'total_students': Student.objects.count(),
        'total_staff': Staff.objects.count(),
        'total_program_chairs': ProgramChair.objects.count(),
        'clearance_stats': {
            'total': Clearance.objects.count(),
            'pending': ClearanceRequest.objects.filter(status='pending').count(),
            'approved': ClearanceRequest.objects.filter(status='approved').count(),
            'denied': ClearanceRequest.objects.filter(status='denied').count(),
        },
        'recent_clearances': Clearance.objects.select_related('student')[:5],
        'offices': Office.objects.annotate(
            staff_count=Count('staff'),
            pending_requests=Count('clearance_requests', filter=Q(clearance_requests__status='pending'))
        ),
        'pending_approvals': pending_approvals,
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
def is_program_chair(user):
    return hasattr(user, 'programchair')

@login_required
@user_passes_test(is_program_chair)
def program_chair_dashboard(request):
    program_chair = request.user.programchair
    students = Student.objects.filter(course__dean=program_chair.dean)
    
    # Get current school year and semester
    current_year = timezone.now().year
    school_year = f"{current_year}-{current_year + 1}"
    semester = "1ST"  # You might want to make this dynamic
    
    # Count statistics
    total_students = students.count()
    cleared_students = students.filter(
        clearances__is_cleared=True,  # Changed from clearance to clearances
        clearances__school_year=school_year,
        clearances__semester=semester
    ).count()
    
    pending_clearances = students.filter(
        clearances__is_cleared=False,
        clearances__school_year=school_year,
        clearances__semester=semester
    ).count()
    
    # Get students with pagination
    paginator = Paginator(students, 10)  # Show 10 students per page
    page = request.GET.get('page')
    students_page = paginator.get_page(page)
    
    context = {
        'program_chair': program_chair,
        'students': students_page,
        'total_students': total_students,
        'cleared_students': cleared_students,
        'pending_clearances': pending_clearances,
        'school_year': school_year,
        'semester': semester,
        'page_obj': students_page,  # For pagination
    }
    return render(request, 'core/program_chair_dashboard.html', context)

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

@login_required
def create_clearance_requests(request):
    if not hasattr(request.user, 'student'):
        messages.error(request, "Access denied. Student profile required.")
        return redirect('home')
    
    try:
        student = request.user.student
        current_year = timezone.now().year
        school_year = f"{current_year}-{current_year + 1}"
        
        # Determine current semester based on month
        month = timezone.now().month
        if 6 <= month <= 10:
            semester = "1ST"
        elif month >= 11 or month <= 3:
            semester = "2ND"
        else:
            semester = "SUM"
        
        # Create clearance requests
        student.create_clearance_requests(school_year=school_year, semester=semester)
        
        messages.success(request, f"Clearance requests created for {school_year} {semester} semester.")
    except Exception as e:
        messages.error(request, f"Error creating clearance requests: {str(e)}")
    
    return redirect('student_dashboard')

@login_required
def view_clearance_details(request, clearance_id):
    clearance = get_object_or_404(Clearance, id=clearance_id)
    
    # Security check - ensure student can only view their own clearance
    if request.user.student != clearance.student:
        messages.error(request, "You don't have permission to view this clearance.")
        return redirect('student_dashboard')
    
    # Get all clearance requests for this clearance
    clearance_requests = ClearanceRequest.objects.filter(
        student=clearance.student,
        school_year=clearance.school_year,
        semester=clearance.semester
    ).select_related('office', 'reviewed_by')
    
    context = {
        'clearance': clearance,
        'clearance_requests': clearance_requests,
    }
    return render(request, 'core/clearance_details.html', context)

@login_required
@require_POST
def update_profile_picture(request):
    try:
        if 'profile_picture' not in request.FILES:
            messages.error(request, 'No image file provided')
            return redirect('home')

        # Handle different user types
        if hasattr(request.user, 'student'):
            profile = request.user.student
        elif hasattr(request.user, 'programchair'):
            profile = request.user.programchair
        elif request.user.is_superuser:
            profile, created = UserProfile.objects.get_or_create(user=request.user)
        else:
            messages.error(request, 'Invalid user type')
            return redirect('home')
        
        # Delete old profile picture if it exists
        if profile.profile_picture:
            profile.profile_picture.delete(save=False)
        
        # Save new profile picture
        profile.profile_picture = request.FILES['profile_picture']
        profile.save()

        messages.success(request, 'Profile picture updated successfully')
        
        # Redirect based on user type
        if hasattr(request.user, 'student'):
            return redirect('student_profile')
        elif hasattr(request.user, 'programchair'):
            return redirect('program_chair_profile')
        else:
            return redirect('admin_profile')

    except Exception as e:
        messages.error(request, f'Error updating profile picture: {str(e)}')
        return redirect('home')
@login_required
@user_passes_test(is_program_chair)
def program_chair_profile(request):
    """
    Display and manage program chair profile information.
    """
    try:
        program_chair = request.user.programchair
        return render(request, 'core/program_chair_profile.html', {
            'program_chair': program_chair
        })
    except ProgramChair.DoesNotExist:
        messages.error(request, "Program chair profile not found.")
        return redirect('home')

@login_required
@user_passes_test(lambda u: u.is_superuser)
def admin_profile(request):
    """
    Display and manage administrator profile information.
    """
    if not request.user.is_superuser:
        messages.error(request, "Access denied. Administrator privileges required.")
        return redirect('home')
    
    # Get or create UserProfile for admin
    profile, created = UserProfile.objects.get_or_create(user=request.user)
    
    return render(request, 'core/admin_profile.html', {
        'admin_user': request.user,
        'profile': profile
    })

@login_required
def staff_dashboard(request):
    """Staff dashboard view showing overview and recent requests."""
    try:
        staff = request.user.staff
    except Staff.DoesNotExist:
        return redirect('login')

    # Get current semester info
    current_year = timezone.now().year
    school_year = f"{current_year}-{current_year + 1}"
    month = timezone.now().month
    
    # Determine current semester based on month
    if 6 <= month <= 10:
        current_semester = "1ST"
    elif month >= 11 or month <= 3:
        current_semester = "2ND"
    else:
        current_semester = "SUM"

    # Get pending requests
    pending_requests = ClearanceRequest.objects.filter(
        office=staff.office,
        status='pending'
    )

    # Get today's statistics
    today = timezone.now().date()
    approved_today_count = ClearanceRequest.objects.filter(
        office=staff.office,
        status='approved',
        reviewed_date__date=today
    ).count()

    # Get total processed requests
    total_processed = ClearanceRequest.objects.filter(
        office=staff.office,
        status__in=['approved', 'denied']
    )

    # Get recent requests
    recent_requests = ClearanceRequest.objects.filter(
        office=staff.office
    ).order_by('-request_date')[:10]

    context = {
        'current_semester': current_semester,
        'pending_requests_count': pending_requests.count(),
        'approved_today_count': approved_today_count,
        'total_processed': total_processed.count(),
        'recent_requests': recent_requests,
    }

    return render(request, 'core/staff_dashboard.html', context)  # Updated template path

@login_required
def staff_pending_requests(request):
    """View for staff to manage their pending clearance requests."""
    try:
        staff = request.user.staff
    except Staff.DoesNotExist:
        return redirect('login')

    # Get current semester info
    current_year = timezone.now().year
    school_year = f"{current_year}-{current_year + 1}"
    month = timezone.now().month
    
    # Determine current semester based on month
    if 6 <= month <= 10:
        current_semester = "1ST"
    elif month >= 11 or month <= 3:
        current_semester = "2ND"
    else:
        current_semester = "SUM"

    # Get pending requests for the staff's office
    pending_requests = ClearanceRequest.objects.filter(
        office=staff.office,
        status='pending'
    ).select_related(
        'student',
        'student__user',
        'student__course'
    ).order_by('-request_date')

    context = {
        'pending_requests': pending_requests,
        'current_semester': current_semester,
        'school_year': school_year,
        'office': staff.office
    }

    return render(request, 'core/staff_pending_requests.html', context)  # Updated template path
@login_required
@require_POST
def approve_clearance_request(request, request_id):
    """Handle approval of a clearance request."""
    try:
        staff = request.user.staff
        clearance_request = get_object_or_404(ClearanceRequest, id=request_id)
        
        # Check if staff member belongs to the office of the clearance request
        if staff.office != clearance_request.office:
            messages.error(
                request,
                f"You don't have permission to handle clearance requests for {clearance_request.office.name}"
            )
            return redirect(request.META.get('HTTP_REFERER', 'staff_dashboard'))

        # Check if request is already processed
        if clearance_request.status != 'pending':
            messages.error(request, 'This request has already been processed')
            return redirect(request.META.get('HTTP_REFERER', 'staff_dashboard'))
        
        # Approve the request
        clearance_request.approve(staff)
        
        # Update the student's overall clearance status
        clearance = Clearance.objects.get(
            student=clearance_request.student,
            school_year=clearance_request.school_year,
            semester=clearance_request.semester
        )
        clearance.check_clearance()
        
        messages.success(
            request,
            f'Successfully approved clearance request for {clearance_request.student.full_name}'
        )
        
    except Staff.DoesNotExist:
        messages.error(request, 'Staff access required')
    except Exception as e:
        messages.error(request, f'Error processing request: {str(e)}')
    
    return redirect(request.META.get('HTTP_REFERER', 'staff_dashboard'))

@login_required
@require_POST
def deny_clearance_request(request, request_id):
    """Handle denial of a clearance request."""
    try:
        staff = request.user.staff
        clearance_request = get_object_or_404(ClearanceRequest, id=request_id)
        
        # Check if staff member belongs to the office of the clearance request
        if staff.office != clearance_request.office:
            messages.error(
                request,
                f"You don't have permission to handle clearance requests for {clearance_request.office.name}"
            )
            return redirect(request.META.get('HTTP_REFERER', 'staff_dashboard'))

        # Check if request is already processed
        if clearance_request.status != 'pending':
            messages.error(request, 'This request has already been processed')
            return redirect(request.META.get('HTTP_REFERER', 'staff_dashboard'))
        
        # Get reason from POST data
        reason = request.POST.get('reason')
        
        if not reason:
            messages.error(request, 'A reason must be provided for denial')
            return redirect(request.META.get('HTTP_REFERER', 'staff_dashboard'))
        
        # Deny the request
        clearance_request.deny(staff, reason)
        
        # Update the student's overall clearance status
        clearance = Clearance.objects.get(
            student=clearance_request.student,
            school_year=clearance_request.school_year,
            semester=clearance_request.semester
        )
        clearance.check_clearance()
        
        messages.success(
            request,
            f'Successfully denied clearance request for {clearance_request.student.full_name}'
        )
        
    except Staff.DoesNotExist:
        messages.error(request, 'Staff access required')
    except Exception as e:
        messages.error(request, f'Error processing request: {str(e)}')
    
    return redirect(request.META.get('HTTP_REFERER', 'staff_dashboard'))

@login_required
def staff_clearance_history(request):
    """View for staff to see history of processed clearance requests."""
    try:
        staff = request.user.staff
    except Staff.DoesNotExist:
        return redirect('login')

    # Get filter parameters from request
    status = request.GET.get('status', '')
    school_year = request.GET.get('school_year', '')
    semester = request.GET.get('semester', '')
    search_query = request.GET.get('search', '')

    # Base queryset
    clearance_requests = ClearanceRequest.objects.filter(
        office=staff.office,
        status__in=['approved', 'denied']
    ).select_related(
        'student',
        'student__user',
        'student__course',
        'reviewed_by'
    ).order_by('-reviewed_date')

    # Apply filters
    if status:
        clearance_requests = clearance_requests.filter(status=status)
    if school_year:
        clearance_requests = clearance_requests.filter(school_year=school_year)
    if semester:
        clearance_requests = clearance_requests.filter(semester=semester)
    if search_query:
        clearance_requests = clearance_requests.filter(
            Q(student__student_id__icontains=search_query) |
            Q(student__user__first_name__icontains=search_query) |
            Q(student__user__last_name__icontains=search_query)
        )

    # Get unique school years for filter dropdown
    school_years = ClearanceRequest.objects.filter(
        office=staff.office
    ).values_list('school_year', flat=True).distinct()

    # Pagination
    paginator = Paginator(clearance_requests, 20)  # 20 items per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'school_years': school_years,
        'current_filters': {
            'status': status,
            'school_year': school_year,
            'semester': semester,
            'search': search_query,
        },
        'office': staff.office,
        'SEMESTER_CHOICES': SEMESTER_CHOICES,
    }

    return render(request, 'core/staff_clearance_history.html', context)  # Updated path
@login_required
def staff_profile(request):
    """
    Display and manage staff profile information.
    """
    try:
        staff = request.user.staff
    except Staff.DoesNotExist:
        messages.error(request, "Staff profile not found.")
        return redirect('home')

    if request.method == 'POST':
        # Handle profile updates
        if 'update_role' in request.POST:
            new_role = request.POST.get('role')
            staff.role = new_role
            staff.save()
            messages.success(request, 'Role updated successfully')
            return redirect('staff_profile')

    context = {
        'staff': staff,
        'office': staff.office,
        'user': request.user,
        'is_dormitory_owner': staff.is_dormitory_owner,
        'assigned_students': staff.students_dorm.all() if staff.is_dormitory_owner else None,
    }

    return render(request, 'core/staff_profile.html', context)  # Updated template path

@login_required
def view_request(request, request_id):
    """
    View for staff to see details of a specific clearance request.
    """
    try:
        staff = request.user.staff
    except Staff.DoesNotExist:
        messages.error(request, "Staff profile not found.")
        return redirect('home')

    # Get the clearance request with related data
    clearance_request = get_object_or_404(
        ClearanceRequest.objects.select_related(
            'student',
            'student__user',
            'student__course',
            'office',
            'reviewed_by'
        ),
        id=request_id
    )

    # Check if staff member can handle this request
    if not clearance_request.can_be_handled_by(staff):
        messages.error(request, "You don't have permission to view this request.")
        return redirect('staff_pending_requests')

    # Handle POST requests for approving/denying
    if request.method == 'POST':
        action = request.POST.get('action')
        
        try:
            if action == 'approve':
                clearance_request.approve(staff)
                messages.success(request, 'Clearance request approved successfully.')
                return redirect('staff_pending_requests')
            
            elif action == 'deny':
                reason = request.POST.get('reason')
                if not reason:
                    messages.error(request, 'A reason must be provided when denying a request.')
                else:
                    clearance_request.deny(staff, reason)
                    messages.success(request, 'Clearance request denied.')
                    return redirect('staff_pending_requests')
        
        except PermissionError as e:
            messages.error(request, str(e))
        except Exception as e:
            messages.error(request, f'Error processing request: {str(e)}')

    context = {
        'clearance_request': clearance_request,
        'student': clearance_request.student,
        'office': staff.office,
        'can_handle': clearance_request.can_be_handled_by(staff)
    }

    return render(request, 'staff/view_request.html', context)

from django.http import JsonResponse
from django.views.decorators.http import require_POST

def get_user_details(request, user_id):
    """API endpoint to get detailed user information"""
    try:
        student = Student.objects.select_related('user', 'course').get(user_id=user_id)
        data = {
            'full_name': f"{student.user.first_name} {student.user.last_name}",
            'student_id': student.student_id,
            'email': student.user.email,
            'course': student.course.name,
            'year_level': student.year_level,
            'is_boarder': student.is_boarder,
        }
        return JsonResponse(data)
    except Student.DoesNotExist:
        return JsonResponse({'error': 'Student not found'}, status=404)

@require_POST
def approve_registration(request, user_id):
    """API endpoint to approve student registration"""
    try:
        student = Student.objects.get(user_id=user_id)
        student.is_approved = True
        student.approval_date = timezone.now()
        student.approval_admin = request.user
        student.user.is_active = True
        student.user.save()
        student.save()
        return JsonResponse({'success': True})
    except Student.DoesNotExist:
        return JsonResponse({'error': 'Student not found'}, status=404)

@require_POST
def reject_registration(request, user_id):
    """API endpoint to reject student registration"""
    try:
        data = json.loads(request.body)
        reason = data.get('reason')
        
        student = Student.objects.get(user_id=user_id)
        student.user.delete()  # This will cascade delete the student profile
        
        # Could add notification logic here
        
        return JsonResponse({'success': True})
    except Student.DoesNotExist:
        return JsonResponse({'error': 'Student not found'}, status=404)






























































