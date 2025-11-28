import json
import logging
import base64
import pickle
import numpy as np
import cv2
import cv2
import pickle
from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from django.db import OperationalError
from django.http import JsonResponse, HttpResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required, permission_required
from django.utils import timezone
from django.core.files.base import ContentFile
from django.db import transaction

from accounts.models import Cadet
from attendance.models import AttendanceSession, Attendance
from .face_recognition.face_utils import (
    detect_faces, get_face_encodings, find_best_match,
    draw_face_boxes, preprocess_image, FaceRecognitionError
)
from .face_recognition.face_utils import is_deepface_available
from .face_recognition.models import FaceEncoding, FaceAttendanceLog

logger = logging.getLogger(__name__)

# Constants
FACE_MATCH_THRESHOLD = 0.6  # Adjust this value to make matching more/less strict

@login_required
def face_registration_view(request, cadet_id=None):
    """View for registering a cadet's face"""
    # If a cadet_id is provided, an officer or staff can register a face for that cadet
    if cadet_id:
        if not (request.user.is_staff or hasattr(request.user, 'officer_profile')):
            return HttpResponse("You are not authorized to register faces for other cadets.", status=403)
        cadet = get_object_or_404(Cadet, id=cadet_id)
    else:
        if not hasattr(request.user, 'cadet_profile'):
            return HttpResponse("This feature is only available to cadets.", status=403)
        cadet = request.user.cadet_profile
    
    if request.method == 'POST':
        try:
            # Get the image data from the request
            image_data = request.FILES.get('image')
            if not image_data:
                return JsonResponse({'success': False, 'error': 'No image provided'}, status=400)
            
            # Preprocess the image
            image_array = preprocess_image(image_data)
            
            # Detect faces in the image
            face_locations, rgb_image = detect_faces(image_array)
            
            # Check if exactly one face is detected
            if not face_locations:
                return JsonResponse({
                    'success': False,
                    'error': 'No face detected. Please ensure your face is clearly visible.'
                }, status=400)
                
            if len(face_locations) > 1:
                return JsonResponse({
                    'success': False,
                    'error': 'Multiple faces detected. Please ensure only your face is visible.'
                }, status=400)
            
            # Get face encodings
            face_encodings = get_face_encodings(rgb_image, face_locations)
            
            if not face_encodings:
                return JsonResponse({
                    'success': False,
                    'error': 'Could not extract face features. Please try again.'
                }, status=400)
            
            # Save the face encoding to the database
            with transaction.atomic():
                # Delete any existing face encodings for this cadet
                FaceEncoding.objects.filter(cadet=cadet).delete()
                
                # Create a new face encoding
                face_encoding = FaceEncoding(cadet=cadet)
                face_encoding.set_encoding(face_encodings[0])
                
                # Save a thumbnail of the face
                top, right, bottom, left = face_locations[0]
                face_image = rgb_image[top:bottom, left:right]
                face_encoding.save_face_thumbnail(face_image)
                
                # Save the face encoding
                face_encoding.save()
            
            return JsonResponse({
                'success': True,
                'message': 'Face registered successfully!',
                'thumbnail_url': face_encoding.face_thumbnail.url if face_encoding.face_thumbnail else ''
            })
            
        except FaceRecognitionError as e:
            logger.error(f"Face registration error: {str(e)}")
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=400)
            
        except Exception as e:
            logger.error(f"Unexpected error during face registration: {str(e)}", exc_info=True)
            return JsonResponse({
                'success': False,
                'error': 'An unexpected error occurred. Please try again.'
            }, status=500)
    
    # GET request - show the registration page
    context = {
        'cadet': cadet,
        'has_face_registered': hasattr(cadet, 'face_encoding')
    }
    # Indicate if the DeepFace stack is available on this server
    context['deepface_available'] = is_deepface_available()
    return render(request, 'attendance/face_register.html', context)

@login_required
def face_attendance_view(request, session_id=None):
    """View for marking attendance using face recognition"""
    # If session_id is provided, use it; otherwise, get the latest active session
    if session_id:
        session = get_object_or_404(AttendanceSession, id=session_id, is_active=True)
    else:
        session = AttendanceSession.objects.filter(
            date=timezone.now().date(),
            is_active=True
        ).order_by('-start_time').first()
        
        if not session:
            return render(request, 'attendance/no_active_session.html')
    
    # Check if the user is authorized to mark attendance for this session
    if not (request.user.is_staff or 
            request.user == session.created_by.user or
            hasattr(request.user, 'officer_profile') and 
            request.user.officer_profile.unit == session.unit):
        return HttpResponse("You are not authorized to mark attendance for this session.", status=403)
    
    context = {
        'session': session,
        'now': timezone.now(),
    }
    context['deepface_available'] = is_deepface_available()
    return render(request, 'attendance/face_attendance.html', context)

