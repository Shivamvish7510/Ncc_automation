from django.db import models
import uuid

class Certificate(models.Model):
    CERTIFICATE_TYPE_CHOICES = (
        ('A', 'A Certificate'),
        ('B', 'B Certificate'),
        ('C', 'C Certificate'),
        ('PARTICIPATION', 'Participation Certificate'),
        ('ACHIEVEMENT', 'Achievement Certificate'),
        ('MERIT', 'Merit Certificate'),
        ('TRAINING', 'Training Certificate'),
        ('APPRECIATION', 'Appreciation Certificate'),
    )
    
    STATUS_CHOICES = (
        ('DRAFT', 'Draft'),
        ('ISSUED', 'Issued'),
        ('REVOKED', 'Revoked'),
    )
    
    certificate_type = models.CharField(max_length=20, choices=CERTIFICATE_TYPE_CHOICES)
    certificate_number = models.CharField(max_length=100, unique=True, blank=True)
    
    cadet = models.ForeignKey('accounts.Cadet', on_delete=models.CASCADE, related_name='certificates')
    
    title = models.CharField(max_length=200, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    
    issued_date = models.DateField(blank=True, null=True)
    issued_by = models.ForeignKey('accounts.Officer', on_delete=models.SET_NULL, null=True, related_name='issued_certificates')
    valid_until = models.DateField(blank=True, null=True)
    
    # Related entities
    event = models.ForeignKey('events.Event', on_delete=models.SET_NULL, null=True, blank=True, related_name='certificates')
    training = models.ForeignKey('training.Training', on_delete=models.SET_NULL, null=True, blank=True, related_name='certificates')
    
    # Assessment details
    grade = models.CharField(max_length=5, blank=True)
    score = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    
    # Files
    certificate_file = models.FileField(upload_to='certificates/', blank=True, null=True)
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='DRAFT')
    
    remarks = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)
    
    class Meta:
        db_table = 'certificates'
        ordering = ['-issued_date']

    def save(self, *args, **kwargs):
        if not self.certificate_number:
            # Generate unique certificate number
            year = self.issued_date.year if self.issued_date else 2024
            type_code = self.certificate_type[:3].upper()
            unique_id = str(uuid.uuid4())[:8].upper()
            self.certificate_number = f"NCC/{year}/{type_code}/{unique_id}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.certificate_number} - {self.cadet.user.get_full_name()}"
