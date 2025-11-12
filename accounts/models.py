from django.db import models
from django.contrib.auth.models import AbstractUser
from guardian.shortcuts import assign_perm

class User(AbstractUser):
    ROLE_CHOICES = (
        ('ADMIN', 'Administrator'),
        ('OFFICER', 'NCC Officer'),
        ('CADET', 'Cadet'),
    )
    
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='CADET')
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    profile_picture = models.ImageField(upload_to='profiles/', blank=True, null=True)
    date_of_birth = models.DateField(blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active_member = models.BooleanField(default=True)

    class Meta:
        db_table = 'users'
        permissions = (
            ('can_view_all_cadets', 'Can view all cadets'),
            ('can_manage_unit', 'Can manage unit'),
            ('can_mark_attendance', 'Can mark attendance'),
            ('can_create_events', 'Can create events'),
        )

    def save(self, *args, **kwargs):
        # Automatically set role to ADMIN for superusers
        if self.is_superuser or self.is_staff:
            self.role = 'ADMIN'
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.username} - {self.get_role_display()}"

class Officer(models.Model):
    RANK_CHOICES = (
        ('SUO', 'Senior Under Officer'),
        ('JUO', 'Junior Under Officer'),
        ('SGT', 'Sergeant'),
        ('LT', 'Lieutenant'),
        ('CAPT', 'Captain'),
        ('MAJ', 'Major'),
    )
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='officer_profile')
    rank = models.CharField(max_length=10, choices=RANK_CHOICES)
    unit = models.ForeignKey('units.Unit', on_delete=models.SET_NULL, null=True, related_name='officers')
    employee_id = models.CharField(max_length=50, unique=True)
    joining_date = models.DateField()
    specialization = models.CharField(max_length=200, blank=True)
    
    class Meta:
        db_table = 'officers'

    def __str__(self):
        return f"{self.get_rank_display()} {self.user.get_full_name()}"


class Cadet(models.Model):
    RANK_CHOICES = (
        ('CDT', 'Cadet'),
        ('LCPL', 'Lance Corporal'),
        ('CPL', 'Corporal'),
        ('SGT', 'Sergeant'),
        ('SUO', 'Senior Under Officer'),
    )
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='cadet_profile')
    rank = models.CharField(max_length=10, choices=RANK_CHOICES, default='CDT')
    unit = models.ForeignKey('units.Unit', on_delete=models.SET_NULL, null=True, related_name='cadets')
    enrollment_number = models.CharField(max_length=50, unique=True)
    enrollment_date = models.DateField()
    
    college_name = models.CharField(max_length=200)
    course = models.CharField(max_length=100)
    year_of_study = models.IntegerField()
    roll_number = models.CharField(max_length=50)
    
    parent_name = models.CharField(max_length=200)
    parent_phone = models.CharField(max_length=15)
    parent_email = models.EmailField(blank=True, null=True)
    emergency_contact = models.CharField(max_length=15)
    
    blood_group = models.CharField(max_length=5, blank=True)
    height = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    weight = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    assigned_officer = models.ForeignKey(Officer, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_cadets')
    
    class Meta:
        db_table = 'cadets'

    def __str__(self):
        return f"{self.enrollment_number} - {self.user.get_full_name()}"
    
    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)
        if is_new:
            assign_perm('view_cadet', self.user, self)