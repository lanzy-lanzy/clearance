from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from core.models import Office, Staff, Student, ClearanceRequest, Clearance

class Command(BaseCommand):
    help = 'Populate database with initial sample data including offices, staff, and students.'

    def handle(self, *args, **kwargs):
        # -------------------------
        # Create required offices
        offices_data = [
            {"name": "Admissions", "description": "Handles student admissions and records"},
            {"name": "Library", "description": "Manages library clearances and dues"},
            {"name": "Finance", "description": "Handles financial clearances and payments"},
            {"name": "Dormitory", "description": "Manages dormitory clearances"},
            {"name": "Department", "description": "Academic department clearances"},
            {"name": "Student Affairs", "description": "Student activities and conduct clearances"}
        ]
        for office_info in offices_data:
            office, created = Office.objects.get_or_create(
                name=office_info["name"],
                defaults={"description": office_info["description"]}
            )
            self.stdout.write(
                self.style.SUCCESS(f"Created Office: {office.name}") if created
                else self.style.WARNING(f"Office exists: {office.name}")
            )

        # -------------------------
        # Create staff members for each office
        staff_data = [
            {"username": "admissions_staff", "office_name": "Admissions", "role": "Admissions Officer"},
            {"username": "library_staff", "office_name": "Library", "role": "Librarian"},
            {"username": "finance_staff", "office_name": "Finance", "role": "Finance Officer"},
            {"username": "dorm_owner", "office_name": "Dormitory", "role": "Dormitory Manager", "is_dormitory_owner": True},
            {"username": "dept_staff", "office_name": "Department", "role": "Department Head"},
            {"username": "student_affairs", "office_name": "Student Affairs", "role": "Student Affairs Officer"}
        ]
        for staff_info in staff_data:
            # Create or get user account
            user, created = User.objects.get_or_create(
                username=staff_info["username"],
                defaults={
                    "first_name": staff_info["username"].split('_')[0].title(),
                    "last_name": "Staff",
                    "email": f"{staff_info['username']}@example.com"
                }
            )
            if created:
                user.set_password("staffpass123")
                user.save()

            # Get corresponding office
            office = Office.objects.get(name=staff_info["office_name"])
            # Create or get staff record
            staff, created = Staff.objects.get_or_create(
                user=user,
                defaults={
                    "office": office,
                    "role": staff_info["role"],
                    "is_dormitory_owner": staff_info.get("is_dormitory_owner", False)
                }
            )
            self.stdout.write(
                self.style.SUCCESS(f"Created Staff: {staff.user.username} for {staff.office.name}")
                if created else self.style.WARNING(f"Staff exists: {staff.user.username}")
            )

        # -------------------------
        # Create sample students and their clearance data
        students_data = [
            {
                "username": "student1",
                "password": "student123",
                "first_name": "John",
                "last_name": "Doe",
                "email": "john.doe@student.edu",
                "student_id": "2023-0001",
                "course": "Computer Science",
                "year_level": 3,
                "is_boarder": True
            },
            {
                "username": "student2",
                "password": "student123",
                "first_name": "Jane",
                "last_name": "Smith",
                "email": "jane.smith@student.edu",
                "student_id": "2023-0002",
                "course": "Engineering",
                "year_level": 2,
                "is_boarder": False
            },
            {
                "username": "student3",
                "password": "student123",
                "first_name": "Mike",
                "last_name": "Johnson",
                "email": "mike.johnson@student.edu",
                "student_id": "2023-0003",
                "course": "Business Administration",
                "year_level": 4,
                "is_boarder": True
            }
        ]
        for student_info in students_data:
            # Create or get user account for the student
            user, created = User.objects.get_or_create(
                username=student_info["username"],
                defaults={
                    "first_name": student_info["first_name"],
                    "last_name": student_info["last_name"],
                    "email": student_info["email"]
                }
            )
            if created:
                user.set_password(student_info["password"])
                user.save()

            # Create or get student record
            student, created = Student.objects.get_or_create(
                user=user,
                defaults={
                    "student_id": student_info["student_id"],
                    "course": student_info["course"],
                    "year_level": student_info["year_level"],
                    "is_boarder": student_info["is_boarder"]
                }
            )
            if created:
                # Create clearance requests for the student (using the model method)
                student.create_clearance_requests()
                # Create an initial final clearance record
                Clearance.objects.get_or_create(student=student)
                self.stdout.write(self.style.SUCCESS(
                    f"Created student: {student.user.get_full_name()} ({student.student_id})"
                ))
            else:
                self.stdout.write(self.style.WARNING(
                    f"Student exists: {student.user.get_full_name()} ({student.student_id})"
                ))

        self.stdout.write(self.style.SUCCESS("Successfully populated offices, staff, and student data"))