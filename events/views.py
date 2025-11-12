from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db.models import Q, Count
from accounts.decorators import officer_required
from accounts.models import Cadet
from .models import Event, EventRegistration, EventParticipation, EventResource, EventAnnouncement
from .forms import EventForm, EventResourceForm,EventAnnouncementForm, EventParticipationForm
from events.forms import EventForm


@login_required
def event_list(request):
    """List all events based on user role"""
    user = request.user
    
    # Base queryset
    if user.role == 'ADMIN':
        events = Event.objects.all()
    elif user.role == 'OFFICER' and hasattr(user, 'officer_profile'):
        events = Event.objects.filter(unit=user.officer_profile.unit)
    elif user.role == 'CADET' and hasattr(user, 'cadet_profile'):
        events = Event.objects.filter(
            unit=user.cadet_profile.unit,
            status__in=['PUBLISHED', 'REGISTRATION_OPEN', 'ONGOING', 'COMPLETED']
        )
    else:
        events = Event.objects.none()
    
    # Filters
    event_type = request.GET.get('type')
    status = request.GET.get('status')
    search = request.GET.get('search')
    
    if event_type:
        events = events.filter(event_type=event_type)
    
    if status:
        events = events.filter(status=status)
    
    if search:
        events = events.filter(
            Q(title__icontains=search) | 
            Q(description__icontains=search) |
            Q(location__icontains=search)
        )
    
    # Annotate with registration count
    events = events.select_related('unit', 'organizer__user').annotate(
        registration_count=Count('registrations')
    )
    
    context = {
        'events': events,
        'event_types': Event.EVENT_TYPE_CHOICES,
        'statuses': Event.STATUS_CHOICES,
        'selected_type': event_type,
        'selected_status': status,
        'search_query': search,
    }
    
    return render(request, 'events/event_list.html', context)


@login_required
def event_detail(request, slug):
    """Event detail view with registration option for cadets"""
    event = get_object_or_404(Event, slug=slug)
    
    is_registered = False
    registration = None
    can_manage = False
    
    # Check if user can manage this event
    if request.user.role in ['ADMIN', 'OFFICER']:
        can_manage = True
    
    # Check if cadet is registered
    if request.user.role == 'CADET' and hasattr(request.user, 'cadet_profile'):
        try:
            registration = EventRegistration.objects.get(
                event=event,
                cadet=request.user.cadet_profile
            )
            is_registered = True
        except EventRegistration.DoesNotExist:
            pass
    
    # Get event resources and announcements
    resources = event.resources.all()
    announcements = event.announcements.all()[:5]
    
    context = {
        'event': event,
        'is_registered': is_registered,
        'registration': registration,
        'can_manage': can_manage,
        'resources': resources,
        'announcements': announcements,
        'can_register': event.can_register(),
    }
    
    return render(request, 'events/event_detail.html', context)




@officer_required
def event_create(request):
    """Create new event with better error handling"""
    
    if request.method == 'POST':
        form = EventForm(request.POST, request.FILES)
        
        if form.is_valid():
            try:
                event = form.save(commit=False)
                
                # Set organizer
                if hasattr(request.user, 'officer_profile'):
                    event.organizer = request.user.officer_profile
                else:
                    messages.error(request, 'Officer profile not found. Please contact admin.')
                    return redirect('dashboard')
                
                # Set created_by
                event.created_by = request.user
                
                # Save the event
                event.save()
                
                # Save many-to-many fields
                form.save_m2m()
                
                messages.success(request, f'Event "{event.title}" created successfully!')
                return redirect('event_detail', slug=event.slug)
                
            except Exception as e:
                messages.error(request, f'Error creating event: {str(e)}')
                # Keep form data for user to correct
        else:
            # Show validation errors
            for field, errors in form.errors.items():
                for error in errors:
                    if field == '__all__':
                        messages.error(request, error)
                    else:
                        messages.error(request, f'{field}: {error}')
    else:
        form = EventForm()
        
        # Pre-fill unit for officers
        if request.user.role == 'OFFICER' and hasattr(request.user, 'officer_profile'):
            form.initial['unit'] = request.user.officer_profile.unit
            form.initial['status'] = 'DRAFT'  # Default to draft
    
    return render(request, 'events/event_form.html', {
        'form': form,
        'action': 'Create',
        'title': 'Create New Event'
    })


