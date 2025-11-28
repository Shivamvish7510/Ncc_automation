import os
import numpy as np
from django.db import models
from django.conf import settings
from django.core.files.base import ContentFile
from accounts.models import Cadet
import pickle
import base64

class FaceEncoding(models.Model):
    """
    Stores face encodings for each cadet
    """
    cadet = models.OneToOneField(
        Cadet, 
        on_delete=models.CASCADE,
        related_name='face_encoding',
        help_text="The cadet this face encoding belongs to"
    )
    
    # Store the face encoding as a binary field
    encoding = models.BinaryField(help_text="Pickled face encoding data")
    
    # Store a thumbnail of the face for verification
    face_thumbnail = models.ImageField(
        upload_to='face_thumbnails/',
        help_text="Thumbnail of the registered face"
    )
    
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this face encoding is active"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'face_encodings'
        verbose_name = 'Face Encoding'
        verbose_name_plural = 'Face Encodings'
    
    def __str__(self):
        return f"Face encoding for {self.cadet.user.get_full_name()}"
    
    def get_encoding_array(self):
        """Convert binary encoding back to numpy array"""
        if not self.encoding:
            return None
        return pickle.loads(self.encoding)
    
    def set_encoding(self, encoding_array):
        """Convert numpy array to binary for storage"""
        self.encoding = pickle.dumps(encoding_array, protocol=pickle.HIGHEST_PROTOCOL)
    
    def save_face_thumbnail(self, image_array):
        """Save a thumbnail of the face"""
        from PIL import Image
        import io
        
        # Convert numpy array to PIL Image
        img = Image.fromarray(image_array.astype('uint8'), 'RGB')
        
        # Create thumbnail (150x150)
        img.thumbnail((150, 150))
        
        # Save to a bytes buffer
        buffer = io.BytesIO()
        img.save(buffer, format='JPEG')
        
        # Save to the ImageField
        filename = f"{self.cadet.enrollment_number}_face.jpg"
        self.face_thumbnail.save(filename, ContentFile(buffer.getvalue()), save=False)


class FaceAttendanceLog(models.Model):
    """
    Logs face recognition attendance attempts
    """
    ATTENDANCE_STATUS = (
        ('SUCCESS', 'Success'),
        ('FAILED', 'Failed'),
        ('UNKNOWN', 'Unknown Face'),
        ('MULTIPLE', 'Multiple Faces Detected'),
        ('NONE', 'No Face Detected'),
    )
    
    session = models.ForeignKey(
        'attendance.AttendanceSession',
        on_delete=models.CASCADE,
        related_name='face_attendance_logs'
    )
    
    cadet = models.ForeignKey(
        Cadet,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='face_attendance_logs'
    )
    
    status = models.CharField(
        max_length=10,
        choices=ATTENDANCE_STATUS,
        help_text="Status of the face recognition attempt"
    )
    
    confidence = models.FloatField(
        null=True,
        blank=True,
        help_text="Confidence score of the face match (0-1)"
    )
    
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        help_text="IP address of the device used for attendance"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'face_attendance_logs'
        ordering = ['-created_at']
        verbose_name = 'Face Attendance Log'
        verbose_name_plural = 'Face Attendance Logs'
    
    def __str__(self):
        return f"{self.get_status_display()} - {self.cadet} - {self.created_at}"