@csrf_exempt
@require_http_methods(["POST"])
@login_required
def process_face_attendance(request, session_id):
    """API endpoint to process face attendance"""
    try:
        # Get the session
        session = get_object_or_404(AttendanceSession, id=session_id, is_active=True)
        # Permission check - only staff, session owner, or unit officer can mark via face recognition
        if not (request.user.is_staff or request.user == session.created_by.user or (hasattr(request.user, 'officer_profile') and request.user.officer_profile.unit == session.unit)):
            return JsonResponse({'success': False, 'error': 'unauthorized', 'message': 'You are not authorized to mark attendance for this session.'}, status=403)
        
        # Get the image data from the request
        data = json.loads(request.body)
        image_data = data.get('image')
        
        if not image_data:
            return JsonResponse({
                'success': False,
                'error': 'No image data provided'
            }, status=400)
        
        # Decode the base64 image
        # Handle both full data URL (data:image/jpeg;base64,...) and raw base64 strings
        if isinstance(image_data, str) and ';base64,' in image_data:
            _, imgstr = image_data.split(';base64,')
            image_bytes = base64.b64decode(imgstr)
        else:
            # Already a raw base64 string
            image_bytes = base64.b64decode(image_data)
        
        # Convert to numpy array
        nparr = np.frombuffer(image_bytes, np.uint8)
        image_array = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if image_array is None:
            return JsonResponse({
                'success': False,
                'error': 'Invalid image data'
            }, status=400)
        
        # Convert BGR to RGB
        rgb_image = cv2.cvtColor(image_array, cv2.COLOR_BGR2RGB)
        
        # Detect faces
        face_locations, _ = detect_faces(rgb_image)
        
        if not face_locations:
            return JsonResponse({
                'success': False,
                'error': 'no_face',
                'message': 'No face detected. Please ensure your face is clearly visible.'
            })
        
        if len(face_locations) > 1:
            return JsonResponse({
                'success': False,
                'error': 'multiple_faces',
                'message': 'Multiple faces detected. Please ensure only one person is in the frame.'
            })
        
        # Get face encodings
        face_encodings = get_face_encodings(rgb_image, face_locations)
        
        if not face_encodings:
            return JsonResponse({
                'success': False,
                'error': 'no_encoding',
                'message': 'Could not process face features. Please try again.'
            })
        
        # Get all face encodings for cadets in this unit
        cadet_encodings = FaceEncoding.objects.filter(
            cadet__unit=session.unit,
            is_active=True
        ).select_related('cadet')
        
        if not cadet_encodings.exists():
            return JsonResponse({
                'success': False,
                'error': 'no_registered_faces',
                'message': 'No registered faces found for this unit.'
            })

        # Simulation mode - useful for local testing without deepface installed
        if settings.DEBUG and getattr(settings, 'FACE_RECOG_SIMULATE', False):
            # Choose the first cadet as a simulated match
            simulated_cadet = cadet_encodings.first().cadet
            if simulated_cadet:
                attendance, created = Attendance.objects.get_or_create(
                    session=session,
                    cadet=simulated_cadet,
                    defaults={
                        'status': 'PRESENT',
                        'marked_by': request.user.officer_profile if hasattr(request.user, 'officer_profile') else None,
                        'check_in_time': timezone.now(),
                        'remarks': 'Simulated via face recognition (DEBUG)'
                    }
                )
                if not created:
                    attendance.status = 'PRESENT'
                    attendance.check_in_time = timezone.now()
                    attendance.remarks = 'Simulated via face recognition (DEBUG)'
                    attendance.save()

                FaceAttendanceLog.objects.create(
                    session=session,
                    cadet=simulated_cadet,
                    status='SUCCESS',
                    confidence=0.99,
                    ip_address=request.META.get('REMOTE_ADDR','')
                )

                return JsonResponse({
                    'success': True,
                    'cadet_id': simulated_cadet.id,
                    'cadet_name': simulated_cadet.user.get_full_name(),
                    'enrollment_number': simulated_cadet.enrollment_number,
                    'confidence': 0.99,
                    'message': f'Attendance marked for {simulated_cadet.user.get_full_name()} (simulated)'
                })
        
        # Convert encodings to numpy arrays
        known_face_encodings = [
            pickle.loads(encoding.encoding) 
            for encoding in cadet_encodings
        ]
        
        # Find the best match
        best_match_index, confidence = find_best_match(
            known_face_encodings,
            face_encodings[0],
            threshold=FACE_MATCH_THRESHOLD
        )
        
        # Log the attendance attempt
        ip_address = request.META.get('REMOTE_ADDR', '')
        
        if best_match_index is not None:
            # Ensure integer indexing for Django QuerySets (convert numpy types)
            idx = int(best_match_index)
            matched_cadet = cadet_encodings[idx].cadet
            
            # Check if attendance is already marked for this cadet and session
            attendance, created = Attendance.objects.get_or_create(
                session=session,
                cadet=matched_cadet,
                defaults={
                    'status': 'PRESENT',
                    'marked_by': request.user.officer_profile if hasattr(request.user, 'officer_profile') else None,
                    'check_in_time': timezone.now(),
                    'remarks': 'Marked via face recognition'
                }
            )
            
            if not created:
                attendance.status = 'PRESENT'
                attendance.check_in_time = timezone.now()
                attendance.remarks = 'Updated via face recognition'
                attendance.save()
            
            # Log successful recognition
            FaceAttendanceLog.objects.create(
                session=session,
                cadet=matched_cadet,
                status='SUCCESS',
                confidence=confidence,
                ip_address=ip_address
            )
            
            # Prepare thumbnail url if available
            thumbnail_url = ''
            try:
                thumbnail_url = matched_cadet.face_encoding.face_thumbnail.url if matched_cadet.face_encoding.face_thumbnail else ''
            except Exception:
                thumbnail_url = ''

            return JsonResponse({
                'success': True,
                'cadet_id': matched_cadet.id,
                'cadet_name': matched_cadet.user.get_full_name(),
                'enrollment_number': matched_cadet.enrollment_number,
                'thumbnail_url': thumbnail_url,
                'confidence': confidence,
                'message': f'Attendance marked for {matched_cadet.user.get_full_name()}' 
            })
        
        else:
            # Log failed recognition
            FaceAttendanceLog.objects.create(
                session=session,
                status='UNKNOWN',
                ip_address=ip_address
            )
            
            return JsonResponse({
                'success': False,
                'error': 'no_match',
                'message': 'Face not recognized. Please register your face or contact an administrator.'
            })
    
    except FaceRecognitionError as e:
        logger.error(f"Face recognition error: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': 'deepface_unavailable',
            'message': str(e)
        }, status=503)
    except Exception as e:
        logger.error(f"Error processing face attendance: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': 'server_error',
            'message': 'An error occurred while processing your request.'
        }, status=500)

