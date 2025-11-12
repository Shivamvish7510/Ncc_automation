from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Count
from .models import User, Cadet, Officer
from .forms import LoginForm, CadetRegistrationForm
from .decorators import role_required, officer_required, admin_required


def login_view(request):
    """Enhanced login view with flexible role checking"""
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        selected_role = request.POST.get('role')  # Get selected role
        
        # Authenticate user
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            # Special handling for superusers/staff
            if user.is_superuser or user.is_staff:
                # Superuser can login from any tab
                user.role = 'ADMIN'
                user.save()
                login(request, user)
                messages.success(request, f'Welcome back, {user.get_full_name()}!')
                return redirect('admin_dashboard')
            
            # Check if selected role matches user's actual role
            if selected_role and user.role != selected_role:
                messages.error(request, f'Invalid credentials for {selected_role} login. Please select the correct role tab.')
                return render(request, 'accounts/login.html')
            
            # Login successful
            login(request, user)
            messages.success(request, f'Welcome back, {user.get_full_name()}!')
            
            # Role-based redirection
            if user.role == 'ADMIN':
                return redirect('admin_dashboard')
            elif user.role == 'OFFICER':
                return redirect('officer_dashboard')
            elif user.role == 'CADET':
                return redirect('cadet_dashboard')
            else:
                return redirect('dashboard')
        else:
            messages.error(request, 'Invalid username or password.')
    
    return render(request, 'accounts/login.html')

def logout_view(request):
    """Logout view"""
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('login')


@login_required
def dashboard_view(request):
    """Main dashboard - redirects based on role"""
    user = request.user
    
    if user.role == 'ADMIN':
        return redirect('admin_dashboard')
    elif user.role == 'OFFICER':
        return redirect('officer_dashboard')
    elif user.role == 'CADET':
        return redirect('cadet_dashboard')
    
    return render(request, 'dashboard/base_dashboard.html')


@admin_required
def admin_dashboard_view(request):
    """Admin dashboard"""
    from units.models import Unit
    from events.models import Event
    from attendance.models import AttendanceSession
    
    context = {
        'total_cadets': Cadet.objects.count(),
        'total_officers': Officer.objects.count(),
        'total_units': Unit.objects.count(),
        'total_events': Event.objects.count(),
        'active_sessions': AttendanceSession.objects.filter(is_active=True).count(),
        'recent_cadets': Cadet.objects.select_related('user', 'unit').order_by('-id')[:5],
    }
    return render(request, 'dashboard/admin_dashboard.html', context)


@officer_required
def officer_dashboard_view(request):
    """Officer dashboard"""
    officer = request.user.officer_profile
    
    from events.models import Event
    from attendance.models import AttendanceSession
    
    context = {
        'officer': officer,
        'unit': officer.unit,
        'unit_cadets_count': Cadet.objects.filter(unit=officer.unit).count() if officer.unit else 0,
        'my_events': Event.objects.filter(organizer=officer).count(),
        'pending_registrations': 0,  # Add logic for pending registrations
        'recent_sessions': AttendanceSession.objects.filter(unit=officer.unit).order_by('-date')[:5] if officer.unit else [],
    }
    return render(request, 'dashboard/officer_dashboard.html', context)


@login_required
def cadet_dashboard_view(request):
    """Cadet dashboard"""
    if request.user.role != 'CADET':
        messages.error(request, 'Access denied.')
        return redirect('dashboard')
    
    cadet = request.user.cadet_profile
    
    from attendance.models import Attendance
    from events.models import EventRegistration
    from certificates.models import Certificate
    
    # Calculate attendance statistics
    total_attendance = Attendance.objects.filter(cadet=cadet).count()
    present_count = Attendance.objects.filter(cadet=cadet, status='PRESENT').count()
    attendance_percentage = (present_count / total_attendance * 100) if total_attendance > 0 else 0
    
    context = {
        'cadet': cadet,
        'attendance_percentage': round(attendance_percentage, 2),
        'total_sessions': total_attendance,
        'present_count': present_count,
        'registered_events': EventRegistration.objects.filter(cadet=cadet).count(),
        'certificates_count': Certificate.objects.filter(cadet=cadet).count(),
    }
    return render(request, 'dashboard/cadet_dashboard.html', context)


