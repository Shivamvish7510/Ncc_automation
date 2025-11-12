from django.db import models

class Achievement(models.Model):
    ACHIEVEMENT_TYPE_CHOICES = (
        ('MEDAL', 'Medal'),
        ('TROPHY', 'Trophy'),
        ('AWARD', 'Award'),
        ('RECOGNITION', 'Recognition'),
        ('DISTINCTION', 'Distinction'),
        ('HONOR', 'Honor'),
        ('SCHOLARSHIP', 'Scholarship'),
    )
    
    LEVEL_CHOICES = (
        ('UNIT', 'Unit Level'),
        ('GROUP', 'Group Level'),
        ('DIRECTORATE', 'Directorate Level'),
        ('NATIONAL', 'National Level'),
        ('INTERNATIONAL', 'International Level'),
    )
    
    cadet = models.ForeignKey('accounts.Cadet', on_delete=models.CASCADE, related_name='achievements')
    
    title = models.CharField(max_length=200)
    achievement_type = models.CharField(max_length=20, choices=ACHIEVEMENT_TYPE_CHOICES)
    level = models.CharField(max_length=20, choices=LEVEL_CHOICES, default='UNIT')
    
    description = models.TextField()
    
    date_awarded = models.DateField()
    awarded_by = models.CharField(max_length=200, help_text='Authority who awarded this achievement')
    
    # Related entities
    event = models.ForeignKey('events.Event', on_delete=models.SET_NULL, null=True, blank=True, related_name='achievements')
    training = models.ForeignKey('training.Training', on_delete=models.SET_NULL, null=True, blank=True, related_name='achievements')
    
    # Details
    position = models.IntegerField(blank=True, null=True, help_text='Position/Rank achieved (for competitions)')
    citation = models.TextField(blank=True, help_text='Official citation or commendation text')
    
    # Media
    certificate_file = models.FileField(upload_to='achievements/', blank=True, null=True)
    photo = models.ImageField(upload_to='achievements/photos/', blank=True, null=True)
    
    # Verification
    verified = models.BooleanField(default=False)
    verified_by = models.ForeignKey('accounts.Officer', on_delete=models.SET_NULL, null=True, blank=True, related_name='verified_achievements')
    verification_date = models.DateField(blank=True, null=True)
    
    remarks = models.TextField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'achievements'
        ordering = ['-date_awarded']

    def __str__(self):
        return f"{self.title} - {self.cadet.user.get_full_name()}"
