from django.core.management.base import BaseCommand
from attendance.face_recognition.face_utils import is_deepface_available


class Command(BaseCommand):
    help = 'Check if DeepFace and face recognition dependencies are available in the current environment.'

    def handle(self, *args, **options):
        if is_deepface_available():
            try:
                import deepface
                import tensorflow as tf
                import cv2
                self.stdout.write(self.style.SUCCESS('DeepFace and dependencies seem available.'))
                self.stdout.write(f'DeepFace: {getattr(deepface, "__version__", "unknown")}')
                self.stdout.write(f'TensorFlow: {getattr(tf, "__version__", "unknown")}')
                self.stdout.write(f'OpenCV: {getattr(cv2, "__version__", "unknown")}')
            except Exception as e:
                self.stdout.write(self.style.SUCCESS('DeepFace is importable but a dependency import failed.'))
                self.stdout.write(str(e))
        else:
            self.stdout.write(self.style.WARNING('DeepFace is not available. Install requirements from requirements_face.txt and use a compatible Python version (recommend Python 3.10 or 3.11).'))