@officer_required
def event_update(request, slug):
    """Update event"""
    event = get_object_or_404(Event, slug=slug)
    
    # Check permission for officers
    if request.user.role == 'OFFICER':
        if hasattr(request.user, 'officer_profile'):
            if event.unit != request.user.officer_profile.unit:
                messages.error(request, 'You can only edit events in your unit.')
                return redirect('event_list')
    
    if request.method == 'POST':
        form = EventForm(request.POST, request.FILES, instance=event)
        if form.is_valid():
            event = form.save()
            messages.success(request, f'Event "{event.title}" updated successfully!')
            return redirect('event_detail', slug=event.slug)
    else:
        form = EventForm(instance=event)
    
    return render(request, 'events/event_form.html', {
        'form': form,
        'action': 'Update',
        'title': f'Update Event: {event.title}',
        'event': event
    })


@officer_required
def event_delete(request, slug):
    """Delete event"""
    event = get_object_or_404(Event, slug=slug)
    
    # Only admin can delete
    if request.user.role != 'ADMIN':
        messages.error(request, 'Only administrators can delete events.')
        return redirect('event_list')
    
    if request.method == 'POST':
        event_title = event.title
        event.delete()
        messages.success(request, f'Event "{event_title}" deleted successfully!')
        return redirect('event_list')
    
    return render(request, 'events/event_confirm_delete.html', {'event': event})


@officer_required
def event_registrations(request, slug):
    """Manage event registrations"""
    event = get_object_or_404(Event, slug=slug)
    
    # Handle approval/rejection
    if request.method == 'POST':
        registration_id = request.POST.get('registration_id')
        action = request.POST.get('action')
        
        try:
            registration = EventRegistration.objects.get(id=registration_id, event=event)
            
            if action == 'approve':
                # Check if event is full
                if event.max_participants:
                    approved_count = event.registrations.filter(status='APPROVED').count()
                    if approved_count >= event.max_participants:
                        messages.warning(request, 'Event has reached maximum participants!')
                        return redirect('event_registrations', slug=slug)
                
                registration.status = 'APPROVED'
                if hasattr(request.user, 'officer_profile'):
                    registration.approved_by = request.user.officer_profile
                registration.approval_date = timezone.now()
                registration.save()
                messages.success(request, f'Approved registration for {registration.cadet.user.get_full_name()}')
            
            elif action == 'reject':
                reason = request.POST.get('reason', '')
                registration.status = 'REJECTED'
                registration.rejection_reason = reason
                registration.save()
                messages.success(request, f'Rejected registration for {registration.cadet.user.get_full_name()}')
            
            elif action == 'waitlist':
                registration.status = 'WAITLIST'
                registration.save()
                messages.success(request, f'Moved {registration.cadet.user.get_full_name()} to waitlist')
        
        except EventRegistration.DoesNotExist:
            messages.error(request, 'Registration not found!')
        
        return redirect('event_registrations', slug=slug)
    
    # Get all registrations
    registrations = event.registrations.all().select_related('cadet__user', 'cadet__unit')
    
    # Statistics
    stats = {
        'total': registrations.count(),
        'pending': registrations.filter(status='PENDING').count(),
        'approved': registrations.filter(status='APPROVED').count(),
        'rejected': registrations.filter(status='REJECTED').count(),
        'waitlist': registrations.filter(status='WAITLIST').count(),
        'cancelled': registrations.filter(status='CANCELLED').count(),
    }
    
    return render(request, 'events/event_registrations.html', {
        'event': event,
        'registrations': registrations,
        'stats': stats
    })


@login_required
def event_register(request, slug):
    """Cadet registers for event"""
    if request.user.role != 'CADET':
        messages.error(request, 'Only cadets can register for events.')
        return redirect('event_list')
    
    event = get_object_or_404(Event, slug=slug)
    cadet = request.user.cadet_profile
    
    # Check if registration is allowed
    if not event.can_register():
        messages.error(request, 'Registration is not open for this event.')
        return redirect('event_detail', slug=slug)
    
    # Check if already registered
    if EventRegistration.objects.filter(event=event, cadet=cadet).exists():
        messages.warning(request, 'You are already registered for this event.')
        return redirect('event_detail', slug=slug)
    
    # Create registration
    registration = EventRegistration.objects.create(
        event=event,
        cadet=cadet,
        status='PENDING'
    )
    
    messages.success(request, f'Successfully registered for "{event.title}"! Awaiting approval.')
    return redirect('cadet_events')


