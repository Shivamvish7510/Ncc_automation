import os
import cv2
import numpy as np
from PIL import Image, ImageDraw
from django.conf import settings
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
import io
import logging

logger = logging.getLogger(__name__)

class FaceRecognitionError(Exception):
    """Custom exception for face recognition errors"""
    pass

# Initialize DeepFace with default settings
DETECTOR_BACKEND = 'opencv'  # Options: 'opencv', 'ssd', 'dlib', 'mtcnn', 'retinaface', 'mediapipe'
MODEL_NAME = 'Facenet512'  # Options: 'VGG-Face', 'Facenet', 'Facenet512', 'OpenFace', 'DeepFace', 'DeepID', 'ArcFace', 'Dlib', 'SFace'
DISTANCE_METRIC = 'cosine'  # Options: 'cosine', 'euclidean', 'euclidean_l2'
ENFORCE_DETECTION = True
ALIGN = True
NORMALIZATION = 'Facenet'  # Options: 'base', 'raw', 'Facenet', 'Facenet2018', 'VGGFace', 'VGGFace2', 'ArcFace'

_detector = None
_model = None

def _import_deepface():
    """Import deepface modules lazily and return useful references.
    Raises FaceRecognitionError if deepface or dependencies are missing.
    """
    try:
        from deepface import DeepFace
        # deepface >= 1.x refactored commons: there is no 'functions' module exported
        # Import only modules we actually use. Keep compatibility with older versions
        # by not relying on a 'functions' symbol that may not exist.
        from deepface.modules import representation
        from deepface.modules import detection as detection_module
        return DeepFace, representation, detection_module
    except Exception as e:
        logger.error(f"DeepFace import error: {e}")
        # Detect common TF / Keras-related errors and give a tailored hint
        hint = ""
        msg = str(e)
        if 'tf_keras' in msg or 'tf-keras' in msg or 'tf_keras' in repr(e).lower():
            hint = " It looks like TensorFlow requires the 'tf-keras' package; try `pip install tf-keras` or downgrade TensorFlow to a supported version (e.g. 2.11)."
        elif 'tensorflow' in msg:
            hint = " Consider installing a TensorFlow version supported by DeepFace (recommend 2.11 or 2.12), or check compatibility with your Python version."

        raise FaceRecognitionError(
            "DeepFace or one of its dependencies is not available. "
            "Install requirements or configure the environment." + hint
        ) from e


def is_deepface_available():
    """Return True if DeepFace and its dependencies are importable.

    This helper lets views determine whether to enable camera-based
    flow in templates. It avoids throwing exceptions to the caller; use
    it to show user-friendly fallbacks when heavy dependencies aren't
    installed (for example in lightweight developer environments).
    """
    try:
        _import_deepface()
        return True
    except FaceRecognitionError:
        return False

def get_detector():
    global _detector
    if _detector is None:
        DeepFace, representation, detection_module = _import_deepface()
        try:
            build = getattr(detection_module, "build_model", None)
            if callable(build):
                try:
                    _detector = build(DETECTOR_BACKEND)
                except Exception:
                    _detector = None
            else:
                _detector = None
        except Exception as e:
            logger.error(f"Error initializing detector: {e}")
            raise FaceRecognitionError("Failed to initialize face detector") from e
    return _detector

def get_model():
    global _model
    if _model is None:
        DeepFace, representation, detection_module = _import_deepface()
        try:
            _model = DeepFace.build_model(MODEL_NAME)
        except Exception as e:
            logger.error(f"Error initializing DeepFace model: {e}")
            raise FaceRecognitionError("Failed to initialize face recognition model") from e
    return _model

