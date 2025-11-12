from django.db import models

class Notification(models.Model):
    NOTIFICATION_TYPE_CHOICES = (
        ('EVENT', 'Event Notification'),
        ('ATTENDANCE', 'Attendance Alert'),
        ('CERTIFICATE', 'Certificate Update'),
        ('TRAINING', 'Training Notification'),
        ('ACHIEVEMENT', 'Achievement Update'),
        ('GENERAL', 'General Announcement'),
        ('REGISTRATION', 'Registration Status'),
        ('REMINDER', 'Reminder'),
    )
    
    PRIORITY_CHOICES = (
        ('LOW', 'Low'),
        ('MEDIUM', 'Medium'),
        ('HIGH', 'High'),
        ('URGENT', 'Urgent'),
    )
    
    title = models.CharField(max_length=200)
    message = models.TextField()
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPE_CHOICES)
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='MEDIUM')
    
    recipient = models.ForeignKey('accounts.User', on_delete=models.CASCADE, related_name='notifications')
    sender = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='sent_notifications')
    
    # Related entities
    event = models.ForeignKey('events.Event', on_delete=models.SET_NULL, null=True, blank=True)
    training = models.ForeignKey('training.Training', on_delete=models.SET_NULL, null=True, blank=True)
    
    # Status
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(blank=True, null=True)
    
    # Action URL (optional)
    action_url = models.CharField(max_length=500, blank=True, help_text='URL to redirect when clicked')
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'notifications'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient', 'is_read']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"{self.title} - {self.recipient.username}"
    
    def mark_as_read(self):
        if not self.is_read:
            self.is_read = True
            from django.utils import timezone
            self.read_at = timezone.now()
            self.save()


# Bulk Notification Model
class BulkNotification(models.Model):
    TARGET_CHOICES = (
        ('ALL_CADETS', 'All Cadets'),
        ('ALL_OFFICERS', 'All Officers'),
        ('UNIT', 'Specific Unit'),
        ('YEAR', 'Specific Year'),
        ('ALL', 'Everyone'),
    )
    
    title = models.CharField(max_length=200)
    message = models.TextField()
    notification_type = models.CharField(max_length=20, choices=Notification.NOTIFICATION_TYPE_CHOICES)
    priority = models.CharField(max_length=10, choices=Notification.PRIORITY_CHOICES, default='MEDIUM')
    
    target_audience = models.CharField(max_length=20, choices=TARGET_CHOICES)
    target_unit = models.ForeignKey('units.Unit', on_delete=models.SET_NULL, null=True, blank=True)
    target_year = models.IntegerField(blank=True, null=True)
    
    sent_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True)
    sent_at = models.DateTimeField(auto_now_add=True)
    
    recipients_count = models.IntegerField(default=0)
    
    class Meta:
        db_table = 'bulk_notifications'
        ordering = ['-sent_at']

    def __str__(self):
        return f"{self.title} - {self.get_target_audience_display()}"
