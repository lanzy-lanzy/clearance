
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from core.models import ClearanceRequest, Clearance, Staff, Student, Office,ProgramChair, User
from django.db.models import Count, Q
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from core.models import Student, Clearance

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

def register_view(request):
    # Get all program chairs for the dropdown if needed
    program_chairs = ProgramChair.objects.all()
    
    if request.method == 'POST':
        username = request.POST['username']
    
        if User.objects.filter(username=username).exists():
            messages.error(request, 'Username already taken. Please choose another.')
            return render(request, 'registration/register.html', {'program_chairs': program_chairs})
        
        password = request.POST['password']
        password2 = request.POST['password2']
        email = request.POST['email']
        first_name = request.POST['first_name']
        last_name = request.POST['last_name']
        student_id = request.POST['student_id']
        course = request.POST['course']
        year_level = request.POST['year_level']
        is_boarder = request.POST.get('is_boarder') == 'on'
        selected_pc_id = request.POST.get('program_chair')

        if password == password2:
            # Create User (this triggers the post_save signal which creates the Student profile automatically)
            user = User.objects.create_user(
                username=username,
                password=password,
                email=email,
                first_name=first_name,
                last_name=last_name
            )
        
            # Now retrieve the auto-created student profile and update it
            student = user.student
            student.student_id = student_id
            student.course = course
            student.year_level = year_level
            student.is_boarder = is_boarder
            student.save()

            # Create initial clearance requests if needed
            student.create_clearance_requests()

            # Auto-assign the selected Program Chair to the student if provided
            if selected_pc_id:
                program_chair = ProgramChair.objects.filter(id=selected_pc_id).first()
                if program_chair:
                    student.program_chair = program_chair
                    student.save()
                else:
                    messages.error(request, "Selected Program Chair not found.")
                    return render(request, 'registration/register.html', {'program_chairs': program_chairs})
            
            login(request, user)
            return redirect('student_dashboard')
        else:
            messages.error(request, 'Passwords do not match')
    
    return render(request, 'registration/register.html', {'program_chairs': program_chairs})
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
      try:
          student = request.user.student
      except Student.DoesNotExist:
          messages.error(request, "Only students can access this page.")
          return redirect('dashboard')

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
              cr.notes = request.POST.get('notes')  # Save the denial reason
            
          cr.reviewed_by = staff_member
          cr.reviewed_date = timezone.now()
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


class ProgramChairDashboardView(LoginRequiredMixin, TemplateView):
      template_name = 'core/program_chair_dashboard.html'

      def get_context_data(self, **kwargs):
          context = super().get_context_data(**kwargs)
          pc = self.request.user.programchair  # current program chair

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

          # Course-wise statistics and the detailed student list filtered by program chair
          context['course_stats'] = Student.objects.filter(
              user__is_staff=False,
              program_chair=pc
          ).values('course').annotate(
              total=Count('id'),
              cleared=Count('clearance', filter=Q(clearance__is_cleared=True))
          )

          # List of assigned students for this program chair
          context['students'] = Student.objects.filter(
              user__is_staff=False,
              program_chair=pc
          ).order_by('user__first_name')

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
