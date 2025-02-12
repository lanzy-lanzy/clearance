from django.db import models
from django.contrib.auth.models import User
from django.dispatch import receiver 
from django.db.models.signals import post_save
from django.utils import timezone

class Office(models.Model):
    """Represents different offices handling clearance."""
    OFFICE_TYPES = [
        ('SET', 'SET'),
        ('STE', 'STE'),
        ('SOCJE', 'SOCJE'),
        ('SAFES', 'SAFES'),
        ('SSB SET', 'SSB SET'),
        ('SSB STE', 'SSB STE'),
        ('SSB SOCJE', 'SSB SOCJE'),
        ('SSB SAFES', 'SSB SAFES'),
        ('OTHER', 'OTHER'),
    ]
    name = models.CharField(max_length=255, unique=True)
    office_type = models.CharField(max_length=50, choices=OFFICE_TYPES, default='OTHER')
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class Staff(models.Model):
    """Represents staff members assigned to different offices."""
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    office = models.ForeignKey(Office, on_delete=models.CASCADE, related_name='staff')
    role = models.CharField(max_length=100, blank=True, null=True)
    is_dormitory_owner = models.BooleanField(default=False)  # 🔹 New field for dormitory manager

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.office.name}"

# Add ProgramChair model

import os
from django.conf import settings

class ProgramChair(models.Model):
    """Represents a program chair (dean) user responsible for final clearance approval."""
    DESIGNATION_CHOICES = [
        ('SET DEAN', 'School of Engineering and Technology (BSIT)'),
        ('STE DEAN', 'School of Teacher Education (BPED,BEED,BSED,BAELS,BSMATH)'),
        ('SOCJE DEAN', 'School of Criminal Justice Education (BSCRIM,BSISM)'),
        ('SAFES DEAN', 'School of Agriculture Forestry and Environmental Science (BSA,BSAES,BCF)'),
    ]
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    designation = models.CharField(max_length=50, choices=DESIGNATION_CHOICES)

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.get_designation_display()}"

    def get_logo_url(self):
        # Map each designation to a specific static logo path
        logo_mapping = {
            'SET DEAN': 'img/logo_set.png',
            'STE DEAN': 'img/logo_ste.png',
            'SOCJE DEAN': 'img/logo_socje.png',
            'SAFES DEAN': 'img/logo_safes.png',
        }

        designated_logo = logo_mapping.get(self.designation)
        if designated_logo:
            # Construct the absolute path of the logo file
            logo_path = os.path.join(settings.BASE_DIR, 'static', designated_logo)
            if os.path.exists(logo_path):
                return designated_logo
        # Return default permit logo if designated logo is missing
        return 'img/permit_logo.png'

class Student(models.Model):
    """Represents students requesting clearance."""
    COURSE_CHOICES = {
        'SET DEAN': [
            ('BSIT', 'Bachelor of Science in Information Technology'),
        ],
        'STE DEAN': [
            ('BPED', 'Bachelor in Physical Education'),
            ('BEED', 'Bachelor in Elementary Education'),
            ('BSED', 'Bachelor of Secondary Education'),
            ('BAELS', 'Bachelor of Arts in English Language Studies'),
            ('BSMATH', 'Bachelor of Science in Mathematics'),
        ],
        'SOCJE DEAN': [
            ('BSCRIM', 'Bachelor of Science in Criminology'),
            ('BSISM', 'Bachelor of Science in Industrial Security Management'),
        ],
        'SAFES DEAN': [
            ('BSA', 'Bachelor of Science in Agriculture'),
            ('BSAES', 'Bachelor of Science in Agricultural Engineering Science'),
            ('BCF', 'Bachelor in Community Forestry'),
        ],
    }

    student_id = models.CharField(max_length=20, unique=True)
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    course = models.CharField(max_length=255)
    year_level = models.IntegerField()
    is_boarder = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    program_chair = models.ForeignKey(ProgramChair, on_delete=models.SET_NULL, null=True, blank=True, related_name="students")
    dormitory_owner = models.ForeignKey(Staff, on_delete=models.SET_NULL, null=True, blank=True, related_name="students_dorm", limit_choices_to={'is_dormitory_owner': True})
    is_approved = models.BooleanField(default=False)
    approval_date = models.DateTimeField(null=True, blank=True)
    approval_admin = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_students')

    @property
    def full_name(self):
            return self.user.get_full_name()

    def __str__(self):
            return f"{self.full_name} ({self.student_id})"
    
    def approve_student(self, admin_user):
        """Approve a student's registration"""
        self.is_approved = True
        self.approval_date = timezone.now()
        self.approval_admin = admin_user
        self.save()

    def create_clearance_requests(self):
            """Creates clearance requests for all required offices, including Dormitory if boarder."""
            from core.models import Office, ClearanceRequest  # import here to avoid circular imports
            required_offices = Office.objects.all()
            dormitory_office = Office.objects.filter(name="Dormitory").first()
            if self.is_boarder and dormitory_office:
                # Ensure the dormitory office is included (it might already be in required_offices)
                required_offices = required_offices | Office.objects.filter(id=dormitory_office.id)
            for office in required_offices:
                ClearanceRequest.objects.get_or_create(student=self, office=office)
