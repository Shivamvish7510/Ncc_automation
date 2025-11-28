import os
import cv2
import numpy as np
import unittest
from django.test import TestCase, override_settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.conf import settings
from accounts.models import User, Cadet
from attendance.face_recognition.face_utils import (
    detect_faces, get_face_encodings, compare_faces, find_best_match,
    draw_face_boxes, preprocess_image, save_face_image
)
from attendance.face_recognition.models import FaceEncoding

# Path to test images
TEST_IMAGES_DIR = os.path.join(os.path.dirname(__file__), 'test_images')

class FaceRecognitionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        # Create a test user and cadet
        cls.user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            first_name='Test',
            last_name='User',
            role='CADET'
        )
        cls.cadet = Cadet.objects.create(
            user=cls.user,
            enrollment_number='TEST001',
            enrollment_date='2023-01-01',
            college_name='Test College',
            course='B.Tech',
            year_of_study=2,
            roll_number='001',
            parent_name='Parent Name',
            parent_phone='1234567890',
            emergency_contact='0987654321',
            blood_group='O+'
        )
        
        # Load a test image
        test_image_path = os.path.join(TEST_IMAGES_DIR, 'test_face.jpg')
        if os.path.exists(test_image_path):
            with open(test_image_path, 'rb') as f:
                cls.test_image_data = f.read()
            cls.test_image = cv2.imdecode(
                np.frombuffer(cls.test_image_data, np.uint8),
                cv2.IMREAD_COLOR
            )
    
    def test_face_detection(self):
        """Test that faces can be detected in an image"""
        if not hasattr(self, 'test_image'):
            self.skipTest("Test image not found")
        
        # Convert to RGB (OpenCV uses BGR by default)
        rgb_image = cv2.cvtColor(self.test_image, cv2.COLOR_BGR2RGB)
        
        # Detect faces
        face_locations, _ = detect_faces(rgb_image)
        
        # Check that at least one face was detected
        self.assertGreater(len(face_locations), 0, "No faces detected in test image")
    
    def test_face_encoding(self):
        """Test that face encodings can be generated"""
        if not hasattr(self, 'test_image'):
            self.skipTest("Test image not found")
        
        # Convert to RGB
        rgb_image = cv2.cvtColor(self.test_image, cv2.COLOR_BGR2RGB)
        
        # Detect faces
        face_locations, _ = detect_faces(rgb_image)
        self.assertGreater(len(face_locations), 0, "No faces detected")
        
        # Get encodings
        encodings = get_face_encodings(rgb_image, face_locations)
        self.assertEqual(len(encodings), len(face_locations))
        self.assertEqual(len(encodings[0]), 128)  # Face encodings should be 128-dimensional
    
    def test_face_comparison(self):
        """Test that face comparisons work correctly"""
        if not hasattr(self, 'test_image'):
            self.skipTest("Test image not found")
        
        # Convert to RGB
        rgb_image = cv2.cvtColor(self.test_image, cv2.COLOR_BGR2RGB)
        
        # Detect faces and get encodings
        face_locations, _ = detect_faces(rgb_image)
        self.assertGreater(len(face_locations), 0, "No faces detected")
        
        encodings = get_face_encodings(rgb_image, face_locations)
        
        # Compare face with itself (should match)
        matches = compare_faces([encodings[0]], encodings[0])
        self.assertTrue(all(matches), "Face should match itself")
        
        # Create a different encoding (all zeros)
        different_encoding = np.zeros(128)
        matches = compare_faces([different_encoding], encodings[0])
        self.assertFalse(any(matches), "Different encodings should not match")
    
    def test_face_encoding_model(self):
        """Test the FaceEncoding model"""
        if not hasattr(self, 'test_image'):
            self.skipTest("Test image not found")
        
        # Convert to RGB and detect faces
        rgb_image = cv2.cvtColor(self.test_image, cv2.COLOR_BGR2RGB)
        face_locations, _ = detect_faces(rgb_image)
        self.assertGreater(len(face_locations), 0, "No faces detected")
        
        # Get encodings
        encodings = get_face_encodings(rgb_image, face_locations)
        
        # Create a FaceEncoding instance
        face_encoding = FaceEncoding(cadet=self.cadet)
        face_encoding.set_encoding(encodings[0])
        
        # Save a thumbnail
        top, right, bottom, left = face_locations[0]
        face_image = rgb_image[top:bottom, left:right]
        face_encoding.save_face_thumbnail(face_image)
        
        # Save to database
        face_encoding.save()
        
        # Retrieve from database
        saved_encoding = FaceEncoding.objects.get(cadet=self.cadet)
        
        # Check that the encoding was saved and can be retrieved
        self.assertIsNotNone(saved_encoding.encoding)
        self.assertIsNotNone(saved_encoding.face_thumbnail)
        
        # Check that the encoding can be converted back to a numpy array
        encoding_array = saved_encoding.get_encoding_array()
        self.assertEqual(encoding_array.shape, (128,))
        
        # Clean up
        if saved_encoding.face_thumbnail:
            saved_encoding.face_thumbnail.delete()
    
    @override_settings(MEDIA_ROOT=os.path.join(settings.BASE_DIR, 'test_media'))
    def test_save_face_image(self):
        """Test saving a face image to disk"""
        if not hasattr(self, 'test_image'):
            self.skipTest("Test image not found")
        
        # Convert to RGB and detect faces
        rgb_image = cv2.cvtColor(self.test_image, cv2.COLOR_BGR2RGB)
        face_locations, _ = detect_faces(rgb_image)
        self.assertGreater(len(face_locations), 0, "No faces detected")
        
        # Save face image
        file_path = 'test_face_thumbnails/test_face.jpg'
        saved_path = save_face_image(rgb_image, face_locations[0], file_path)
        
        # Check that the file was saved
        self.assertTrue(os.path.exists(os.path.join(settings.MEDIA_ROOT, saved_path)))
        
        # Clean up
        if os.path.exists(os.path.join(settings.MEDIA_ROOT, saved_path)):
            os.remove(os.path.join(settings.MEDIA_ROOT, saved_path))
            os.rmdir(os.path.dirname(os.path.join(settings.MEDIA_ROOT, saved_path)))
    
    def test_preprocess_image(self):
        """Test image preprocessing"""
        if not hasattr(self, 'test_image'):
            self.skipTest("Test image not found")
        
        # Create a test image file
        test_file = SimpleUploadedFile(
            'test.jpg',
            self.test_image_data,
            content_type='image/jpeg'
        )
        
        # Preprocess the image
        processed_image = preprocess_image(test_file)
        
        # Check that the image was processed correctly
        self.assertIsInstance(processed_image, np.ndarray)
        self.assertEqual(processed_image.shape[2], 3)  # Should be RGB
        
        # Test with a large image (should be resized)
        large_image = np.zeros((2000, 2000, 3), dtype=np.uint8)
        _, buffer = cv2.imencode('.jpg', large_image)
        large_file = SimpleUploadedFile(
            'large.jpg',
            buffer.tobytes(),
            content_type='image/jpeg'
        )
        processed_large = preprocess_image(large_file)
        self.assertLessEqual(max(processed_large.shape[:2]), 1000, "Image should be resized")

if __name__ == '__main__':
    unittest.main()
