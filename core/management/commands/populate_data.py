from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
import random
from core.models import Office, Staff, Student, ClearanceRequest, Clearance, ProgramChair

class Command(BaseCommand):
    help = 'Populate database with initial sample data including offices, staff, students, and program chair assignments'

    def handle(self, *args, **kwargs):
        # -------------------------
        # Create required offices (DSA updated)
        offices_data = [
            {"name": "SSC", "description": "Student Services Center"},
            {"name": "OSA", "description": "Office of Student Affairs"},
            {"name": "Guidance Office", "description": "Provides student guidance and counseling"},
            {"name": "Library Office", "description": "Manages library resources and clearances"},
            {"name": "Laboratory In-charge", "description": "Oversees laboratory clearances and safety"},
            {"name": "Accounting Office", "description": "Handles student financial clearances"},
            {"name": "Registrar's Office", "description": "Manages academic records and clearances"},
            {"name": "BH In-charge", "description": "Handles boarding house clearances"}
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
        # Create staff members for each updated office
        staff_data = [
            {"username": "ssc_staff", "office_name": "SSC", "role": "SSC Officer"},
            {"username": "osa_staff", "office_name": "OSA", "role": "OSA Coordinator"},
            {"username": "guidance_staff", "office_name": "Guidance Office", "role": "Guidance Counselor"},
            {"username": "library_staff", "office_name": "Library Office", "role": "Librarian"},
            {"username": "lab_incharge", "office_name": "Laboratory In-charge", "role": "Lab In-charge"},
            {"username": "accounting_staff", "office_name": "Accounting Office", "role": "Accounting Officer"},
            {"username": "registrar_staff", "office_name": "Registrar's Office", "role": "Registrar"},
            {"username": "bh_incharge", "office_name": "BH In-charge", "role": "Boarding House Manager", "is_dormitory_owner": True}
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
        # Create multiple ProgramChair (dean) users with designations
        program_chair_data = [
            {
                "username": "pc_set",
                "first_name": "Zenon A.",
                "last_name": "Matos, MIT",
                "email": "pc_set@example.com",
                "designation": "SET DEAN"
            },
            {
                "username": "pc_ste",
                "first_name": "Star Clyde",
                "last_name": "Sebial, Ph.D",
                "email": "pc_ste@example.com",
                "designation": "STE DEAN"
            },
            {
                "username": "pc_socje",
                "first_name": "Mark E.",
                "last_name": "Patalinghug, Ph.D",
                "email": "pc_socje@example.com",
                "designation": "SOCJE DEAN"
            },
            {
                "username": "pc_safes",
                "first_name": "Teonita Y.",
                "last_name": "Velasco, Ed.D",
                "email": "pc_safes@example.com",
                "designation": "SAFES DEAN"
            },
            # The remaining program chairs can remain the same if needed
            {
                "username": "pc_ssb_set",
                "first_name": "SSB SET",
                "last_name": "Dean",
                "email": "pc_ssb_set@example.com",
                "designation": "SSB SET"
            },
            {
                "username": "pc_ssb_ste",
                "first_name": "SSB STE",
                "last_name": "Dean",
                "email": "pc_ssb_ste@example.com",
                "designation": "SSB STE"
            },
            {
                "username": "pc_ssb_socje",
                "first_name": "SSB SOCJE",
                "last_name": "Dean",
                "email": "pc_ssb_socje@example.com",
                "designation": "SSB SOCJE"
            },
            {
                "username": "pc_ssb_safes",
                "first_name": "SSB SAFES",
                "last_name": "Dean",
                "email": "pc_ssb_safes@example.com",
                "designation": "SSB SAFES"
            }
        ]        
        program_chairs_created = []
        for pc_info in program_chair_data:
            # Create or get the program chair user account
            pc_user, created = User.objects.get_or_create(
                username=pc_info["username"],
                defaults={
                    "first_name": pc_info["first_name"],
                    "last_name": pc_info["last_name"],
                    "email": pc_info["email"]
                }
            )
            if created:
                pc_user.set_password("pc_pass123")
                pc_user.save()

            # Create or get the ProgramChair profile
            pc, created = ProgramChair.objects.get_or_create(
                user=pc_user,
                defaults={
                    "designation": pc_info["designation"]
                }
            )
            program_chairs_created.append(pc)
            self.stdout.write(
                self.style.SUCCESS(f"Created Program Chair: {pc.user.username} with designation {pc.designation}")
                if created else self.style.WARNING(f"Program Chair exists: {pc.user.username}")
            )

        # -------------------------
        # Create sample students and assign them a Program Chair (dean)
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
        for idx, student_info in enumerate(students_data):
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
            # -------------------------
            # Assign a Program Chair to the student based on a simple mapping
            # For example, using the student index modulo the number of program chairs available:
            assigned_pc = program_chairs_created[idx % len(program_chairs_created)]
            student.program_chair = assigned_pc
            student.save()
            self.stdout.write(self.style.SUCCESS(
                f"Assigned Program Chair {assigned_pc.user.get_full_name()} ({assigned_pc.designation}) to student: {student.student_id}"
            ))

        # -------------------------
        # For demonstration purposes: Unlock permit for student1 if cleared
        try:
            student = Student.objects.get(user__username="student1")
            clearance, created = Clearance.objects.get_or_create(student=student)
            # Simulate that this student's clearance has been verified
            clearance.is_cleared = True
            clearance.cleared_date = timezone.now()
            clearance.unlock_permit()  # This sets program_chair_approved to True if is_cleared is True
            self.stdout.write(self.style.SUCCESS(f"Permit unlocked for student: {student.student_id}"))
        except Student.DoesNotExist:
            self.stdout.write(self.style.ERROR("Student with username 'student1' does not exist."))

        self.stdout.write(self.style.SUCCESS("Successfully populated offices, staff, students, and program chair data"))