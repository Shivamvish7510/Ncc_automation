from django.db import models
from django.utils import timezone

class AttendanceSession(models.Model):
    SESSION_TYPE_CHOICES = (
        ('DAILY', 'Daily Parade'),
        ('WEEKLY', 'Weekly Training'),
        ('SPECIAL', 'Special Event'),
        ('CAMP', 'Camp'),
    )
    
    title = models.CharField(max_length=200)
    session_type = models.CharField(max_length=20, choices=SESSION_TYPE_CHOICES)
    date = models.DateField(default=timezone.now)
    start_time = models.TimeField()
    end_time = models.TimeField()
    unit = models.ForeignKey('units.Unit', on_delete=models.CASCADE, related_name='sessions')
    created_by = models.ForeignKey('accounts.Officer', on_delete=models.SET_NULL, null=True)
    is_mandatory = models.BooleanField(default=True)
    location = models.CharField(max_length=200)
    notes = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'attendance_sessions'
        ordering = ['-date', '-start_time']

    def __str__(self):
        return f"{self.title} - {self.date}"
    
    def get_attendance_stats(self):
        total = self.attendances.count()
        present = self.attendances.filter(status='PRESENT').count()
        absent = self.attendances.filter(status='ABSENT').count()
        late = self.attendances.filter(status='LATE').count()
        return {
            'total': total,
            'present': present,
            'absent': absent,
            'late': late,
            'percentage': round((present / total * 100) if total > 0 else 0, 2)
        }


class Attendance(models.Model):
    STATUS_CHOICES = (
        ('PRESENT', 'Present'),
        ('ABSENT', 'Absent'),
        ('LATE', 'Late'),
        ('EXCUSED', 'Excused'),
        ('ON_LEAVE', 'On Leave'),
    )
    
    session = models.ForeignKey(AttendanceSession, on_delete=models.CASCADE, related_name='attendances')
    cadet = models.ForeignKey('accounts.Cadet', on_delete=models.CASCADE, related_name='attendances')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='ABSENT')
    marked_by = models.ForeignKey('accounts.Officer', on_delete=models.SET_NULL, null=True)
    check_in_time = models.TimeField(blank=True, null=True)
    remarks = models.TextField(blank=True, null=True)
    marked_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'attendance'
        unique_together = ('session', 'cadet')
        ordering = ['-session__date']

    def __str__(self):
        return f"{self.cadet.user.get_full_name()} - {self.session.date} - {self.status}"