@receiver(post_save, sender=User)
def create_student_profile(sender, instance, created, **kwargs):
    # Remove automatic student creation since we'll handle it in the view
    pass

class ClearanceRequest(models.Model):
    """Represents clearance requests for students dynamically per office."""
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='clearance_requests')
    office = models.ForeignKey(Office, on_delete=models.CASCADE, related_name='clearance_requests')
    status_choices = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('denied', 'Denied'),
    ]
    status = models.CharField(max_length=10, choices=status_choices, default='pending')
    remarks = models.TextField(blank=True, null=True)
    reviewed_by = models.ForeignKey(Staff, on_delete=models.SET_NULL, null=True, blank=True)
    request_date = models.DateTimeField(auto_now_add=True)
    reviewed_date = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True, null=True, help_text="Reasons for pending or denied clearance.")

    def __str__(self):
        return f"{self.student} - {self.office} ({self.status})"

    def approve(self, staff):
        """Approve the clearance request with proper permission checks."""
        if self.office.name == "Dormitory":
            if not staff.is_dormitory_owner:
                raise PermissionError("Only dormitory owners can approve dormitory clearances.")
            if self.student.dormitory_owner != staff:
                raise PermissionError("You can only approve clearances for your assigned students.")
        
        self.status = "approved"
        self.reviewed_by = staff
        self.reviewed_date = timezone.now()
        self.save()

    def deny(self, staff, reason):
        """Deny the clearance request with proper permission checks."""
        if self.office.name == "Dormitory":
            if not staff.is_dormitory_owner:
                raise PermissionError("Only dormitory owners can deny dormitory clearances.")
            if self.student.dormitory_owner != staff:
                raise PermissionError("You can only deny clearances for your assigned students.")
        
        self.status = "denied"
        self.reviewed_by = staff
        self.notes = reason
        self.reviewed_date = timezone.now()
        self.save()

class Clearance(models.Model):
    """Represents the final clearance status of a student."""
    student = models.OneToOneField(Student, on_delete=models.CASCADE, related_name='clearance')
    is_cleared = models.BooleanField(default=False)
    cleared_date = models.DateTimeField(null=True, blank=True)
    program_chair_approved = models.BooleanField(default=False)

    def check_clearance(self):
        """Checks if all clearance requests are approved before allowing the program chair to unlock the permit."""
        pending_requests = self.student.clearance_requests.filter(status='pending').exists()
        denied_requests = self.student.clearance_requests.filter(status='denied').exists()
        if not pending_requests and not denied_requests:
            self.is_cleared = True
            self.cleared_date = models.DateTimeField(auto_now=True)
            self.save()

    def unlock_permit(self):
        """Allows the program chair to approve the final clearance for printing."""
        if self.is_cleared:
            self.program_chair_approved = True
            self.save()

    def __str__(self):
        return f"{self.student} - {'Cleared' if self.is_cleared else 'Not Cleared'} - {'Permit Unlocked' if self.program_chair_approved else 'Permit Locked'}"


from django.db import models
from django.contrib.auth.models import User

# ...

class Payment(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=8, decimal_places=2, default=0.00)
    is_paid = models.BooleanField(default=False)
    payment_date = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        status = "Paid" if self.is_paid else "Unpaid"
        return f"{self.student.full_name} - {status} - {self.amount}"