@login_required
def face_management_view(request):
    """View for managing registered faces"""
    if not (request.user.is_staff or hasattr(request.user, 'officer_profile')):
        return HttpResponse("You are not authorized to access this page.", status=403)
    
    # Get the unit for filtering (if user is an officer)
    unit = None
    if hasattr(request.user, 'officer_profile'):
        unit = request.user.officer_profile.unit
    
    # Get all cadets with face encodings (catch DB errors like missing migrations)
    try:
        cadets_with_faces = Cadet.objects.filter(
            face_encoding__isnull=False
        )
    except OperationalError as e:
        # DB likely needs migrations; show a user-friendly message
        context = {
            'cadets_with_faces': [],
            'cadets_without_faces': [],
            'unit': None,
            'db_error': True,
            'db_error_message': str(e)
        }
        return render(request, 'attendance/face_management.html', context)
    
    # Filter by unit if user is an officer
    if unit:
        cadets_with_faces = cadets_with_faces.filter(unit=unit)
    
    # Get cadets without face encodings
    cadets_without_faces = Cadet.objects.filter(
        face_encoding__isnull=True
    )
    
    # Filter by unit if user is an officer
    if unit:
        cadets_without_faces = cadets_without_faces.filter(unit=unit)
    
    context = {
        'cadets_with_faces': cadets_with_faces,
        'cadets_without_faces': cadets_without_faces,
        'unit': unit
    }
    
    return render(request, 'attendance/face_management.html', context)

@login_required
def delete_face_encoding(request, cadet_id):
    """Delete a face encoding"""
    cadet = get_object_or_404(Cadet, id=cadet_id)
    
    # Check permissions
    if not (request.user.is_staff or 
            (hasattr(request.user, 'officer_profile') and 
             request.user.officer_profile.unit == cadet.unit)):
        return JsonResponse({
            'success': False,
            'error': 'You are not authorized to perform this action.'
        }, status=403)
    
    # Delete the face encoding
    FaceEncoding.objects.filter(cadet=cadet).delete()
    
    return JsonResponse({
        'success': True,
        'message': 'Face encoding deleted successfully.'
    })

@login_required
def attendance_logs_view(request, session_id=None):
    """View for viewing attendance logs"""
    # If session_id is provided, get logs for that session
    if session_id:
        session = get_object_or_404(AttendanceSession, id=session_id)
        logs = FaceAttendanceLog.objects.filter(session=session).order_by('-created_at')
    else:
        # Otherwise, get logs for the most recent session
        latest_session = AttendanceSession.objects.filter(
            is_active=True
        ).order_by('-date', '-start_time').first()
        
        if latest_session:
            logs = FaceAttendanceLog.objects.filter(
                session=latest_session
            ).order_by('-created_at')
        else:
            logs = FaceAttendanceLog.objects.none()
    
    context = {
        'logs': logs,
        'session': session if session_id else latest_session
    }
    
    return render(request, 'attendance/attendance_logs.html', context)