def detect_faces(image_array):
    """
    Detect faces in an image and return their locations using DeepFace
    
    Args:
        image_array: numpy array of the image in RGB format
        
    Returns:
        tuple: (face_locations, rgb_image) where face_locations is a list of (top, right, bottom, left) tuples
    """
    try:
        # Convert to RGB if needed
        if len(image_array.shape) == 2:  # If grayscale
            rgb_image = cv2.cvtColor(image_array, cv2.COLOR_GRAY2RGB)
        elif image_array.shape[2] == 4:  # If RGBA
            rgb_image = cv2.cvtColor(image_array, cv2.COLOR_RGBA2RGB)
        elif image_array.shape[2] == 3:  # If BGR (OpenCV default)
            rgb_image = cv2.cvtColor(image_array, cv2.COLOR_BGR2RGB)
        else:
            rgb_image = image_array
        
        # Detect faces using DeepFace detection module
        DeepFace, representation, detection_module = _import_deepface()
        detect = getattr(detection_module, 'detect_faces', None)
        if callable(detect):
            face_objs = detect(DETECTOR_BACKEND, rgb_image, align=ALIGN)
        else:
            detector_instance = get_detector()
            if detector_instance is None:
                raise FaceRecognitionError("No available face detector (incompatible deepface version)")
            # Older API fallback: detector_instance.detect_faces expects only the image
            # and returns a list of FacialAreaRegion objects
            face_objs = detector_instance.detect_faces(rgb_image)
        
        # Convert to (top, right, bottom, left) format
        face_locations = []
        for face_obj in face_objs:
            # Newer API returns dict with 'facial_area'. Older API may return a 2-tuple/list.
            x = y = w = h = None
            if isinstance(face_obj, dict) and 'facial_area' in face_obj:
                fa = face_obj['facial_area']
                # fa may be dict
                if isinstance(fa, dict):
                    x, y, w, h = fa['x'], fa['y'], fa['w'], fa['h']
                else:
                    # might be an object with attributes
                    x, y, w, h = fa.x, fa.y, fa.w, fa.h
            elif hasattr(face_obj, 'facial_area'):
                # DetectedFace object has facial_area attribute (a FacialAreaRegion object)
                fa = getattr(face_obj, 'facial_area')
                if isinstance(fa, dict):
                    x, y, w, h = fa['x'], fa['y'], fa['w'], fa['h']
                else:
                    x, y, w, h = fa.x, fa.y, fa.w, fa.h
            elif hasattr(face_obj, 'x') and hasattr(face_obj, 'y') and hasattr(face_obj, 'w') and hasattr(face_obj, 'h'):
                # face_obj itself is a FacialAreaRegion object
                x, y, w, h = face_obj.x, face_obj.y, face_obj.w, face_obj.h
            elif isinstance(face_obj, (list, tuple)) and len(face_obj) >= 4 and all(isinstance(v, (int, float, np.integer, np.floating)) for v in face_obj[:4]):
                # case where detector returned a plain tuple (x,y,w,h) or similar
                x, y, w, h = face_obj[0], face_obj[1], face_obj[2], face_obj[3]
            elif isinstance(face_obj, (list, tuple)) and len(face_obj) > 1:
                fa = face_obj[1]
                if isinstance(fa, dict):
                    x, y, w, h = fa['x'], fa['y'], fa['w'], fa['h']
                elif hasattr(fa, 'x'):
                    x, y, w, h = fa.x, fa.y, fa.w, fa.h
                else:
                    # try interpreting nested structures like (img, (x,y,w,h))
                    try:
                        x, y, w, h = fa[0], fa[1], fa[2], fa[3]
                    except Exception:
                        raise FaceRecognitionError('Unexpected face object structure from DeepFace detector')
            elif isinstance(face_obj, (list, tuple)) and len(face_obj) >= 4 and all(isinstance(v, (int, float, np.integer, np.floating)) for v in face_obj[:4]):
                # case where detector returned a plain tuple (x,y,w,h) or similar
                x, y, w, h = face_obj[0], face_obj[1], face_obj[2], face_obj[3]
            elif hasattr(face_obj, '__array__') and len(np.array(face_obj).shape) == 1 and np.array(face_obj).shape[0] >= 4:
                arr = np.array(face_obj).flatten()
                x, y, w, h = int(arr[0]), int(arr[1]), int(arr[2]), int(arr[3])
            else:
                # Log the object type and a brief representation for debugging
                try:
                    obj_type = type(face_obj).__name__
                    if isinstance(face_obj, dict):
                        obj_keys = list(face_obj.keys())
                    else:
                        obj_keys = [k for k in dir(face_obj) if not k.startswith('_')][:10]
                    logger.debug(f"Unexpected DeepFace detector object structure: type={obj_type}, keys={obj_keys}")
                except Exception:
                    logger.debug("Unexpected DeepFace detector object structure and failed to get keys")
                raise FaceRecognitionError(f'Unexpected face object structure from DeepFace detector (type={type(face_obj)})')
            top = max(0, y)
            right = min(rgb_image.shape[1], x + w)
            bottom = min(rgb_image.shape[0], y + h)
            left = max(0, x)
            face_locations.append((top, right, bottom, left))
            
        return face_locations, rgb_image
    except Exception as e:
        logger.error(f"Error detecting faces: {str(e)}")
        raise FaceRecognitionError(f"Error detecting faces: {str(e)}")

