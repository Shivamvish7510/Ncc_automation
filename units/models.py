from django.db import models

class Unit(models.Model):
    WING_CHOICES = (
        ('ARMY', 'Army Wing'),
        ('NAVY', 'Navy Wing'),
        ('AIR', 'Air Wing'),
    )
    
    name = models.CharField(max_length=200)
    wing = models.CharField(max_length=10, choices=WING_CHOICES)
    unit_code = models.CharField(max_length=50, unique=True)
    location = models.CharField(max_length=200)
    contact_email = models.EmailField()
    contact_phone = models.CharField(max_length=15)
    established_date = models.DateField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'units'
        ordering = ['name']

    def __str__(self):
        return f"{self.name} - {self.get_wing_display()}"
