# Generated by Django 5.1.6 on 2025-02-18 21:59

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Dean',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, unique=True)),
                ('logo', models.ImageField(blank=True, null=True, upload_to='dean_logos/')),
                ('description', models.TextField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
        ),
        migrations.CreateModel(
            name='Course',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('code', models.CharField(max_length=10, unique=True)),
                ('name', models.CharField(max_length=100)),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('dean', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='courses', to='core.dean')),
            ],
            options={
                'ordering': ['code'],
            },
        ),
        migrations.CreateModel(
            name='Office',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255, unique=True)),
                ('office_type', models.CharField(choices=[('SET', 'SET'), ('STE', 'STE'), ('SOCJE', 'SOCJE'), ('SAFES', 'SAFES'), ('SSB SET', 'SSB SET'), ('SSB STE', 'SSB STE'), ('SSB SOCJE', 'SSB SOCJE'), ('SSB SAFES', 'SSB SAFES'), ('OTHER', 'OTHER')], default='OTHER', max_length=50)),
                ('description', models.TextField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('affiliated_dean', models.ForeignKey(blank=True, help_text='Associate this office with a specific dean (program)', null=True, on_delete=django.db.models.deletion.SET_NULL, to='core.dean')),
            ],
        ),
        migrations.CreateModel(
            name='ProgramChair',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('profile_picture', models.ImageField(blank=True, null=True, upload_to='program_chair_profiles/')),
                ('dean', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='core.dean')),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='Staff',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('role', models.CharField(blank=True, max_length=100, null=True)),
                ('is_dormitory_owner', models.BooleanField(default=False)),
                ('office', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='staff', to='core.office')),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='Student',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('student_id', models.CharField(max_length=20, unique=True)),
                ('year_level', models.IntegerField()),
                ('is_boarder', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('is_approved', models.BooleanField(default=False)),
                ('approval_date', models.DateTimeField(blank=True, null=True)),
                ('profile_picture', models.ImageField(blank=True, null=True, upload_to='student_profiles/')),
                ('approval_admin', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='approved_students', to=settings.AUTH_USER_MODEL)),
                ('course', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='core.course')),
                ('dormitory_owner', models.ForeignKey(blank=True, limit_choices_to={'is_dormitory_owner': True}, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='students_dorm', to='core.staff')),
                ('program_chair', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='students', to='core.programchair')),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='UserProfile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('profile_picture', models.ImageField(blank=True, null=True, upload_to='admin_profiles/')),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='ClearanceRequest',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('school_year', models.CharField(max_length=9)),
                ('semester', models.CharField(choices=[('1ST', 'First Semester'), ('2ND', 'Second Semester'), ('SUM', 'Summer')], max_length=3)),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('approved', 'Approved'), ('denied', 'Denied')], default='pending', max_length=10)),
                ('remarks', models.TextField(blank=True, null=True)),
                ('request_date', models.DateTimeField(auto_now_add=True)),
                ('reviewed_date', models.DateTimeField(blank=True, null=True)),
                ('notes', models.TextField(blank=True, help_text='Reasons for pending or denied clearance.', null=True)),
                ('office', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='clearance_requests', to='core.office')),
                ('reviewed_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='core.staff')),
                ('student', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='clearance_requests', to='core.student')),
            ],
            options={
                'ordering': ['-school_year', '-semester', '-request_date'],
                'unique_together': {('student', 'office', 'school_year', 'semester')},
            },
        ),
        migrations.CreateModel(
            name='Clearance',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('school_year', models.CharField(max_length=9)),
                ('semester', models.CharField(choices=[('1ST', 'First Semester'), ('2ND', 'Second Semester'), ('SUM', 'Summer')], max_length=3)),
                ('is_cleared', models.BooleanField(default=False)),
                ('cleared_date', models.DateTimeField(blank=True, null=True)),
                ('program_chair_approved', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('student', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='clearances', to='core.student')),
            ],
            options={
                'ordering': ['-school_year', '-semester'],
                'unique_together': {('student', 'school_year', 'semester')},
            },
        ),
    ]
