from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
import random
from core.models import Office, Staff, Student, ClearanceRequest, Clearance, ProgramChair, Payment

class Command(BaseCommand):
    help = 'Populate database with initial sample data including offices, staff, students, and program chair assignments'

    def handle(self, *args, **kwargs):
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

        self.stdout.write(self.style.SUCCESS("\nCreating Offices..."))
        # Create all required offices
        office_data = [
            {"name": "SET", "description": "School of Engineering and Technology"},
            {"name": "STE", "description": "School of Teacher Education"},
            {"name": "SOCJE", "description": "School of Criminal Justice Education"},
            {"name": "SAFES", "description": "School of Agriculture, Forestry and Environmental Sciences"},
            {"name": "SSB SET", "description": "SSB School of Engineering and Technology"},
            {"name": "SSB STE", "description": "SSB School of Teacher Education"},
            {"name": "SSB SOCJE", "description": "SSB School of Criminal Justice Education"},
            {"name": "SSB SAFES", "description": "SSB School of Agriculture, Forestry and Environmental Sciences"},
            {"name": "Dormitory", "description": "Dormitory Office"},
            {"name": "OSA", "description": "Office of Student Affairs"},
            {"name": "Guidance Office", "description": "Student Guidance Office"},
            {"name": "Library Office", "description": "Library Services"},
            {"name": "Laboratory In-charge", "description": "Laboratory Management"},
            {"name": "Accounting Office", "description": "Financial Services"},
            {"name": "Registrar's Office", "description": "Academic Records Management"}
        ]

        offices_created = []
        for office_info in office_data:
            office, created = Office.objects.get_or_create(
                name=office_info["name"],
                defaults={"description": office_info["description"]}
            )
            offices_created.append(office)
            message = f"Created office: {office.name}" if created else f"Office exists: {office.name}"
            self.stdout.write(self.style.SUCCESS(message))

        # Get the dormitory office reference after creation
        dormitory_office = Office.objects.get(name="Dormitory")

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
                    "email": owner_data["email"]
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
            message = f"Created BH Owner: {staff.user.get_full_name()}" if created else f"BH Owner exists: {staff.user.get_full_name()}"
            self.stdout.write(self.style.SUCCESS(message))

        self.stdout.write(self.style.SUCCESS("\nCreating Staff Members..."))
        # Create staff members for each updated office
        staff_data = [
            {"username": "ssc_staff", "office_name": "SET", "role": "SET Officer"},
            {"username": "osa_staff", "office_name": "OSA", "role": "OSA Coordinator"},
            {"username": "guidance_staff", "office_name": "Guidance Office", "role": "Guidance Counselor"},
            {"username": "library_staff", "office_name": "Library Office", "role": "Librarian"},
            {"username": "lab_incharge", "office_name": "Laboratory In-charge", "role": "Lab In-charge"},
            {"username": "accounting_staff", "office_name": "Accounting Office", "role": "Accounting Officer"},
            {"username": "registrar_staff", "office_name": "Registrar's Office", "role": "Registrar"}
        ]
        for staff_info in staff_data:
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

            office = Office.objects.get(name=staff_info["office_name"])
            staff, created = Staff.objects.get_or_create(
                user=user,
                defaults={
                    "office": office,
                    "role": staff_info["role"],
                    "is_dormitory_owner": staff_info.get("is_dormitory_owner", False)
                }
            )
            message = f"Created Staff: {staff.user.username} for {staff.office.name}" if created else f"Staff exists: {staff.user.username}"
            self.stdout.write(self.style.SUCCESS(message))

        self.stdout.write(self.style.SUCCESS("\nCreating Program Chairs..."))
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
            }
        ]

        program_chairs_created = []
        for pc_info in program_chair_data:
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

            pc, created = ProgramChair.objects.get_or_create(
                user=pc_user,
                defaults={
                    "designation": pc_info["designation"]
                }
            )
            program_chairs_created.append(pc)
            message = f"Created Program Chair: {pc.user.username} with designation {pc.designation}" if created else f"Program Chair exists: {pc.user.username}"
            self.stdout.write(self.style.SUCCESS(message))

        self.stdout.write(self.style.SUCCESS("\nCreating Boarder Students..."))
        # Create boarder students with assignments to BH owners
        boarder_students_data = [
            {
                "username": "boarder1",
                "password": "student123",
                "first_name": "Alice",
                "last_name": "Brown",
                "email": "alice.brown@student.edu",
                "student_id": "2023-B001",
                "course": "Computer Science",
                "year_level": 2,
                "bh_owner": bh_owners[0],
                "payment_amount": 5000.00
            },
            {
                "username": "boarder2",
                "password": "student123",
                "first_name": "Bob",
                "last_name": "Wilson",
                "email": "bob.wilson@student.edu",
                "student_id": "2023-B002",
                "course": "Engineering",
                "year_level": 3,
                "bh_owner": bh_owners[0],
                "payment_amount": 4500.00
            },
            {
                "username": "boarder3",
                "password": "student123",
                "first_name": "Carol",
                "last_name": "Davis",
                "email": "carol.davis@student.edu",
                "student_id": "2023-B003",
                "course": "Business",
                "year_level": 2,
                "bh_owner": bh_owners[1],
                "payment_amount": 5500.00
            }
        ]
        # Mapping between boarder student usernames and designated program chair usernames.
        designated_pc = {
            "boarder1": "pc_set",
            "boarder2": "pc_ste",
            "boarder3": "pc_socje"
        }
        for student_data in boarder_students_data:
            user, created = User.objects.get_or_create(
                username=student_data["username"],
                defaults={
                    "first_name": student_data["first_name"],
                    "last_name": student_data["last_name"],
                    "email": student_data["email"]
                }
            )
            if created:
                user.set_password("password")
                user.save()

            student, created = Student.objects.get_or_create(
                user=user,
                defaults={
                    "student_id": student_data["student_id"],
                    "course": student_data["course"],
                    "year_level": student_data["year_level"],
                    "is_boarder": True,
                    "dormitory_owner": student_data["bh_owner"]
                }
            )
            if created:
                # Create clearance requests for the student
                student.create_clearance_requests()
                Payment.objects.create(
                    student=student,
                    amount=student_data["payment_amount"],
                    is_paid=False
                )
                Clearance.objects.get_or_create(student=student)
                self.stdout.write(self.style.SUCCESS(
                    f"Created boarder student: {student.full_name} ({student.student_id}) assigned to BH Owner: {student_data['bh_owner'].user.get_full_name()}"
                ))
            else:
                self.stdout.write(self.style.WARNING(
                    f"Boarder student exists: {student.full_name} ({student.student_id})"
                ))

            # Assign the designated Program Chair if applicable
            pc_username = designated_pc.get(student_data["username"])
            if pc_username:
                assigned_pc = ProgramChair.objects.filter(user__username=pc_username).first()
                if assigned_pc:
                    student.program_chair = assigned_pc
                    student.save()
                    self.stdout.write(self.style.SUCCESS(
                        f"Assigned Program Chair {assigned_pc.user.get_full_name()} ({assigned_pc.designation}) to student: {student.student_id}"
                    ))

        self.stdout.write(self.style.SUCCESS("\nUpdating Clearance Requests and Unlocking Permits..."))
        # For testing purposes, approve all clearance requests and unlock printing
        for student in Student.objects.all():
            # Ensure a Clearance record exists for the student.
            clearance, created = Clearance.objects.get_or_create(student=student)
            for clearance_request in student.clearance_requests.all():
                # Use the student's dormitory owner for Dormitory clearances.
                if clearance_request.office.name == "Dormitory":
                    staff = student.dormitory_owner
                else:
                    staff = Staff.objects.filter(office=clearance_request.office).first()
                if staff:
                    clearance_request.approve(staff)
            clearance.check_clearance()  # Sets is_cleared to True if no pending/denied requests
            clearance.program_chair_approved = True  # Unlock permit for printing
            clearance.save()
            self.stdout.write(self.style.SUCCESS(
                f"Unlocked printing for student: {student.full_name}"
            ))

        self.stdout.write(self.style.SUCCESS("\nData population completed successfully!"))