def get_face_encodings(image_array, face_locations=None):
    """
    Get face embeddings for the detected faces
    
    Args:
        image_array: numpy array of the image in RGB format
        face_locations: Optional list of face locations (if None, will detect faces)
        
    Returns:
        list: List of face embeddings (vectors)
    """
    try:
        # Convert to RGB if needed
        if len(image_array.shape) == 2:  # If grayscale
            rgb_image = cv2.cvtColor(image_array, cv2.COLOR_GRAY2RGB)
        elif image_array.shape[2] == 4:  # If RGBA
            rgb_image = cv2.cvtColor(image_array, cv2.COLOR_RGBA2RGB)
        elif image_array.shape[2] == 3:  # If BGR (OpenCV default)
            rgb_image = cv2.cvtColor(image_array, cv2.COLOR_BGR2RGB)
        else:
            rgb_image = image_array
        
        # If face locations are not provided, detect them
        if face_locations is None:
            face_locations, _ = detect_faces(rgb_image)
        
        if not face_locations:
            return []
        
        # Get embeddings for each face
        encodings = []
        for (top, right, bottom, left) in face_locations:
            # Extract face region
            face_img = rgb_image[top:bottom, left:right]
            
            # Get embedding using DeepFace
            DeepFace, representation, detection_module = _import_deepface()
            embedding_obj = DeepFace.represent(
                img_path=face_img,
                model_name=MODEL_NAME,
                enforce_detection=False,
                detector_backend=DETECTOR_BACKEND,
                align=ALIGN,
                normalization=NORMALIZATION
            )
            
            if isinstance(embedding_obj, list):
                # If multiple faces are detected in the cropped region (shouldn't happen)
                embedding = embedding_obj[0]['embedding']
            else:
                embedding = embedding_obj['embedding']
                
            encodings.append(np.array(embedding))
        
        return encodings
    except Exception as e:
        logger.error(f"Error getting face encodings: {str(e)}")
        raise FaceRecognitionError(f"Error getting face encodings: {str(e)}")

def compare_faces(known_encodings, face_encoding_to_check, threshold=0.6):
    """
    Compare a face encoding with a list of known encodings
    
    Args:
        known_encodings: List of known face encodings
        face_encoding_to_check: Face encoding to compare against known encodings
        threshold: Maximum distance to consider it a match (lower is more strict)
        
    Returns:
        list: List of True/False values indicating which known encodings match the face
    """
    if not known_encodings or face_encoding_to_check is None:
        return []
    
    try:
        # Convert to numpy arrays if they aren't already
        known_encodings = [np.array(enc) for enc in known_encodings]
        face_encoding_to_check = np.array(face_encoding_to_check)
        
        # Calculate distances using the specified metric (NumPy replacement)
        known_arr = np.vstack(known_encodings)
        check_arr = face_encoding_to_check.reshape(1, -1)
        if DISTANCE_METRIC == 'cosine':
            # Cosine similarity: dot product of normalized vectors
            def _normalize_rows(arr):
                norms = np.linalg.norm(arr, axis=1, keepdims=True)
                norms[norms == 0] = 1
                return arr / norms
            norm_known = _normalize_rows(known_arr)
            norm_check = _normalize_rows(check_arr)
            similarities = np.dot(norm_known, norm_check.T).flatten()
            distances = 1.0 - similarities
        elif DISTANCE_METRIC == 'euclidean':
            # Euclidean distance
            diffs = known_arr - check_arr
            distances = np.linalg.norm(diffs, axis=1)
        elif DISTANCE_METRIC == 'euclidean_l2':
            # L2-normalized Euclidean (normalize vectors then euclidean)
            def _normalize_rows(arr):
                norms = np.linalg.norm(arr, axis=1, keepdims=True)
                norms[norms == 0] = 1
                return arr / norms
            norm_known = _normalize_rows(known_arr)
            norm_check = _normalize_rows(check_arr)
            diffs = norm_known - norm_check
            distances = np.linalg.norm(diffs, axis=1)
        else:
            raise ValueError(f"Unsupported distance metric: {DISTANCE_METRIC}")
        
        # Compare distances to threshold
        return [dist <= threshold for dist in distances]
    except Exception as e:
        logger.error(f"Error comparing faces: {str(e)}")
        return []

