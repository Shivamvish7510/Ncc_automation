from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Count, Q
from accounts.decorators import officer_required
from accounts.models import Cadet
from .models import AttendanceSession, Attendance
from .forms import AttendanceSessionForm

@officer_required
def attendance_session_list(request):
    user = request.user
    if user.role == 'ADMIN':
        sessions = AttendanceSession.objects.all()
    elif hasattr(user, 'officer_profile'):
        sessions = AttendanceSession.objects.filter(unit=user.officer_profile.unit)
    else:
        sessions = AttendanceSession.objects.none()
    
    return render(request, 'attendance/session_list.html', {'sessions': sessions})

@officer_required
def attendance_session_create(request):
    if request.method == 'POST':
        form = AttendanceSessionForm(request.POST)
        if form.is_valid():
            session = form.save(commit=False)
            if hasattr(request.user, 'officer_profile'):
                session.created_by = request.user.officer_profile
            session.save()
            messages.success(request, 'Attendance session created successfully!')
            return redirect('attendance_session_list')
    else:
        form = AttendanceSessionForm()
        # Pre-fill unit for officers
        if hasattr(request.user, 'officer_profile') and request.user.role == 'OFFICER':
            form.initial['unit'] = request.user.officer_profile.unit
    
    return render(request, 'attendance/session_form.html', {'form': form, 'action': 'Create'})

@officer_required
def mark_attendance(request, session_id):
    session = get_object_or_404(AttendanceSession, id=session_id)
    
    if request.method == 'POST':
        # Bulk mark attendance
        for key, value in request.POST.items():
            if key.startswith('status_'):
                cadet_id = key.split('_')[1]
                status = value
                remarks = request.POST.get(f'remarks_{cadet_id}', '')
                
                try:
                    cadet = Cadet.objects.get(id=cadet_id)
                    officer = request.user.officer_profile if hasattr(request.user, 'officer_profile') else None
                    
                    Attendance.objects.update_or_create(
                        session=session,
                        cadet=cadet,
                        defaults={
                            'status': status,
                            'remarks': remarks,
                            'marked_by': officer
                        }
                    )
                except Cadet.DoesNotExist:
                    continue
        
        messages.success(request, 'Attendance marked successfully!')
        return redirect('attendance_session_list')
    
    # Get cadets for this unit
    cadets = Cadet.objects.filter(unit=session.unit).select_related('user')
    
    # Get existing attendance records
    attendance_dict = {}
    for att in Attendance.objects.filter(session=session):
        attendance_dict[att.cadet_id] = att
    
    # Prepare cadet data with attendance
    cadet_attendance = []
    for cadet in cadets:
        cadet_attendance.append({
            'cadet': cadet,
            'attendance': attendance_dict.get(cadet.id)
        })
    
    return render(request, 'attendance/mark_attendance.html', {
        'session': session,
        'cadet_attendance': cadet_attendance,
        'status_choices': Attendance.STATUS_CHOICES
    })

@officer_required
def attendance_session_detail(request, pk):
    session = get_object_or_404(AttendanceSession, pk=pk)
    attendances = Attendance.objects.filter(session=session).select_related('cadet__user')
    stats = session.get_attendance_stats()
    
    return render(request, 'attendance/session_detail.html', {
        'session': session,
        'attendances': attendances,
        'stats': stats
    })

@login_required
def cadet_attendance_view(request):
    if request.user.role != 'CADET' or not hasattr(request.user, 'cadet_profile'):
        messages.error(request, 'Access denied.')
        return redirect('dashboard')
    
    cadet = request.user.cadet_profile
    attendance_records = Attendance.objects.filter(cadet=cadet).select_related('session').order_by('-session__date')
    
    # Calculate statistics
    total = attendance_records.count()
    present = attendance_records.filter(status='PRESENT').count()
    absent = attendance_records.filter(status='ABSENT').count()
    late = attendance_records.filter(status='LATE').count()
    excused = attendance_records.filter(status='EXCUSED').count()
    percentage = (present / total * 100) if total > 0 else 0
    
    return render(request, 'attendance/cadet_attendance.html', {
        'attendance_records': attendance_records,
        'statistics': {
            'total': total,
            'present': present,
            'absent': absent,
            'late': late,
            'excused': excused,
            'percentage': round(percentage, 2)
        }
    })
