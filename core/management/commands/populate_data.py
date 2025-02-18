from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
import random
from core.models import (
    Office, Staff, Student, ClearanceRequest, 
    Clearance, ProgramChair, Dean, Course
)

class Command(BaseCommand):
    help = 'Populate database with initial sample data for all models'

    def handle(self, *args, **kwargs):
        # Get or set current school year and semester
        current_year = timezone.now().year
        school_year = f"{current_year}-{current_year + 1}"
        semester = "1ST"  # You can modify this as needed: "1ST", "2ND", or "SUM"

        self.stdout.write(self.style.SUCCESS("\nCreating Admin User..."))
        # Create superuser/admin account
        admin_user, created = User.objects.get_or_create(
            username="admin",
            defaults={
                "email": "admin@example.com",
                "is_staff": True,
                "is_superuser": True,
                "first_name": "Admin",
                "last_name": "User"
            }
        )
        if created:
            admin_user.set_password("admin123")
            admin_user.save()
            self.stdout.write(self.style.SUCCESS("Created admin user"))
        else:
            self.stdout.write(self.style.WARNING("Admin user already exists"))

        # Create Deans
        self.stdout.write(self.style.SUCCESS("\nCreating Deans..."))
        deans_data = [
            {
                "name": "SET DEAN",  # Changed to match the format used in JavaScript
                "description": "School of Engineering and Technology"
            },
            {
                "name": "STE DEAN",
                "description": "School of Teacher Education"
            },
            {
                "name": "SOCJE DEAN",
                "description": "School of Criminal Justice Education"
            },
            {
                "name": "SAFES DEAN",
                "description": "School of Agriculture, Forestry and Environmental Sciences"
            }
        ]

        deans = []
        for dean_data in deans_data:
            dean, created = Dean.objects.get_or_create(
                name=dean_data["name"],
                defaults={"description": dean_data["description"]}
            )
            deans.append(dean)
            self.stdout.write(self.style.SUCCESS(f"{'Created' if created else 'Found'} dean: {dean.name}"))

        # Create Courses
        self.stdout.write(self.style.SUCCESS("\nCreating Courses..."))
        courses_data = [
            # SET Courses
            {"code": "BSIT", "name": "Bachelor of Science in Information Technology", "dean": "SET DEAN"},
            {"code": "BSCS", "name": "Bachelor of Science in Computer Science", "dean": deans[0]},
            # STE Courses
            {"code": "BPED", "name": "Bachelor of Physical Education", "dean": "STE DEAN"},
            {"code": "BEED", "name": "Bachelor of Elementary Education", "dean": "STE DEAN"},
            {"code": "BSED", "name": "Bachelor of Secondary Education", "dean": "STE DEAN"},
            {"code": "BAELS", "name": "Bachelor of Arts in English Language Studies", "dean": "STE DEAN"},
            {"code": "BSMATH", "name": "Bachelor of Science in Mathematics", "dean": "STE DEAN"},
            # SOCJE Courses
            {"code": "BSCRIM", "name": "Bachelor of Science in Criminology", "dean": "SOCJE DEAN"},
            {"code": "BSISM", "name": "Bachelor of Science in Industrial Security Management", "dean": "SOCJE DEAN"},
            # SAFES Courses
            {"code": "BSA", "name": "Bachelor of Science in Agriculture", "dean": "SAFES DEAN"},
            {"code": "BSAES", "name": "Bachelor of Science in Agricultural Engineering Science", "dean": "SAFES DEAN"},
            {"code": "BCF", "name": "Bachelor of Science in Commercial Farming", "dean": "SAFES DEAN"},
        ]

        for course_data in courses_data:
            dean = Dean.objects.get(name=course_data["dean"])
            course, created = Course.objects.get_or_create(
                code=course_data["code"],
                defaults={
                    "name": course_data["name"],
                    "dean": dean
                }
            )
            self.stdout.write(self.style.SUCCESS(f"{'Created' if created else 'Found'} course: {course.code}"))

        self.stdout.write(self.style.SUCCESS("\nCreating Offices..."))
        self.create_offices()

        # Get the dormitory office reference after creation
        dormitory_office = Office.objects.get(name="DORMITORY")

        self.stdout.write(self.style.SUCCESS("\nCreating BH Owners..."))
        # Create multiple BH owners
        bh_owners_data = [
            {
                "username": "bh_owner1",
                "first_name": "John",
                "last_name": "Smith",
                "email": "john.smith@bh.com",
                "role": "BH Owner 1"
            },
            {
                "username": "bh_owner2",
                "first_name": "Mary",
                "last_name": "Johnson",
                "email": "mary.johnson@bh.com",
                "role": "BH Owner 2"
            }
        ]

        bh_owners = []
        for owner_data in bh_owners_data:
            user, created = User.objects.get_or_create(
                username=owner_data["username"],
                defaults={
                    "first_name": owner_data["first_name"],
                    "last_name": owner_data["last_name"],
                    "email": owner_data["email"],
                    "is_active": True
                }
            )
            if created:
                user.set_password("bhowner123")
                user.save()

            staff, created = Staff.objects.get_or_create(
                user=user,
                defaults={
                    "office": dormitory_office,
                    "role": owner_data["role"],
                    "is_dormitory_owner": True
                }
            )
            bh_owners.append(staff)
            self.stdout.write(self.style.SUCCESS(f"{'Created' if created else 'Found'} BH Owner: {staff.user.get_full_name()}"))

        self.stdout.write(self.style.SUCCESS("\nCreating Program Chairs..."))
        program_chair_data = [
            {
                "username": "pc_set",
                "first_name": "Zenon A.",
                "last_name": "Matos, MIT",
                "email": "pc_set@example.com",
                "dean": deans[0]  # SET Dean
            },
            {
                "username": "pc_ste",
                "first_name": "Star Clyde",
                "last_name": "Sebial, Ph.D",
                "email": "pc_ste@example.com",
                "dean": deans[1]  # STE Dean
            },
            {
                "username": "pc_socje",
                "first_name": "Mark E.",
                "last_name": "Patalinghug, Ph.D",
                "email": "pc_socje@example.com",
                "dean": deans[2]  # SOCJE Dean
            },
            {
                "username": "pc_safes",
                "first_name": "Teonita Y.",
                "last_name": "Velasco, Ed.D",
                "email": "pc_safes@example.com",
                "dean": deans[3]  # SAFES Dean
            }
        ]

        program_chairs = []
        for pc_info in program_chair_data:
            user, created = User.objects.get_or_create(
                username=pc_info["username"],
                defaults={
                    "first_name": pc_info["first_name"],
                    "last_name": pc_info["last_name"],
                    "email": pc_info["email"],
                    "is_active": True
                }
            )
            if created:
                user.set_password("pc_pass123")
                user.save()

            pc, created = ProgramChair.objects.get_or_create(
                user=user,
                defaults={
                    "dean": pc_info["dean"]
                }
            )
            program_chairs.append(pc)
            self.stdout.write(self.style.SUCCESS(f"{'Created' if created else 'Found'} Program Chair: {pc.user.get_full_name()}"))

        self.stdout.write(self.style.SUCCESS("\nCreating Sample Students..."))
        student_data = [
            {
                "username": "set_student1",
                "password": "student123",
                "first_name": "John",
                "last_name": "Doe",
                "email": "john.doe@student.edu",
                "student_id": "2023-SET-001",
                "course": Course.objects.get(code="BSIT"),
                "year_level": 3,
                "is_boarder": True,
                "bh_owner": bh_owners[0],
                "program_chair": program_chairs[0],
                "school_year": school_year,
                "semester": semester
            },
            {
                "username": "ste_student1",
                "password": "student123",
                "first_name": "Jane",
                "last_name": "Smith",
                "email": "jane.smith@student.edu",
                "student_id": "2023-STE-001",
                "course": Course.objects.get(code="BSED"),
                "year_level": 2,
                "is_boarder": True,
                "bh_owner": bh_owners[1],
                "program_chair": program_chairs[1],
                "school_year": school_year,
                "semester": semester
            }
        ]

        for student_info in student_data:
            user, created = User.objects.get_or_create(
                username=student_info["username"],
                defaults={
                    "first_name": student_info["first_name"],
                    "last_name": student_info["last_name"],
                    "email": student_info["email"],
                    "is_active": True
                }
            )
            if created:
                user.set_password(student_info["password"])
                user.save()

            student, created = Student.objects.get_or_create(
                user=user,
                defaults={
                    "student_id": student_info["student_id"],
                    "course": student_info["course"],
                    "year_level": student_info["year_level"],
                    "is_boarder": student_info["is_boarder"],
                    "program_chair": student_info["program_chair"],
                    "dormitory_owner": student_info["bh_owner"] if student_info["is_boarder"] else None,
                    "is_approved": True,
                    "approval_date": timezone.now(),
                    "approval_admin": admin_user
                }
            )

            if created:
                # Create clearance requests with school year and semester
                student.create_clearance_requests(
                    school_year=student_info["school_year"],
                    semester=student_info["semester"]
                )
                
                # Create clearance record with school year and semester
                Clearance.objects.get_or_create(
                    student=student,
                    school_year=student_info["school_year"],
                    semester=student_info["semester"],
                    defaults={'is_cleared': False}
                )
                
                self.stdout.write(self.style.SUCCESS(f"Created student: {student.user.get_full_name()} ({student.student_id})"))
            else:
                self.stdout.write(self.style.WARNING(f"Student exists: {student.user.get_full_name()} ({student.student_id})"))

        self.stdout.write(self.style.SUCCESS("\nData population completed successfully!"))

    def create_offices(self):
        created_count = 0
        offices = [
            # Base offices that all students must pass
            {
                "name": "OSA",
                "description": "Office of Student Affairs",
                "office_type": "OTHER"
            },
            {
                "name": "DSA",
                "description": "Department of Student Affairs",
                "office_type": "OTHER"
            },
            {
                "name": "SSC",
                "description": "Student Services Center",
                "office_type": "OTHER"
            },
            {
                "name": "LIBRARY",
                "description": "Library Services",
                "office_type": "OTHER"
            },
            {
                "name": "LABORATORY",
                "description": "Laboratory Services",
                "office_type": "OTHER"
            },
            {
                "name": "ACCOUNTING OFFICE",
                "description": "Accounting Office",
                "office_type": "OTHER"
            },
            {
                "name": "REGISTRAR OFFICE",
                "description": "Registrar Office",
                "office_type": "OTHER"
            },
            {
                "name": "Guidance Office",
                "description": "Guidance and Counseling Office",
                "office_type": "OTHER"
            },
            {
                "name": "DORMITORY",
                "description": "Dormitory/Boarding House Office",
                "office_type": "OTHER"
            },
            # School-specific SSB offices
            {
                "name": "SSB SET",
                "description": "Student Services Bureau - School of Engineering and Technology",
                "office_type": "SSB SET"
            },
            {
                "name": "SSB STE",
                "description": "Student Services Bureau - School of Teacher Education",
                "office_type": "SSB STE"
            },
            {
                "name": "SSB SOCJE",
                "description": "Student Services Bureau - School of Criminal Justice Education",
                "office_type": "SSB SOCJE"
            },
            {
                "name": "SSB SAFES",
                "description": "Student Services Bureau - School of Agriculture, Forestry and Environmental Sciences",
                "office_type": "SSB SAFES"
            },
            # Dean offices (for permit printing only)
            {
                "name": "SET DEAN",
                "description": "School of Engineering and Technology Dean's Office",
                "office_type": "SET"
            },
            {
                "name": "STE DEAN",
                "description": "School of Teacher Education Dean's Office",
                "office_type": "STE"
            },
            {
                "name": "SOCJE DEAN",
                "description": "School of Criminal Justice Education Dean's Office",
                "office_type": "SOCJE"
            },
            {
                "name": "SAFES DEAN",
                "description": "School of Agriculture, Forestry and Environmental Sciences Dean's Office",
                "office_type": "SAFES"
            }
        ]

        for office_data in offices:
            office, created = Office.objects.get_or_create(
                name=office_data["name"],
                defaults={
                    "description": office_data["description"],
                    "office_type": office_data["office_type"]
                }
            )
            if created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f"Created office: {office.name}"))
            else:
                self.stdout.write(self.style.WARNING(f"Office exists: {office.name}"))

        self.stdout.write(self.style.SUCCESS(f"\nCreated {created_count} new offices"))