@login_required
def event_cancel_registration(request, registration_id):
    """Cadet cancels their registration"""
    if request.user.role != 'CADET':
        messages.error(request, 'Access denied.')
        return redirect('dashboard')
    
    registration = get_object_or_404(EventRegistration, id=registration_id)
    
    # Verify ownership
    if registration.cadet.user != request.user:
        messages.error(request, 'You can only cancel your own registrations.')
        return redirect('cadet_events')
    
    # Check if can cancel
    if registration.status not in ['PENDING', 'APPROVED', 'WAITLIST']:
        messages.error(request, 'Cannot cancel this registration.')
        return redirect('cadet_events')
    
    if request.method == 'POST':
        event_title = registration.event.title
        registration.status = 'CANCELLED'
        registration.save()
        messages.success(request, f'Registration for "{event_title}" cancelled successfully!')
        return redirect('cadet_events')
    
    return render(request, 'events/cancel_registration.html', {'registration': registration})

@login_required
def cadet_events_view(request):
    """Cadet's personal event dashboard"""
    if request.user.role != 'CADET' or not hasattr(request.user, 'cadet_profile'):
        messages.error(request, 'Access denied.')
        return redirect('dashboard')
    
    cadet = request.user.cadet_profile
    
    # Get all registrations
    registrations = EventRegistration.objects.filter(
        cadet=cadet
    ).select_related('event').order_by('-registration_date')
    
    # Calculate counts
    approved_count = registrations.filter(status='APPROVED').count()
    pending_count = registrations.filter(status='PENDING').count()
    
    # Get available events
    available_events = Event.objects.filter(
        unit=cadet.unit,
        status='REGISTRATION_OPEN'
    ).exclude(
        registrations__cadet=cadet
    ).order_by('start_date')[:10]
    
    # Get upcoming approved events
    from django.utils import timezone
    upcoming_events = Event.objects.filter(
        registrations__cadet=cadet,
        registrations__status='APPROVED',
        start_date__gte=timezone.now().date()
    ).order_by('start_date')
    
    context = {
        'registrations': registrations,
        'available_events': available_events,
        'upcoming_events': upcoming_events,
        'approved_count': approved_count,  # ← Add this
        'pending_count': pending_count,    # ← Add this
    }
    
    return render(request, 'events/cadet_events.html', context)

@officer_required
def event_manage_participation(request, slug):
    """Manage event participation and attendance"""
    event = get_object_or_404(Event, slug=slug)
    
    # Get approved registrations only
    registrations = event.registrations.filter(status='APPROVED').select_related('cadet__user', 'cadet__unit')
    
    if request.method == 'POST':
        # Bulk update participation
        for reg in registrations:
            attendance_status = request.POST.get(f'attendance_{reg.id}')
            
            if attendance_status:
                # Get or create participation record
                from .models import EventParticipation
                participation, created = EventParticipation.objects.get_or_create(
                    registration=reg,
                    defaults={'attendance_status': attendance_status}
                )
                
                if not created:
                    participation.attendance_status = attendance_status
                
                # Update optional fields
                rating = request.POST.get(f'rating_{reg.id}')
                if rating:
                    try:
                        participation.performance_rating = int(rating)
                    except (ValueError, TypeError):
                        pass
                
                position = request.POST.get(f'position_{reg.id}')
                if position:
                    try:
                        participation.position = int(position)
                    except (ValueError, TypeError):
                        pass
                
                award = request.POST.get(f'award_{reg.id}')
                if award:
                    participation.award = award
                
                # Set evaluator
                if hasattr(request.user, 'officer_profile'):
                    participation.evaluated_by = request.user.officer_profile
                    from django.utils import timezone
                    participation.evaluation_date = timezone.now()
                
                participation.save()
        
        messages.success(request, 'Participation data saved successfully!')
        return redirect('event_manage_participation', slug=slug)
    
    # Get existing participations
    participations = {}
    from .models import EventParticipation
    for part in EventParticipation.objects.filter(registration__in=registrations):
        participations[part.registration_id] = part
    
    context = {
        'event': event,
        'registrations': registrations,
        'participations': participations,
    }
    
    return render(request, 'events/event_participation.html', context)

