from django.contrib.auth import authenticate, login
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.views.generic import TemplateView, ListView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from django.template.loader import render_to_string
from datetime import datetime

# PDF Generation
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch

# Excel Generation
from openpyxl import Workbook

# Local imports
from core.models import (
    ClearanceRequest, Clearance, Staff, Student, 
    Office, ProgramChair, User, Payment
)


def home(request):
    return render(request, 'home.html')



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
            
            # Redirect based on user role after successful update
            if hasattr(request.user, 'staff'):
                return redirect('office_dashboard')
            elif hasattr(request.user, 'programchair'):
                return redirect('program_chair_dashboard')
            else:
                return redirect('student_dashboard')
        except PermissionError as e:
            messages.error(request, str(e))
            return redirect('office_dashboard')  # Redirect to office dashboard on error

    context = {
        'clearance_request': clearance_request,
    }
    return render(request, 'core/update_clearance_request.html', context)

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from core.models import ClearanceRequest, Clearance, Student
@login_required
def student_dashboard(request):
    """Dashboard for students to view their clearance status."""
    try:
        student = request.user.student
    except Student.DoesNotExist:
        messages.error(request, 'You are not authorized to view this page.')
        return redirect('login')

    clearance_requests = student.clearance_requests.select_related('office', 'reviewed_by').all()
    clearance, created = Clearance.objects.get_or_create(student=student)
    
    dormitory_request = None
    if student.is_boarder:
        dormitory_request = clearance_requests.filter(office__name='Dormitory').first()

    context = {
        'student': student,
        'student_info': {
            'full_name': student.user.get_full_name(),
            'student_id': student.student_id,
            'course': student.course,
            'year_level': student.year_level,
            'is_boarder': student.is_boarder
        },
        'clearance_requests': clearance_requests,
        'clearance': clearance,
        'dormitory_request': dormitory_request,
        'pending_count': clearance_requests.filter(status='pending').count(),
        'approved_count': clearance_requests.filter(status='approved').count(),
        'denied_count': clearance_requests.filter(status='denied').count()
    }
    return render(request, 'core/student_dashboard.html', context)


def register_view(request):
    if request.method == 'POST':
        # Get form data
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        password2 = request.POST.get('password2')
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        student_id = request.POST.get('student_id')
        course = request.POST.get('course')
        year_level = request.POST.get('year_level')
        program_chair_id = request.POST.get('program_chair')
        is_boarder = request.POST.get('is_boarder') == 'on'
        dormitory_owner_id = request.POST.get('dormitory_owner')

        # Validate username
        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already taken!")
            return redirect('register')

        # Validate passwords match
        if password != password2:
            messages.error(request, "Passwords do not match!")
            return redirect('register')

        try:
            # Validate course selection based on selected dean
            program_chair = ProgramChair.objects.get(id=program_chair_id)
            valid_courses = {
                'SET DEAN': ['BSIT'],
                'STE DEAN': ['BPED', 'BEED', 'BSED', 'BAELS', 'BSMATH'],
                'SOCJE DEAN': ['BSCRIM', 'BSISM'],
                'SAFES DEAN': ['BSA', 'BSAES', 'BCF']
            }
            
            if course not in valid_courses.get(program_chair.designation, []):
                messages.error(request, 'Invalid course selection for the chosen school')
                return redirect('register')

            # Validate dormitory owner selection
            if is_boarder and not dormitory_owner_id:
                messages.error(request, "Boarder students must select a dormitory owner!")
                return redirect('register')

            # Create user
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name
            )

            # Create student profile with program chair assignment
            student = Student.objects.create(
                user=user,
                student_id=student_id,
                course=course,
                year_level=int(year_level),
                is_boarder=is_boarder,
                program_chair_id=program_chair_id  # Assign program chair using ID
            )

            # If student is a boarder and dormitory owner is selected, assign it
            if is_boarder and dormitory_owner_id:
                try:
                    dorm_owner = Staff.objects.get(id=dormitory_owner_id, is_dormitory_owner=True)
                    student.dormitory_owner = dorm_owner
                    student.save()
                    
                    # Create initial payment record for boarders
                    Payment.objects.create(
                        student=student,
                        amount=0.00,
                        is_paid=False
                    )
                except Staff.DoesNotExist:
                    user.delete()
                    messages.error(request, "Selected dormitory owner not found!")
                    return redirect('register')

            # Create clearance requests for the student
            student.create_clearance_requests()
            
            # Create clearance record
            Clearance.objects.create(student=student)

            # Login the user
            login(request, user)
            messages.success(request, "Registration successful! Welcome to the clearance system.")
            return redirect('student_dashboard')

        except IntegrityError:
            messages.error(request, "Registration failed. Please try again with different information.")
            return redirect('register')
        except Exception as e:
            if 'user' in locals():
                user.delete()
            messages.error(request, f"Registration failed: {str(e)}")
            return redirect('register')

    # If GET request, show the registration form
    program_chairs = ProgramChair.objects.filter(designation__in=[
        'SET DEAN', 'STE DEAN', 'SOCJE DEAN', 'SAFES DEAN'
    ])
    dormitory_owners = Staff.objects.filter(is_dormitory_owner=True)
    
    return render(request, 'registration/register.html', {
        'program_chairs': program_chairs,
        'dormitory_owners': dormitory_owners,
    })
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.contrib import messages
from core.models import Student

