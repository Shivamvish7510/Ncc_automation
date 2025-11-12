from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator

class Training(models.Model):
    TRAINING_TYPE_CHOICES = (
        ('WEAPON', 'Weapon Training'),
        ('MAP', 'Map Reading'),
        ('FIRST_AID', 'First Aid'),
        ('DRILL', 'Drill Training'),
        ('PHYSICAL', 'Physical Training'),
        ('LEADERSHIP', 'Leadership Training'),
        ('ADVENTURE', 'Adventure Training'),
        ('COMMUNICATION', 'Communication Skills'),
        ('OTHER', 'Other'),
    )
    
    STATUS_CHOICES = (
        ('SCHEDULED', 'Scheduled'),
        ('ONGOING', 'Ongoing'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
    )
    
    title = models.CharField(max_length=200)
    description = models.TextField()
    training_type = models.CharField(max_length=20, choices=TRAINING_TYPE_CHOICES)
    duration_hours = models.IntegerField()
    instructor = models.ForeignKey('accounts.Officer', on_delete=models.SET_NULL, null=True, related_name='conducted_trainings')
    
    start_date = models.DateField()
    end_date = models.DateField()
    
    unit = models.ForeignKey('units.Unit', on_delete=models.CASCADE, related_name='trainings')
    location = models.CharField(max_length=200)
    venue_details = models.TextField(blank=True)
    
    max_participants = models.IntegerField(blank=True, null=True)
    prerequisites = models.TextField(blank=True, help_text='Any prerequisites for this training')
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='SCHEDULED')
    syllabus = models.FileField(upload_to='trainings/syllabus/', blank=True, null=True)
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'trainings'
        ordering = ['-start_date']

    def __str__(self):
        return self.title
    
    def get_enrollment_count(self):
        return self.enrollments.count()
    
    def get_completion_rate(self):
        total = self.enrollments.count()
        if total == 0:
            return 0
        completed = self.enrollments.filter(completion_status=True).count()
        return round((completed / total * 100), 2)


class TrainingEnrollment(models.Model):
    training = models.ForeignKey(Training, on_delete=models.CASCADE, related_name='enrollments')
    cadet = models.ForeignKey('accounts.Cadet', on_delete=models.CASCADE, related_name='training_enrollments')
    enrollment_date = models.DateTimeField(auto_now_add=True)
    
    attendance_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    completion_status = models.BooleanField(default=False)
    
    # Assessment
    theory_score = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    practical_score = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    overall_score = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    grade = models.CharField(max_length=5, blank=True)
    
    feedback = models.TextField(blank=True, null=True)
    remarks = models.TextField(blank=True, null=True)
    
    certificate_issued = models.BooleanField(default=False)
    certificate_number = models.CharField(max_length=100, blank=True)
    certificate_date = models.DateField(blank=True, null=True)
    
    class Meta:
        db_table = 'training_enrollments'
        unique_together = ('training', 'cadet')
        ordering = ['-enrollment_date']

    def __str__(self):
        return f"{self.cadet.user.get_full_name()} - {self.training.title}"
    
    def calculate_grade(self):
        """Calculate grade based on overall score"""
        if self.overall_score:
            if self.overall_score >= 90:
                return 'A+'
            elif self.overall_score >= 80:
                return 'A'
            elif self.overall_score >= 70:
                return 'B+'
            elif self.overall_score >= 60:
                return 'B'
            elif self.overall_score >= 50:
                return 'C'
            else:
                return 'F'
        return ''