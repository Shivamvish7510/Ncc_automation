import os
import cv2
import face_recognition
import numpy as np
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from accounts.models import Cadet
from attendance.face_recognition.models import FaceEncoding
from attendance.face_recognition.face_utils import detect_faces, get_face_encodings
from PIL import Image
import io
from django.core.files.base import ContentFile

class Command(BaseCommand):
    help = 'Register faces for cadets from a directory of images'

    def add_arguments(self, parser):
        parser.add_argument('directory', type=str, help='Directory containing cadet images')
        parser.add_argument('--ext', type=str, default='.jpg',
                          help='File extension to look for (default: .jpg)')

    def handle(self, *args, **options):
        directory = options['directory']
        ext = options['ext']
        
        if not os.path.isdir(directory):
            raise CommandError(f'Directory {directory} does not exist')
        
        # Get all image files in the directory
        image_files = [f for f in os.listdir(directory) if f.lower().endswith(ext.lower())]
        
        if not image_files:
            raise CommandError(f'No {ext} files found in {directory}')
        
        self.stdout.write(self.style.SUCCESS(f'Found {len(image_files)} image files'))
        
        success_count = 0
        
        for filename in image_files:
            # Extract enrollment number from filename (assuming format: ENROLLMENT_NUMBER.jpg)
            enrollment_number = os.path.splitext(filename)[0].upper()
            
            try:
                cadet = Cadet.objects.get(enrollment_number=enrollment_number)
                
                # Check if face is already registered
                if hasattr(cadet, 'face_encoding'):
                    self.stdout.write(
                        self.style.WARNING(f'Skipping {enrollment_number}: Face already registered')
                    )
                    continue
                
                # Load the image
                image_path = os.path.join(directory, filename)
                image = face_recognition.load_image_file(image_path)
                
                # Detect faces
                face_locations = face_recognition.face_locations(image)
                
                if not face_locations:
                    self.stdout.write(
                        self.style.WARNING(f'No face detected in {filename}')
                    )
                    continue
                
                if len(face_locations) > 1:
                    self.stdout.write(
                        self.style.WARNING(f'Multiple faces detected in {filename}, using the first one')
                    )
                
                # Get face encodings
                face_encodings = face_recognition.face_encodings(image, [face_locations[0]])
                
                if not face_encodings:
                    self.stdout.write(
                        self.style.WARNING(f'Could not extract face features from {filename}')
                    )
                    continue
                
                # Create face encoding
                face_encoding = FaceEncoding(cadet=cadet)
                face_encoding.set_encoding(face_encodings[0])
                
                # Save a thumbnail
                top, right, bottom, left = face_locations[0]
                face_image = image[top:bottom, left:right]
                face_encoding.save_face_thumbnail(face_image)
                
                # Save to database
                face_encoding.save()
                
                success_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'Successfully registered face for {cadet.user.get_full_name()} ({enrollment_number})')
                )
                
            except Cadet.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f'Cadet with enrollment number {enrollment_number} not found')
                )
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'Error processing {filename}: {str(e)}')
                )
        
        self.stdout.write('\n' + '='*50)
        self.stdout.write(self.style.SUCCESS(f'Successfully registered {success_count} out of {len(image_files)} faces'))
