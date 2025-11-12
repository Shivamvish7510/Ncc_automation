from django.db import models
from django.utils.text import slugify
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone

class Event(models.Model):
    EVENT_TYPE_CHOICES = (
        ('DRILL', 'Drill Practice'),
        ('PARADE', 'Parade'),
        ('CAMP', 'Camp'),
        ('TRAINING', 'Training'),
        ('COMPETITION', 'Competition'),
        ('SOCIAL_SERVICE', 'Social Service'),
        ('CULTURAL', 'Cultural Program'),
        ('SPORTS', 'Sports Event'),
        ('SEMINAR', 'Seminar/Workshop'),
        ('OTHER', 'Other'),
    )
    
    STATUS_CHOICES = (
        ('DRAFT', 'Draft'),
        ('PUBLISHED', 'Published'),
        ('REGISTRATION_OPEN', 'Registration Open'),
        ('REGISTRATION_CLOSED', 'Registration Closed'),
        ('ONGOING', 'Ongoing'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
    )
    
    PRIORITY_CHOICES = (
        ('LOW', 'Low'),
        ('MEDIUM', 'Medium'),
        ('HIGH', 'High'),
        ('CRITICAL', 'Critical'),
    )
    
    # Basic Information
    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True, blank=True)
    description = models.TextField()
    event_type = models.CharField(max_length=20, choices=EVENT_TYPE_CHOICES)
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='MEDIUM')
    
    # Date & Time
    start_date = models.DateField()
    end_date = models.DateField()
    start_time = models.TimeField(blank=True, null=True)
    end_time = models.TimeField(blank=True, null=True)
    registration_start_date = models.DateField(blank=True, null=True)
    registration_end_date = models.DateField(blank=True, null=True)
    
    # Location
    location = models.CharField(max_length=200)
    venue_details = models.TextField(blank=True)
    
    # Organization
    unit = models.ForeignKey('units.Unit', on_delete=models.CASCADE, related_name='events')
    organizer = models.ForeignKey('accounts.Officer', on_delete=models.SET_NULL, null=True, related_name='organized_events')
    coordinators = models.ManyToManyField('accounts.Officer', related_name='coordinated_events', blank=True)
    
    # Participation
    max_participants = models.IntegerField(blank=True, null=True)
    min_participants = models.IntegerField(default=0)
    is_mandatory = models.BooleanField(default=False)
    required_rank = models.CharField(max_length=10, blank=True, null=True)
    
    # Status & Tracking
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='DRAFT')
    is_featured = models.BooleanField(default=False)
    
    # Media
    banner_image = models.ImageField(upload_to='events/banners/', blank=True, null=True)
    attachment = models.FileField(upload_to='events/attachments/', blank=True, null=True)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, related_name='created_events')
    
    class Meta:
        db_table = 'events'
        ordering = ['-start_date', '-created_at']
        indexes = [
            models.Index(fields=['status', 'start_date']),
            models.Index(fields=['unit', 'status']),
            models.Index(fields=['event_type']),
        ]
    
    def save(self, *args, **kwargs):
        # Generate unique slug
        if not self.slug:
            base_slug = slugify(self.title)
            slug = base_slug
            counter = 1
            
            # Check if slug exists, if yes, append number
            while Event.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            
            self.slug = slug
        
        super().save(*args, **kwargs)



    def __str__(self):
        return self.title
    
    def get_registration_count(self):
        return self.registrations.filter(status__in=['APPROVED', 'PENDING']).count()
    
    def get_approved_count(self):
        return self.registrations.filter(status='APPROVED').count()
    
    def can_register(self):
        """Check if registration is currently open"""
        if self.status != 'REGISTRATION_OPEN':
            return False
        
        today = timezone.now().date()
        
        if self.registration_start_date and today < self.registration_start_date:
            return False
        
        if self.registration_end_date and today > self.registration_end_date:
            return False
        
        if self.max_participants:
            if self.get_approved_count() >= self.max_participants:
                return False
        
        return True
    
    def is_past(self):
        return self.end_date < timezone.now().date()
    
    def is_upcoming(self):
        return self.start_date > timezone.now().date()


class EventRegistration(models.Model):
    REGISTRATION_STATUS_CHOICES = (
        ('PENDING', 'Pending Approval'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
        ('WAITLIST', 'Waitlist'),
        ('CANCELLED', 'Cancelled'),
    )
    
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='registrations')
    cadet = models.ForeignKey('accounts.Cadet', on_delete=models.CASCADE, related_name='event_registrations')
    status = models.CharField(max_length=20, choices=REGISTRATION_STATUS_CHOICES, default='PENDING')
    registration_date = models.DateTimeField(auto_now_add=True)
    
    # Approval
    approved_by = models.ForeignKey('accounts.Officer', on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_registrations')
    approval_date = models.DateTimeField(blank=True, null=True)
    rejection_reason = models.TextField(blank=True, null=True)
    
    # Additional Info
    remarks = models.TextField(blank=True, null=True)
    
    class Meta:
        db_table = 'event_registrations'
        unique_together = ('event', 'cadet')
        ordering = ['-registration_date']

    def __str__(self):
        return f"{self.cadet.user.get_full_name()} - {self.event.title}"


class EventParticipation(models.Model):
    PARTICIPATION_STATUS_CHOICES = (
        ('ATTENDED', 'Attended'),
        ('ABSENT', 'Absent'),
        ('PARTIAL', 'Partial Attendance'),
    )
    
    registration = models.OneToOneField(EventRegistration, on_delete=models.CASCADE, related_name='participation')
    attendance_status = models.CharField(max_length=20, choices=PARTICIPATION_STATUS_CHOICES)
    
    # Performance Tracking
    performance_rating = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(10)],
        blank=True, null=True
    )
    position = models.IntegerField(blank=True, null=True)
    award = models.CharField(max_length=200, blank=True)
    
    # Feedback
    feedback = models.TextField(blank=True, null=True)
    evaluated_by = models.ForeignKey('accounts.Officer', on_delete=models.SET_NULL, null=True)
    evaluation_date = models.DateTimeField(blank=True, null=True)
    certificate_issued = models.BooleanField(default=False)
    
    class Meta:
        db_table = 'event_participations'

    def __str__(self):
        return f"{self.registration.cadet.user.get_full_name()} - {self.registration.event.title}"


class EventResource(models.Model):
    RESOURCE_TYPE_CHOICES = (
        ('EQUIPMENT', 'Equipment'),
        ('VENUE', 'Venue'),
        ('TRANSPORT', 'Transportation'),
        ('PERSONNEL', 'Personnel'),
        ('BUDGET', 'Budget'),
        ('OTHER', 'Other'),
    )
    
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='resources')
    resource_type = models.CharField(max_length=20, choices=RESOURCE_TYPE_CHOICES)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    quantity = models.IntegerField(default=1)
    estimated_cost = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    actual_cost = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    is_available = models.BooleanField(default=False)
    
    class Meta:
        db_table = 'event_resources'

    def __str__(self):
        return f"{self.event.title} - {self.name}"


class EventAnnouncement(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='announcements')
    title = models.CharField(max_length=200)
    message = models.TextField()
    is_important = models.BooleanField(default=False)
    created_by = models.ForeignKey('accounts.Officer', on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'event_announcements'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.event.title} - {self.title}"