@officer_required
def cadet_list_view(request):
    """Officer/Admin can view list of cadets"""
    user = request.user
    
    if user.role == 'ADMIN':
        cadets = Cadet.objects.all().select_related('user', 'unit')
    elif user.role == 'OFFICER' and hasattr(user, 'officer_profile'):
        cadets = Cadet.objects.filter(unit=user.officer_profile.unit).select_related('user', 'unit')
    else:
        cadets = Cadet.objects.none()
    
    # Search functionality
    search_query = request.GET.get('search', '')
    if search_query:
        cadets = cadets.filter(
            user__first_name__icontains=search_query
        ) | cadets.filter(
            user__last_name__icontains=search_query
        ) | cadets.filter(
            enrollment_number__icontains=search_query
        )
    
    return render(request, 'accounts/cadet_list.html', {
        'cadets': cadets,
        'search_query': search_query
    })


@officer_required
def cadet_create_view(request):
    """Officer/Admin can create new cadet"""
    if request.method == 'POST':
        form = CadetRegistrationForm(request.POST)
        if form.is_valid():
            cadet = form.save()
            messages.success(request, f'Cadet {cadet.user.get_full_name()} created successfully!')
            return redirect('cadet_list')
    else:
        form = CadetRegistrationForm()
        
        # Pre-fill unit for officers
        if request.user.role == 'OFFICER' and hasattr(request.user, 'officer_profile'):
            form.initial['unit'] = request.user.officer_profile.unit
    
    return render(request, 'accounts/cadet_form.html', {'form': form, 'action': 'Create'})


@login_required
def cadet_detail_view(request, pk):
    """View cadet details - READ ONLY for cadets"""
    cadet = get_object_or_404(Cadet, pk=pk)
    user = request.user
    
    # Permission check
    if user.role == 'CADET':
        # Cadets can only view their own profile
        if not hasattr(user, 'cadet_profile') or user.cadet_profile.id != cadet.id:
            messages.error(request, 'You can only view your own profile.')
            return redirect('cadet_dashboard')
    elif user.role == 'OFFICER':
        # Officers can view cadets in their unit
        if hasattr(user, 'officer_profile') and cadet.unit != user.officer_profile.unit:
            messages.error(request, 'You can only view cadets in your unit.')
            return redirect('cadet_list')
    
    # Cadets get read-only view
    is_readonly = user.role == 'CADET'
    
    # Get attendance statistics
    from attendance.models import Attendance
    total_attendance = Attendance.objects.filter(cadet=cadet).count()
    present_count = Attendance.objects.filter(cadet=cadet, status='PRESENT').count()
    attendance_percentage = (present_count / total_attendance * 100) if total_attendance > 0 else 0
    
    return render(request, 'accounts/cadet_detail.html', {
        'cadet': cadet,
        'is_readonly': is_readonly,
        'attendance_percentage': round(attendance_percentage, 2),
        'total_sessions': total_attendance,
    })


@officer_required
def cadet_update_view(request, pk):
    """Officer/Admin can update cadet details"""
    cadet = get_object_or_404(Cadet, pk=pk)
    
    # Officers can only edit cadets in their unit
    if request.user.role == 'OFFICER':
        if hasattr(request.user, 'officer_profile') and cadet.unit != request.user.officer_profile.unit:
            messages.error(request, 'You can only edit cadets in your unit.')
            return redirect('cadet_list')
    
    if request.method == 'POST':
        # Update cadet information
        cadet.rank = request.POST.get('rank', cadet.rank)
        cadet.college_name = request.POST.get('college_name', cadet.college_name)
        cadet.course = request.POST.get('course', cadet.course)
        cadet.year_of_study = request.POST.get('year_of_study', cadet.year_of_study)
        cadet.roll_number = request.POST.get('roll_number', cadet.roll_number)
        cadet.parent_name = request.POST.get('parent_name', cadet.parent_name)
        cadet.parent_phone = request.POST.get('parent_phone', cadet.parent_phone)
        cadet.parent_email = request.POST.get('parent_email', cadet.parent_email)
        cadet.emergency_contact = request.POST.get('emergency_contact', cadet.emergency_contact)
        cadet.blood_group = request.POST.get('blood_group', cadet.blood_group)
        
        cadet.save()
        messages.success(request, 'Cadet updated successfully!')
        return redirect('cadet_detail', pk=cadet.pk)
    
    return render(request, 'accounts/cadet_update.html', {'cadet': cadet})


@admin_required
def cadet_delete_view(request, pk):
    """Only Admin can delete cadets"""
    cadet = get_object_or_404(Cadet, pk=pk)
    
    if request.method == 'POST':
        user = cadet.user
        cadet_name = user.get_full_name()
        cadet.delete()
        user.delete()
        messages.success(request, f'Cadet {cadet_name} deleted successfully!')
        return redirect('cadet_list')
    
    return render(request, 'accounts/cadet_confirm_delete.html', {'cadet': cadet})
