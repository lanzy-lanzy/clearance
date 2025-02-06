from django.db import models
from django.contrib.auth.models import User

class Office(models.Model):
    """Represents different offices handling clearance."""
    name = models.CharField(max_length=255, unique=True)
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

from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

class Student(models.Model):
    """Represents students requesting clearance."""
    student_id = models.CharField(max_length=20, unique=True)
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    course = models.CharField(max_length=255)
    year_level = models.IntegerField()
    is_boarder = models.BooleanField(default=False)  # Field to check if student is a boarder
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def full_name(self):
        return self.user.get_full_name()

    def __str__(self):
        return f"{self.full_name} ({self.student_id})"

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
    # Modify this logic if you want to auto create a Student profile for every new user;
    # here we'll only auto-create if no Student already exists.
    if created and not hasattr(instance, 'student'):
        # You may wish to add default values or conditions. This is an example:
        Student.objects.create(
            user=instance,
            student_id=f"UID{instance.id}",
            course="Undeclared",
            year_level=1,
            is_boarder=False
        )
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
        """Approve the clearance request, only dormitory owner can approve dormitory requests."""
        if self.office.name == "Dormitory":
            if not staff.is_dormitory_owner:
                raise PermissionError("Only the dormitory owner can approve dormitory clearances.")
        self.status = "approved"
        self.reviewed_by = staff
        self.reviewed_date = models.DateTimeField(auto_now=True)
        self.save()

    def deny(self, staff, reason):
        """Deny the clearance request with a reason."""
        if self.office.name == "Dormitory":
            if not staff.is_dormitory_owner:
                raise PermissionError("Only the dormitory owner can deny dormitory clearances.")
        self.status = "denied"
        self.reviewed_by = staff
        self.notes = reason
        self.reviewed_date = models.DateTimeField(auto_now=True)
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