def login_view(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            try:
                # Check for staff member first
                if hasattr(user, 'staff'):
                    staff = user.staff
                    if staff.is_dormitory_owner:
                        return redirect('bh_owner_dashboard')
                    else:
                        return redirect('office_dashboard')
                # Then check other user types
                elif user.is_staff:
                    return redirect('admin_dashboard')
                elif hasattr(user, 'programchair'):
                    return redirect('program_chair_dashboard')
                elif hasattr(user, 'student'):
                    return redirect('student_dashboard')
                else:
                    messages.error(request, 'Invalid user type')
                    return redirect('login')
            except Staff.DoesNotExist:
                messages.error(request, 'Staff profile not found')
                return redirect('login')
        else:
            messages.error(request, 'Invalid credentials')

    return render(request, 'registration/login.html')

from core.models import Office, Student, ClearanceRequest
@login_required
def create_clearance_requests(request):
      try:
          student = request.user.student
      except Student.DoesNotExist:
          messages.error(request, "Only students can access this page.")
          return redirect('student_dashboard')

      offices = Office.objects.all()
      # Build a dictionary mapping office.id to the student's existing clearance request (if any)
      clearance_requests = {cr.office.id: cr for cr in student.clearance_requests.all()}

      if request.method == "POST":
          office_id = request.POST.get("office_id")
          if office_id:
              office = Office.objects.get(id=office_id)
              cr = ClearanceRequest.objects.filter(student=student, office=office).first()
              if cr:
                  # If a denied request exists, allow re-submission and clear the denial reason.
                  if cr.status == 'denied':
                      cr.status = 'pending'
                      cr.notes = ''
                      cr.remarks = ''
                      cr.request_date = timezone.now()
                      cr.reviewed_date = None
                      cr.save()
                      messages.success(request, f"Clearance request re-submitted for {office.name}.")
                  else:
                      messages.warning(request, f"Clearance request for {office.name} already exists.")
              else:
                  ClearanceRequest.objects.create(student=student, office=office)
                  messages.success(request, f"Clearance request submitted for {office.name}.")
              return redirect("clearance_requests")
                
      context = {
          "offices": offices,
          "clearance_requests": clearance_requests,
      }
      return render(request, "core/create_clearance_requests.html", context)
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from core.models import ClearanceRequest, Staff
@login_required
def office_dashboard(request):
    """Dashboard for office staff to manage clearance requests."""
    try:
        staff_member = request.user.staff
        if staff_member.is_dormitory_owner:
            return redirect('bh_owner_dashboard')
    except Staff.DoesNotExist:
        messages.error(request, 'You are not authorized to view this page.')
        return redirect('login')

    current_office = staff_member.office
    clearance_requests = ClearanceRequest.objects.filter(office=current_office)
    
    # Search functionality
    search_query = request.GET.get('search', '')
    if search_query:
        clearance_requests = clearance_requests.filter(
            Q(student__student_id__icontains=search_query) |
            Q(student__user__first_name__icontains=search_query) |
            Q(student__user__last_name__icontains=search_query)
        )
    
    # Pagination
    paginator = Paginator(clearance_requests, 10)  # Show 10 requests per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    if request.method == 'POST':
        request_id = request.POST.get('clearance_request_id')
        action = request.POST.get('action')
        cr = get_object_or_404(ClearanceRequest, id=request_id, office=current_office)
        
        try:
            if action == 'approve':
                cr.approve(staff_member)
                messages.success(request, 'Clearance request approved successfully.')
            elif action == 'deny':
                notes = request.POST.get('notes', '')
                cr.deny(staff_member, notes)
                messages.success(request, 'Clearance request denied successfully.')
            
            # Check overall clearance status
            clearance = getattr(cr.student, 'clearance', None)
            if clearance:
                clearance.check_clearance()
        except PermissionError as e:
            messages.error(request, str(e))
        
        return redirect('office_dashboard')

    context = {
        'office': current_office,
        'page_obj': page_obj,
        'search_query': search_query,
        'clearance_requests': clearance_requests,
    }
    return render(request, 'core/office_dashboard.html', context)


def clearance_requests(request):
    # Replace with actual logic to list and manage clearance requests if needed.
    return render(request, 'core/clearance_requests.html')

def office_profile(request):
    # Replace with logic to show the office or staff profile.
    return render(request, 'core/office_profile.html')

def office_settings(request):
    # Replace with settings management logic.
    return render(request, 'core/office_settings.html')


class ProgramChairDashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'core/program_chair_dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        pc = self.request.user.programchair  # current program chair

        # Get all students for this program chair
        students = Student.objects.filter(
            user__is_staff=False,
            program_chair=pc
        ).order_by('user__first_name')

        # Handle search
        search_query = self.request.GET.get('search', '')
        if search_query:
            students = students.filter(
                Q(student_id__icontains=search_query) |
                Q(user__first_name__icontains=search_query) |
                Q(user__last_name__icontains=search_query)
            )

        # Pagination
        paginator = Paginator(students, 10)  # Show 10 students per page
        page_number = self.request.GET.get('page')
        page_obj = paginator.get_page(page_number)

        context['total_students'] = Student.objects.filter(
            user__is_staff=False,
            program_chair=pc
        ).count()

        context['pending_clearances'] = Clearance.objects.filter(
            is_cleared=True, 
            program_chair_approved=False, 
            student__program_chair=pc
        ).count()

        context['approved_clearances'] = Clearance.objects.filter(
            program_chair_approved=True,
            student__program_chair=pc
        ).count()

        # Clearance status for dashboard breakdown
        context['clearance_stats'] = {
            'ready_for_approval': Clearance.objects.filter(
                is_cleared=True, 
                program_chair_approved=False,
                student__program_chair=pc
            ),
            'recently_approved': Clearance.objects.filter(
                program_chair_approved=True,
                student__program_chair=pc
            ).order_by('-cleared_date')[:5]
        }

        # Course-wise statistics
        context['course_stats'] = Student.objects.filter(
            user__is_staff=False,
            program_chair=pc
        ).values('course').annotate(
            total=Count('id'),
            cleared=Count('clearance', filter=Q(clearance__is_cleared=True))
        )

        # Add search and pagination context
        context['search_query'] = search_query
        context['page_obj'] = page_obj
        context['students'] = students  # Keep this for other parts of the template

        return context
def unlock_permit_view(request, clearance_id):
        """
        Allows the Program Chair to unlock the permit for a student
        who is already cleared by all offices.
        """
        clearance = get_object_or_404(Clearance, pk=clearance_id)

        # Ensure the clearance is actually cleared before unlocking
        if not clearance.is_cleared:
            messages.error(request, "Cannot unlock permit. The student has not been cleared by all offices.")
        else:
            clearance.unlock_permit()
            messages.success(request, f"Permit unlocked for {clearance.student.full_name}.")

        return redirect('program_chair_dashboard')
        return context

from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin

class ProgramChairStudentsView(LoginRequiredMixin, TemplateView):
    template_name = 'core/program_chair_students.html'

@login_required
def re_request_clearance(request, request_id):
    from django.utils import timezone
    from django.contrib import messages
    from core.models import ClearanceRequest, Student

    try:
        student = request.user.student
    except Student.DoesNotExist:
        messages.error(request, "Only students can perform this action.")
        return redirect('student_dashboard')

    cr = get_object_or_404(ClearanceRequest, pk=request_id, student=student)
    if cr.status != 'denied':
        messages.error(request, "Only denied requests can be re-submitted.")
        return redirect('student_dashboard')

    cr.status = 'pending'
    cr.notes = ''      # clear the denial reason
    cr.remarks = ''    # clear any extra remarks
    cr.request_date = timezone.now()
    cr.reviewed_date = None
    cr.save()
    messages.success(request, "Clearance request re-submitted successfully.")
    return redirect('student_dashboard')

from django.shortcuts import render, get_object_or_404
from .models import Clearance

@login_required
def print_permit(request, clearance_id):
    # Retrieve the clearance record. This view assumes that clearance is unlocked.
    clearance = get_object_or_404(Clearance, pk=clearance_id)
    
    # Ensure that the current user is a program chair/dean
    if not hasattr(request.user, 'programchair'):
        messages.error(request, "You are not authorized to print permits.")
        return redirect('login')
    
    # Check that the clearance record's student is assigned to the logged in program chair
    if clearance.student.program_chair != request.user.programchair:
        messages.error(request, "You are not allowed to print the permit for this student.")
        return redirect('program_chair_dashboard')

    # Retrieve the logo URL from the program chair
    logo_url = clearance.student.program_chair.get_logo_url()

    context = {
        'clearance': clearance,
        'student': clearance.student,
        'logo_url': logo_url,
    }
    return render(request, 'core/print_permit.html', context)
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from core.models import Payment, Student, Staff

@login_required
def payment_dashboard(request):
    """View for a BH (Dormitory) owner to monitor their assigned students' payments."""
    try:
        staff_member = request.user.staff
        if not staff_member.is_dormitory_owner:
            messages.error(request, 'You must be a BH/Dormitory owner to view this page.')
            return redirect('bh_owner_dashboard')
    except Staff.DoesNotExist:
        messages.error(request, 'You are not authorized to view this page.')
        return redirect('login')

    # Only show payments for students assigned to this BH owner
    payments = Payment.objects.select_related('student').filter(student__dormitory_owner=staff_member)
    context = {
        'payments': payments
    }
    return render(request, 'core/payment_dashboard.html', context)




@login_required
def update_payment(request, payment_id):
    """Allows BH owner to mark a payment as 'paid' or 'unpaid' for their assigned students."""
    payment = get_object_or_404(Payment, pk=payment_id)
    
    try:
        staff_member = request.user.staff
        if not staff_member.is_dormitory_owner:
            messages.error(request, 'You must be a BH/Dormitory owner to perform this action.')
            return redirect('bh_owner_dashboard')
        # Check if the payment belongs to an assigned student
        if payment.student.dormitory_owner != staff_member:
            messages.error(request, 'You can only manage payments for your assigned students.')
            return redirect('bh_owner_dashboard')
    except Staff.DoesNotExist:
        messages.error(request, 'You are not authorized to view this page.')
        return redirect('login')

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'paid':
            payment.is_paid = True
            payment.payment_date = timezone.now()
        elif action == 'unpaid':
            payment.is_paid = False
            payment.payment_date = None
        payment.save()
        messages.success(request, 'Payment status updated successfully.')
        return redirect('payment_dashboard')

    # If not POST, redirect to payment dashboard
    return redirect('payment_dashboard')


@login_required
def bh_owner_dashboard(request):
    """Dashboard for BH owners to manage their assigned students."""
    try:
        staff_member = request.user.staff
        if not staff_member.is_dormitory_owner:
            messages.error(request, 'You must be a BH owner to view this page.')
            return redirect('office_dashboard')
    except Staff.DoesNotExist:
        messages.error(request, 'You are not authorized to view this page.')
        return redirect('login')

    # Filter clearance requests to only include those assigned to the current BH owner
    clearance_requests = ClearanceRequest.objects.filter(
        student__dormitory_owner=staff_member,
        office__name='Dormitory'
    ).select_related('student')
    
    payments = Payment.objects.filter(student__dormitory_owner=staff_member)
    
    context = {
        'clearance_requests': clearance_requests,
        'payments': payments,
    }
    return render(request, 'core/bh_owner_dashboard.html', context)



@login_required
def admin_dashboard(request):
    """Admin dashboard view for managing users and system data."""
    if not request.user.is_staff:
        messages.error(request, 'You are not authorized to access the admin dashboard.')
        return redirect('login')

    context = {
        'total_students': Student.objects.count(),
        'total_staff': Staff.objects.count(),
        'total_program_chairs': ProgramChair.objects.count(),
        'total_offices': Office.objects.count(),
        'recent_students': Student.objects.select_related('user', 'program_chair').order_by('-created_at')[:5],
        'recent_clearances': Clearance.objects.select_related('student').order_by('-cleared_date')[:5],
        'clearance_stats': {
            'pending': ClearanceRequest.objects.filter(status='pending').count(),
            'approved': ClearanceRequest.objects.filter(status='approved').count(),
            'denied': ClearanceRequest.objects.filter(status='denied').count(),
        },
        'offices': Office.objects.annotate(
            staff_count=Count('staff'),
            pending_requests=Count('clearance_requests', filter=Q(clearance_requests__status='pending'))
        )
    }
    return render(request, 'admin/dashboard.html', context)

@login_required
def admin_users(request):
    """Admin view for managing users."""
    if not request.user.is_staff:
        messages.error(request, 'You are not authorized to access the admin dashboard.')
        return redirect('login')

    if request.method == 'POST':
        action = request.POST.get('action')
        user_id = request.POST.get('user_id')

        if action == 'delete':
            user = get_object_or_404(User, id=user_id)
            user.delete()
            messages.success(request, f'User {user.username} deleted successfully.')
            return redirect('admin_users')

    context = {
        'students': Student.objects.select_related('user', 'program_chair').all(),
        'staff': Staff.objects.select_related('user', 'office').all(),
        'program_chairs': ProgramChair.objects.select_related('user').all(),
        'offices': Office.objects.all(),  # For staff creation
    }
    return render(request, 'admin/users.html', context)

@login_required
def admin_create_user(request):
    """Admin view for creating users."""
    if not request.user.is_staff:
        messages.error(request, 'You are not authorized to access the admin dashboard.')
        return redirect('login')

    if request.method == 'POST':
        user_type = request.POST.get('user_type')
        username = request.POST.get('username')
        password = request.POST.get('password')
        email = request.POST.get('email')
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')

        try:
            user = User.objects.create_user(
                username=username,
                password=password,
                email=email,
                first_name=first_name,
                last_name=last_name
            )

            if user_type == 'student':
                Student.objects.create(
                    user=user,
                    student_id=request.POST.get('student_id'),
                    course=request.POST.get('course'),
                    year_level=int(request.POST.get('year_level')),
                    program_chair_id=request.POST.get('program_chair')
                )
            elif user_type == 'staff':
                Staff.objects.create(
                    user=user,
                    office_id=request.POST.get('office'),
                    role=request.POST.get('role'),
                    is_dormitory_owner=request.POST.get('is_dormitory_owner') == 'on'
                )
            elif user_type == 'program_chair':
                ProgramChair.objects.create(
                    user=user,
                    designation=request.POST.get('designation')
                )

            messages.success(request, f'{user_type.title()} created successfully.')
            return redirect('admin_users')
        except Exception as e:
            messages.error(request, f'Error creating user: {str(e)}')
            return redirect('admin_create_user')

    context = {
        'offices': Office.objects.all(),
        'program_chairs': ProgramChair.objects.all(),
    }
    return render(request, 'admin/create_user.html', context)

@login_required
def admin_edit_user(request, user_id):
    """Admin view for editing users."""
    if not request.user.is_staff:
        messages.error(request, 'You are not authorized to access the admin dashboard.')
        return redirect('login')

    user = get_object_or_404(User, id=user_id)
    user_type = 'student' if hasattr(user, 'student') else 'staff' if hasattr(user, 'staff') else 'program_chair'

    if request.method == 'POST':
        try:
            user.username = request.POST.get('username')
            user.email = request.POST.get('email')
            user.first_name = request.POST.get('first_name')
            user.last_name = request.POST.get('last_name')
            if request.POST.get('password'):
                user.set_password(request.POST.get('password'))
            user.save()

            if user_type == 'student':
                student = user.student
                student.student_id = request.POST.get('student_id')
                student.course = request.POST.get('course')
                student.year_level = int(request.POST.get('year_level'))
                student.program_chair_id = request.POST.get('program_chair')
                student.save()
            elif user_type == 'staff':
                staff = user.staff
                staff.office_id = request.POST.get('office')
                staff.role = request.POST.get('role')
                staff.is_dormitory_owner = request.POST.get('is_dormitory_owner') == 'on'
                staff.save()
            elif user_type == 'program_chair':
                program_chair = user.programchair
                program_chair.designation = request.POST.get('designation')
                program_chair.save()

            messages.success(request, f'User updated successfully.')
            return redirect('admin_users')
        except Exception as e:
            messages.error(request, f'Error updating user: {str(e)}')

    context = {
        'user_obj': user,
        'user_type': user_type,
        'offices': Office.objects.all(),
        'program_chairs': ProgramChair.objects.all(),
    }
    return render(request, 'admin/edit_user.html', context)

@login_required
def admin_offices(request):
    """Admin view for managing offices."""
    if not request.user.is_staff:
        messages.error(request, 'You are not authorized to access the admin dashboard.')
        return redirect('login')

    offices = Office.objects.annotate(
        staff_count=Count('staff'),
        total_requests=Count('clearance_requests'),
        pending_requests=Count('clearance_requests', filter=Q(clearance_requests__status='pending'))
    )
    total_staff = sum(office.staff_count for office in offices)
    total_pending = sum(office.pending_requests for office in offices)
    
    context = {
        'offices': offices,
        'total_staff': total_staff,
        'total_pending': total_pending,
    }
    return render(request, 'admin/offices.html', context)

@login_required
def admin_clearances(request):
    """Admin view for monitoring clearance requests."""
    if not request.user.is_staff:
        messages.error(request, 'You are not authorized to access the admin dashboard.')
        return redirect('login')

    clearance_requests = ClearanceRequest.objects.select_related(
        'student', 'office', 'reviewed_by'
    ).order_by('-request_date')

    pending_count = clearance_requests.filter(status='pending').count()
    approved_count = clearance_requests.filter(status='approved').count()
    denied_count = clearance_requests.filter(status='denied').count()

    clearances = Clearance.objects.select_related('student').all()

    context = {
        'clearance_requests': clearance_requests,
        'clearances': clearances,
        'pending_count': pending_count,
        'approved_count': approved_count,
        'denied_count': denied_count,
    }
    return render(request, 'admin/clearances.html', context)


@login_required
def student_profile(request):
    """View for students to see and manage their profile."""
    try:
        student = request.user.student
    except Student.DoesNotExist:
        messages.error(request, 'You are not authorized to view this page.')
        return redirect('login')

    context = {
        'student': student,
        'student_info': {
            'full_name': student.user.get_full_name(),
            'student_id': student.student_id,
            'course': student.course,
            'year_level': student.year_level,
            'is_boarder': student.is_boarder,
            'program_chair': student.program_chair
        }
    }
    return render(request, 'core/student_profile.html', context)


@login_required
def student_detail(request, student_id):
    """View for program chairs to see detailed student information."""
    # Get student and verify program chair access
    student = get_object_or_404(Student, pk=student_id)
    if not hasattr(request.user, 'programchair') or student.program_chair != request.user.programchair:
        messages.error(request, "You are not authorized to view this student's details.")
        return redirect('program_chair_dashboard')

    # Get all clearance requests with related data
    clearance_requests = student.clearance_requests.select_related(
        'office', 'reviewed_by'
    ).order_by('office__name')

    context = {
        'student': student,
        'clearance_requests': clearance_requests,
    }
    return render(request, 'core/student_detail.html', context)




@login_required
def clearance_status(request):
    """View for students to check their clearance status."""
    try:
        student = request.user.student
    except Student.DoesNotExist:
        messages.error(request, 'You are not authorized to view this page.')
        return redirect('login')

    clearance = get_object_or_404(Clearance, student=student)
    clearance_requests = student.clearance_requests.select_related('office', 'reviewed_by').all()

    context = {
        'student': student,
        'clearance': clearance,
        'clearance_requests': clearance_requests,
        'pending_count': clearance_requests.filter(status='pending').count(),
        'approved_count': clearance_requests.filter(status='approved').count(),
        'denied_count': clearance_requests.filter(status='denied').count()
    }
    return render(request, 'core/clearance_status.html', context)


class ManageStudentsView(LoginRequiredMixin, ListView):
    template_name = 'core/manage_students.html'
    context_object_name = 'page_obj'
    paginate_by = 10

    def get_queryset(self):
        pc = self.request.user.programchair
        queryset = Student.objects.filter(program_chair=pc).order_by('user__first_name')
        
        # Handle search
        search_query = self.request.GET.get('search', '')
        if search_query:
            queryset = queryset.filter(
                Q(student_id__icontains=search_query) |
                Q(user__first_name__icontains=search_query) |
                Q(user__last_name__icontains=search_query)
            )
        
        # Handle filters
        course = self.request.GET.get('course')
        year_level = self.request.GET.get('year_level')
        clearance_status = self.request.GET.get('clearance_status')
        
        if course:
            queryset = queryset.filter(course=course)
        if year_level:
            queryset = queryset.filter(year_level=year_level)
        if clearance_status:
            if clearance_status == 'cleared':
                queryset = queryset.filter(clearance__is_cleared=True)
            elif clearance_status == 'pending':
                queryset = queryset.filter(clearance__is_cleared=False)
        
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        pc = self.request.user.programchair
        context['courses'] = Student.objects.filter(program_chair=pc).values_list('course', flat=True).distinct()
        context['year_levels'] = range(1, 5)  # 1 to 4 year levels
        context['search_query'] = self.request.GET.get('search', '')
        context['selected_course'] = self.request.GET.get('course', '')
        context['selected_year'] = self.request.GET.get('year_level', '')
        context['selected_status'] = self.request.GET.get('clearance_status', '')
        return context


class GenerateReportsView(LoginRequiredMixin, TemplateView):
    template_name = 'core/generate_reports.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        try:
            pc = self.request.user.programchair
            
            # Get date range
            start_date = self.request.GET.get('start_date')
            end_date = self.request.GET.get('end_date')
            if start_date:
                start_date = datetime.strptime(start_date, '%Y-%m-%d')
            if end_date:
                end_date = datetime.strptime(end_date, '%Y-%m-%d')
            
            # Get filters
            report_type = self.request.GET.get('report_type', 'clearance_summary')
            course_filter = self.request.GET.get('course')
            status_filter = self.request.GET.get('status')
            
            # Base queryset with select_related for better performance
            students = Student.objects.filter(program_chair=pc).select_related(
                'user', 'clearance'
            )
            
            if course_filter:
                students = students.filter(course=course_filter)
            
            if status_filter:
                if status_filter == 'cleared':
                    students = students.filter(clearance__is_cleared=True)
                elif status_filter == 'pending':
                    students = students.filter(clearance__is_cleared=False)
            
            # Apply date range if provided
            if start_date and end_date:
                students = students.filter(clearance__cleared_date__range=[start_date, end_date])
            
            # Generate report data based on type
            report_data = None
            if report_type == 'clearance_summary':
                report_data = {
                    'total_students': students.count(),
                    'cleared_students': students.filter(clearance__is_cleared=True).count(),
                    'pending_students': students.filter(clearance__is_cleared=False).count(),
                }
            elif report_type == 'course_statistics':
                report_data = {
                    'course_stats': []
                }
                for course in students.values_list('course', flat=True).distinct():
                    course_students = students.filter(course=course)
                    total = course_students.count()
                    cleared = course_students.filter(clearance__is_cleared=True).count()
                    report_data['course_stats'].append({
                        'course': course,
                        'total': total,
                        'cleared': cleared,
                        'pending': total - cleared,
                        'clearance_rate': round((cleared / total * 100) if total > 0 else 0, 2)
                    })
            elif report_type == 'student_status':
                report_data = {
                    'students': students.values(
                        'user__first_name', 'user__last_name', 'student_id',
                        'course', 'year_level', 'clearance__is_cleared',
                        'clearance__cleared_date'
                    )
                }
            
            context.update({
                'report_type': report_type,
                'start_date': start_date,
                'end_date': end_date,
                'courses': students.values_list('course', flat=True).distinct(),
                'selected_course': course_filter,
                'selected_status': status_filter,
                'report_data': report_data,
                'error_message': None
            })
            
            # Handle export
            export_format = self.request.GET.get('export')
            if export_format and report_data:
                try:
                    if export_format == 'pdf':
                        return self.export_pdf(report_data, report_type)
                    elif export_format == 'excel':
                        return self.export_excel(report_data, report_type)
                except Exception as e:
                    context['error_message'] = f"Error exporting report: {str(e)}"
            
            return context
        except Exception as e:
            context['error_message'] = f"Error generating report: {str(e)}"
            return context

    def export_pdf(self, report_data, report_type):
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename=report_{timezone.now().strftime("%Y%m%d")}.pdf'
        
        doc = SimpleDocTemplate(response, pagesize=letter)
        elements = []
        styles = getSampleStyleSheet()
        
        # Title
        title = Paragraph(f"Clearance Report - {report_type.replace('_', ' ').title()}", styles['Heading1'])
        elements.append(title)
        elements.append(Spacer(1, 12))
        
        # Date
        date_text = Paragraph(f"Generated on {timezone.now().strftime('%B %d, %Y')}", styles['Normal'])
        elements.append(date_text)
        elements.append(Spacer(1, 12))
        
        if report_type == 'clearance_summary':
            data = [
                ['Metric', 'Value'],
                ['Total Students', str(report_data['total_students'])],
                ['Cleared Students', str(report_data['cleared_students'])],
                ['Pending Students', str(report_data['pending_students'])]
            ]
        elif report_type == 'course_statistics':
            data = [['Course', 'Total', 'Cleared', 'Pending', 'Clearance Rate']]
            for stat in report_data['course_stats']:
                data.append([
                    stat['course'],
                    str(stat['total']),
                    str(stat['cleared']),
                    str(stat['pending']),
                    f"{stat['clearance_rate']}%"
                ])
        else:  # student_status
            data = [['Name', 'ID', 'Course', 'Year Level', 'Status', 'Cleared Date']]
            for student in report_data['students']:
                data.append([
                    f"{student['user__first_name']} {student['user__last_name']}",
                    student['student_id'],
                    student['course'],
                    str(student['year_level']),
                    'Cleared' if student['clearance__is_cleared'] else 'Pending',
                    student['clearance__cleared_date'].strftime('%Y-%m-%d') if student['clearance__cleared_date'] else '-'
                ])
        
        # Create table
        table = Table(data)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.green),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 14),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        elements.append(table)
        doc.build(elements)
        return response

    def export_excel(self, report_data, report_type):
        wb = Workbook()
        ws = wb.active
        
        # Write headers and data based on report type
        if report_type == 'clearance_summary':
            headers = ['Metric', 'Value']
            data = [
                ['Total Students', report_data['total_students']],
                ['Cleared Students', report_data['cleared_students']],
                ['Pending Students', report_data['pending_students']]
            ]
        elif report_type == 'course_statistics':
            headers = ['Course', 'Total', 'Cleared', 'Pending', 'Clearance Rate']
            data = [[s['course'], s['total'], s['cleared'], s['pending'], f"{s['clearance_rate']}%"]
                   for s in report_data['course_stats']]
        else:  # student_status
            headers = ['Name', 'ID', 'Course', 'Year Level', 'Status', 'Cleared Date']
            data = [[f"{s['user__first_name']} {s['user__last_name']}", s['student_id'],
                    s['course'], s['year_level'],
                    'Cleared' if s['clearance__is_cleared'] else 'Pending',
                    s['clearance__cleared_date'].strftime('%Y-%m-%d') if s['clearance__cleared_date'] else '-']
                   for s in report_data['students']]
        
        # Write headers
        for col, header in enumerate(headers, 1):
            ws.cell(row=1, column=col, value=header)
        
        # Write data
        for row, row_data in enumerate(data, 2):
            for col, cell_data in enumerate(row_data, 1):
                ws.cell(row=row, column=col, value=cell_data)
        
        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = f'attachment; filename=report_{timezone.now().strftime("%Y%m%d")}.xlsx'
        wb.save(response)
        return response