@officer_required
def event_manage_resources(request, slug):
    """Manage event resources"""
    event = get_object_or_404(Event, slug=slug)
    
    if request.method == 'POST':
        form = EventResourceForm(request.POST)
        if form.is_valid():
            resource = form.save(commit=False)
            resource.event = event
            resource.save()
            messages.success(request, 'Resource added successfully!')
            return redirect('event_manage_resources', slug=slug)
    else:
        form = EventResourceForm()
    
    resources = event.resources.all()
    
    # Calculate total costs
    estimated_total = sum([r.estimated_cost or 0 for r in resources])
    actual_total = sum([r.actual_cost or 0 for r in resources])
    
    context = {
        'event': event,
        'resources': resources,
        'form': form,
        'estimated_total': estimated_total,
        'actual_total': actual_total,
    }
    return render(request, 'events/event_resources.html', context)


@officer_required
def event_delete_resource(request, resource_id):
    """Delete a single EventResource by id.

    This view is deliberately permissive to match older URL names used in the
    project: some URLs reference `event_delete_resource` while others use the
    plural `event_delete_resources`. We provide a single implementation and an
    alias below.
    """
    resource = get_object_or_404(EventResource, id=resource_id)
    event = resource.event

    # Permission: ADMIN can delete; OFFICER can delete if same unit
    if request.user.role == 'OFFICER':
        if not hasattr(request.user, 'officer_profile') or event.unit != request.user.officer_profile.unit:
            messages.error(request, 'You do not have permission to delete this resource.')
            return redirect('event_manage_resources', slug=event.slug)
    elif request.user.role != 'ADMIN':
        messages.error(request, 'Only officers or administrators can delete resources.')
        return redirect('event_manage_resources', slug=event.slug)

    if request.method == 'POST':
        title = getattr(resource, 'name', None) or getattr(resource, 'description', '')
        resource.delete()
        messages.success(request, f'Resource "{title}" deleted successfully!')
        return redirect('event_manage_resources', slug=event.slug)

    # Render a small confirmation page before deletion
    return render(request, 'events/resource_confirm_delete.html', {'resource': resource, 'event': event})


# Keep backward-compatible alias in case URLs reference the plural name
event_delete_resources = event_delete_resource


@officer_required
def event_announcements(request, slug):
    """List and manage announcements for an event.

    Officers (for the event's unit) and admins can create and delete
    announcements. Creation uses `EventAnnouncementForm`. Deletion is handled
    via POST with a `delete_id` parameter.
    """
    event = get_object_or_404(Event, slug=slug)

    # Permission checks
    if request.user.role == 'OFFICER':
        if not hasattr(request.user, 'officer_profile') or event.unit != request.user.officer_profile.unit:
            messages.error(request, 'You do not have permission to manage announcements for this event.')
            return redirect('event_list')
    elif request.user.role != 'ADMIN':
        messages.error(request, 'Only officers or administrators can manage announcements.')
        return redirect('event_list')

    # Handle deletion request
    if request.method == 'POST' and request.POST.get('delete_id'):
        delete_id = request.POST.get('delete_id')
        try:
            ann = EventAnnouncement.objects.get(id=delete_id, event=event)
            ann.delete()
            messages.success(request, 'Announcement deleted successfully.')
        except EventAnnouncement.DoesNotExist:
            messages.error(request, 'Announcement not found.')
        return redirect('event_announcements', slug=slug)

    # Handle creation
    if request.method == 'POST' and not request.POST.get('delete_id'):
        form = EventAnnouncementForm(request.POST)
        if form.is_valid():
            ann = form.save(commit=False)
            ann.event = event
            if hasattr(request.user, 'officer_profile'):
                ann.created_by = request.user.officer_profile
            ann.save()
            messages.success(request, 'Announcement posted successfully.')
            return redirect('event_announcements', slug=slug)
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    else:
        form = EventAnnouncementForm()

    announcements = event.announcements.all()

    context = {
        'event': event,
        'announcements': announcements,
        'form': form,
    }

    return render(request, 'events/event_announcements.html', context)