def find_best_match(known_encodings, face_encoding_to_check, threshold=0.6):
    """
    Find the best match for a face encoding from a list of known encodings
    
    Args:
        known_encodings: List of known face encodings
        face_encoding_to_check: Face encoding to find a match for
        threshold: Maximum distance to consider it a match (lower is more strict)
        
    Returns:
        tuple: (best_match_index, confidence) or (None, None) if no match found
    """
    if not known_encodings or face_encoding_to_check is None:
        return None, None
    
    try:
        # Convert to numpy arrays if they aren't already
        known_encodings = [np.array(enc) for enc in known_encodings]
        face_encoding_to_check = np.array(face_encoding_to_check)
        
        # Calculate distances using the specified metric (NumPy replacement)
        known_arr = np.vstack(known_encodings)
        check_arr = face_encoding_to_check.reshape(1, -1)
        if DISTANCE_METRIC == 'cosine':
            # Cosine similarity: dot of normalized vectors
            def _norm_rows(arr):
                norms = np.linalg.norm(arr, axis=1, keepdims=True)
                norms[norms == 0] = 1
                return arr / norms
            norm_known = _norm_rows(known_arr)
            norm_check = _norm_rows(check_arr)
            similarities = np.dot(norm_known, norm_check.T).flatten()
            distances = 1.0 - similarities
        elif DISTANCE_METRIC == 'euclidean':
            diffs = known_arr - check_arr
            distances = np.linalg.norm(diffs, axis=1)
        elif DISTANCE_METRIC == 'euclidean_l2':
            def _norm_rows(arr):
                norms = np.linalg.norm(arr, axis=1, keepdims=True)
                norms[norms == 0] = 1
                return arr / norms
            norm_known = _norm_rows(known_arr)
            norm_check = _norm_rows(check_arr)
            diffs = norm_known - norm_check
            distances = np.linalg.norm(diffs, axis=1)
        else:
            raise ValueError(f"Unsupported distance metric: {DISTANCE_METRIC}")
        
        # Find the best match (smallest distance)
        best_match_index = np.argmin(distances)
        min_distance = distances[best_match_index]
        
        # Calculate confidence (1 - normalized distance)
        # For cosine: 1 means identical, 0 means orthogonal
        # For euclidean: 1 means identical, higher means more different
        if DISTANCE_METRIC == 'cosine':
            confidence = 1.0 - min_distance  # For cosine, distance is already 1-similarity
        else:
            # For euclidean, normalize to [0,1] range (assuming max possible distance is 4.0)
            confidence = max(0.0, 1.0 - (min_distance / 4.0))
        
        # Check if the best match is below the threshold
        if min_distance <= threshold:
            # Ensure we return Python-native types (not numpy types) for compatibility
            return int(best_match_index), float(confidence)
        
        return None, None
    except Exception as e:
        logger.error(f"Error finding best match: {str(e)}")
        return None, None

def draw_face_boxes(image_array, face_locations, labels=None, confidences=None):
    """
    Draw boxes around faces in the image
    
    Args:
        image_array: numpy array of the image in RGB format
        face_locations: List of face locations as (top, right, bottom, left) tuples
        labels: Optional list of labels for each face
        confidences: Optional list of confidence scores for each face
        
    Returns:
        numpy array: Image with face boxes drawn
    """
    if image_array is None or not face_locations:
        return image_array
    
    # Make a copy of the image to draw on
    image = image_array.copy()
    
    # Convert to PIL Image for drawing
    pil_image = Image.fromarray(image)
    draw = ImageDraw.Draw(pil_image)
    
    for i, (top, right, bottom, left) in enumerate(face_locations):
        # Draw a box around the face
        draw.rectangle([left, top, right, bottom], outline="green", width=2)
        
        # Draw a label with a name and confidence below the face
        if labels and i < len(labels):
            label = labels[i]
            if confidences and i < len(confidences):
                label = f"{label} ({confidences[i]:.2f})"
            
            # Draw a filled rectangle for the label
            text_bbox = draw.textbbox((0, 0), label)
            text_width = text_bbox[2] - text_bbox[0]
            text_height = text_bbox[3] - text_bbox[1]
            
            draw.rectangle(
                [left, bottom, left + text_width + 4, bottom + text_height + 4],
                fill="green"
            )
            draw.text(
                (left + 2, bottom + 2),
                label,
                fill="white"
            )
    
    # Convert back to numpy array
    return np.array(pil_image)

