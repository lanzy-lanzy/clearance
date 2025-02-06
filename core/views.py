
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from core.models import ClearanceRequest, Clearance, Staff


def home(request):
    return render(request, 'home.html')
@login_required
def dashboard(request):
    """
    Display pending clearance requests.
    If the user is a staff member, show only requests for their office; otherwise all pending requests.
    """
    try:
        staff = request.user.staff
        clearance_requests = ClearanceRequest.objects.filter(office=staff.office, status='pending')
    except Staff.DoesNotExist:
        clearance_requests = ClearanceRequest.objects.filter(status='pending')
    context = {
        'clearance_requests': clearance_requests,
    }
    return render(request, 'core/dashboard.html', context)

@login_required
def update_clearance_request(request, request_id):
    """
    Allows a staff member to approve or deny a clearance request.
    On POST, the request status is updated and the clearance (if it exists) is rechecked.
    """
    clearance_request = get_object_or_404(ClearanceRequest, pk=request_id)
    if request.method == 'POST':
        new_status = request.POST.get('status')
        remarks = request.POST.get('remarks', '')
        # If the user is linked to a Staff account, mark them as the reviewer.
        try:
            clearance_request.reviewed_by = request.user.staff
        except Staff.DoesNotExist:
            pass
        clearance_request.status = new_status
        clearance_request.remarks = remarks
        clearance_request.reviewed_date = timezone.now()
        clearance_request.save()
        # Check overall clearance using the model business logic.
        clearance = getattr(clearance_request.student, 'clearance', None)
        if clearance:
            clearance.check_clearance()
        return redirect('dashboard')
    context = {
        'clearance_request': clearance_request,
    }
    return render(request, 'core/update_clearance_request.html', context)

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from core.models import ClearanceRequest, Clearance, Student
@login_required
def student_dashboard(request):
      """
      Display comprehensive dashboard information for student users including:
      - Student profile details
      - All clearance requests with their full status
      - Final clearance status
      - Dormitory status if applicable
      """
      try:
          student = request.user.student
      except Student.DoesNotExist:
          return redirect('dashboard')

      # Get all clearance requests with related office info
      clearance_requests = student.clearance_requests.select_related('office', 'reviewed_by').all()
    
      # Get or create clearance record
      clearance, created = Clearance.objects.get_or_create(student=student)
    
      # Check if student is a boarder and get dormitory clearance if applicable
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
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib import messages
def register_view(request):
    if request.method == 'POST':
        username = request.POST['username']
        
        # Check if username exists before creating user
        if User.objects.filter(username=username).exists():
            messages.error(request, 'Username already taken. Please choose another.')
            return render(request, 'registration/register.html')
            
        password = request.POST['password']
        password2 = request.POST['password2']
        email = request.POST['email']
        first_name = request.POST['first_name']
        last_name = request.POST['last_name']
        student_id = request.POST['student_id']
        course = request.POST['course']
        year_level = request.POST['year_level']
        is_boarder = request.POST.get('is_boarder') == 'on'

        if password == password2:
            # Create User
            user = User.objects.create_user(
                username=username,
                password=password,
                email=email,
                first_name=first_name,
                last_name=last_name
            )

            # Create Student Profile
            student = Student.objects.create(
                user=user,
                student_id=student_id,
                course=course,
                year_level=year_level,
                is_boarder=is_boarder
            )

            # Create initial clearance requests
            student.create_clearance_requests()

            # Log user in
            login(request, user)
            return redirect('dashboard')
        else:
            messages.error(request, 'Passwords do not match')
    
    return render(request, 'registration/register.html')
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
            # Check if user is a program chair
            if hasattr(user, 'programchair'):
                return redirect('program_chair_dashboard')
            # if the user is a staff (or office staff), redirect to office_dashboard
            elif hasattr(user, 'staff'):
                return redirect('office_dashboard')
            # if the user has a student profile, redirect to student_dashboard
            elif hasattr(user, 'student'):
                return redirect('student_dashboard')
            # fallback redirect if the user is neither
            else:
                return redirect('login')
        else:
            messages.error(request, 'Invalid credentials')
    
    return render(request, 'registration/login.html')
from core.models import Office, Student, ClearanceRequest

@login_required
def create_clearance_requests(request):
    """
    Display a table of all available offices. For each office, if a clearance request
    does not already exist for the logged in student, the student can click a button to
    create the request.
    """
    try:
        student = request.user.student
    except Student.DoesNotExist:
        messages.error(request, "Only students can access this page.")
        return redirect('dashboard')

    offices = Office.objects.all()
    # Build a dictionary mapping office.id to the student’s existing clearance request (if any)
    clearance_requests = {cr.office.id: cr for cr in student.clearance_requests.all()}

    if request.method == "POST":
        office_id = request.POST.get("office_id")
        if office_id:
            office = Office.objects.get(id=office_id)
            cr, created = ClearanceRequest.objects.get_or_create(student=student, office=office)
            if created:
                messages.success(request, f"Clearance request submitted for {office.name}.")
            else:
                messages.warning(request, f"Clearance request for {office.name} already exists.")
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
    # Retrieve the staff object for the logged-in user.
    try:
        staff_member = request.user.staff
    except Staff.DoesNotExist:
        return render(request, 'core/not_authorized.html', {'message': 'You are not authorized to view this page.'})

    current_office = staff_member.office
    clearance_requests = ClearanceRequest.objects.filter(office=current_office)

    if request.method == 'POST':
        request_id = request.POST.get('clearance_request_id')
        action = request.POST.get('action')
        cr = get_object_or_404(ClearanceRequest, id=request_id, office=current_office)
        if action == 'approve':
            cr.status = 'approved'
        elif action == 'deny':
            cr.status = 'denied'
        cr.save()
        return redirect('office_dashboard')

    context = {
        'office': current_office,
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


from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count, Q
from .models import Clearance, Student

class ProgramChairDashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'core/program_chair_dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Overall statistics
        context['total_students'] = Student.objects.count()
        context['pending_clearances'] = Clearance.objects.filter(is_cleared=True, program_chair_approved=False).count()
        context['approved_clearances'] = Clearance.objects.filter(program_chair_approved=True).count()
        
        # Clearance status breakdown
        context['clearance_stats'] = {
            'ready_for_approval': Clearance.objects.filter(is_cleared=True, program_chair_approved=False),
            'recently_approved': Clearance.objects.filter(program_chair_approved=True).order_by('-cleared_date')[:5]
        }
        
        # Course-wise statistics
        context['course_stats'] = Student.objects.values('course').annotate(
            total=Count('id'),
            cleared=Count('clearance', filter=Q(clearance__is_cleared=True))
        )
        
        # Add student list to display on dashboard
        context['students'] = Student.objects.all().order_by('user__first_name')
        
        return context