def preprocess_image(image_file):
    """
    Preprocess an uploaded image file for face recognition
    
    Args:
        image_file: InMemoryUploadedFile or similar file-like object
        
    Returns:
        numpy array: Preprocessed image in RGB format
    """
    try:
        # Read the image file
        image = Image.open(image_file)
        
        # Convert to RGB if necessary
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # Convert to numpy array
        image_array = np.array(image)
        
        # Resize if the image is too large (for performance)
        max_size = 1000
        height, width = image_array.shape[:2]
        if max(height, width) > max_size:
            scale = max_size / max(height, width)
            new_size = (int(width * scale), int(height * scale))
            image_array = cv2.resize(image_array, new_size, interpolation=cv2.INTER_AREA)
        
        return image_array
    except Exception as e:
        logger.error(f"Error preprocessing image: {str(e)}")
        raise FaceRecognitionError(f"Error processing image: {str(e)}")

def save_face_image(image_array, face_location, file_path):
    """
    Save a cropped face image to the specified path
    
    Args:
        image_array: numpy array of the image in RGB format
        face_location: Tuple of (top, right, bottom, left) face coordinates
        file_path: Path to save the face image to
        
    Returns:
        str: Path to the saved image
    """
    try:
        top, right, bottom, left = face_location
        
        # Extract the face from the image
        face_image = image_array[top:bottom, left:right]
        
        # Convert to PIL Image
        face_pil = Image.fromarray(face_image)
        
        # Create a buffer to save the image
        buffer = io.BytesIO()
        face_pil.save(buffer, format='JPEG')
        
        # Save to the specified path
        file_path = default_storage.save(file_path, ContentFile(buffer.getvalue()))
        
        return file_path
    except Exception as e:
        logger.error(f"Error saving face image: {str(e)}")
        raise FaceRecognitionError(f"Error saving face image: {str(e)}")

def verify_faces(img1_path, img2_path, threshold=0.6):
    """
    Verify if two images contain the same face using DeepFace
    
    Args:
        img1_path: Path or numpy array of the first image
        img2_path: Path or numpy array of the second image
        threshold: Maximum distance to consider it a match
        
    Returns:
        dict: Verification result with 'verified' (bool) and 'distance' (float)
    """
    try:
        DeepFace, representation, detection_module = _import_deepface()
        result = DeepFace.verify(
            img1_path=img1_path,
            img2_path=img2_path,
            model_name=MODEL_NAME,
            detector_backend=DETECTOR_BACKEND,
            distance_metric=DISTANCE_METRIC,
            enforce_detection=ENFORCE_DETECTION,
            align=ALIGN,
            normalization=NORMALIZATION
        )
        
        # Add a 'verified' field based on the threshold
        result['verified'] = result['distance'] <= threshold
        return result
    except Exception as e:
        logger.error(f"Error verifying faces: {str(e)}")
        return {
            'verified': False,
            'distance': float('inf'),
            'threshold': threshold,
            'model': MODEL_NAME,
            'detector_backend': DETECTOR_BACKEND,
            'similarity_metric': DISTANCE_METRIC,
            'error': str(e)
        }

def find_similar_faces(img_path, db_path, threshold=0.6):
    """
    Find similar faces in a database of images
    
    Args:
        img_path: Path or numpy array of the query image
        db_path: Path to the directory containing face images
        threshold: Maximum distance to consider it a match
        
    Returns:
        list: List of matching faces with their paths and similarity scores
    """
    try:
        DeepFace, representation, detection_module = _import_deepface()
        # Find similar faces using DeepFace
        dfs = DeepFace.find(
            img_path=img_path,
            db_path=db_path,
            model_name=MODEL_NAME,
            distance_metric=DISTANCE_METRIC,
            enforce_detection=ENFORCE_DETECTION,
            detector_backend=DETECTOR_BACKEND,
            align=ALIGN,
            normalization=NORMALIZATION,
            silent=True
        )
        
        # Filter results by threshold
        results = []
        if isinstance(dfs, list) and len(dfs) > 0:
            df = dfs[0]  # Get the first DataFrame (for the first face in the image)
            for _, row in df.iterrows():
                if row[DISTANCE_METRIC] <= threshold:
                    results.append({
                        'identity': row['identity'],
                        'distance': row[DISTANCE_METRIC],
                        'threshold': threshold,
                        'verified': True
                    })
        
        return results
    except Exception as e:
        logger.error(f"Error finding similar faces: {str(e)}")
        return []
