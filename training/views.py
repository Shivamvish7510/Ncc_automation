from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Count, Avg
from accounts.decorators import officer_required
from accounts.models import Cadet
from .models import Training, TrainingEnrollment
from .forms import TrainingForm, TrainingAssessmentForm

@login_required
def training_list(request):
    """List all trainings based on user role"""
    user = request.user
    
    if user.role == 'ADMIN':
        trainings = Training.objects.all()
    elif user.role == 'OFFICER' and hasattr(user, 'officer_profile'):
        trainings = Training.objects.filter(unit=user.officer_profile.unit)
    elif user.role == 'CADET' and hasattr(user, 'cadet_profile'):
        trainings = Training.objects.filter(unit=user.cadet_profile.unit, is_active=True)
    else:
        trainings = Training.objects.none()
    
    # Filters
    training_type = request.GET.get('type')
    status = request.GET.get('status')
    
    if training_type:
        trainings = trainings.filter(training_type=training_type)
    if status:
        trainings = trainings.filter(status=status)
    
    trainings = trainings.select_related('unit', 'instructor__user').annotate(
        enrollment_count=Count('enrollments')
    )
    
    context = {
        'trainings': trainings,
        'training_types': Training.TRAINING_TYPE_CHOICES,
        'statuses': Training.STATUS_CHOICES,
    }
    
    return render(request, 'training/training_list.html', context)


@login_required
def training_detail(request, pk):
    """Training detail view"""
    training = get_object_or_404(Training, pk=pk)
    
    is_enrolled = False
    enrollment = None
    can_manage = False
    
    if request.user.role in ['ADMIN', 'OFFICER']:
        can_manage = True
    
    if request.user.role == 'CADET' and hasattr(request.user, 'cadet_profile'):
        try:
            enrollment = TrainingEnrollment.objects.get(
                training=training,
                cadet=request.user.cadet_profile
            )
            is_enrolled = True
        except TrainingEnrollment.DoesNotExist:
            pass
    
    context = {
        'training': training,
        'is_enrolled': is_enrolled,
        'enrollment': enrollment,
        'can_manage': can_manage,
    }
    
    return render(request, 'training/training_detail.html', context)


@officer_required
def training_create(request):
    """Create new training"""
    if request.method == 'POST':
        form = TrainingForm(request.POST, request.FILES)
        if form.is_valid():
            training = form.save()
            messages.success(request, f'Training "{training.title}" created successfully!')
            return redirect('training_detail', pk=training.pk)
    else:
        form = TrainingForm()
        if request.user.role == 'OFFICER' and hasattr(request.user, 'officer_profile'):
            form.initial['unit'] = request.user.officer_profile.unit
            form.initial['instructor'] = request.user.officer_profile
    
    return render(request, 'training/training_form.html', {
        'form': form,
        'action': 'Create'
    })


@officer_required
def training_update(request, pk):
    """Update training"""
    training = get_object_or_404(Training, pk=pk)
    
    if request.method == 'POST':
        form = TrainingForm(request.POST, request.FILES, instance=training)
        if form.is_valid():
            training = form.save()
            messages.success(request, 'Training updated successfully!')
            return redirect('training_detail', pk=training.pk)
    else:
        form = TrainingForm(instance=training)
    
    return render(request, 'training/training_form.html', {
        'form': form,
        'action': 'Update',
        'training': training
    })


@login_required
def training_enroll(request, pk):
    """Cadet enrolls in training"""
    if request.user.role != 'CADET':
        messages.error(request, 'Only cadets can enroll in trainings.')
        return redirect('training_list')
    
    training = get_object_or_404(Training, pk=pk)
    cadet = request.user.cadet_profile
    
    if TrainingEnrollment.objects.filter(training=training, cadet=cadet).exists():
        messages.warning(request, 'You are already enrolled in this training.')
        return redirect('training_detail', pk=pk)
    
    if training.status != 'SCHEDULED':
        messages.error(request, 'Cannot enroll in this training at this time.')
        return redirect('training_detail', pk=pk)
    
    if training.max_participants:
        if training.get_enrollment_count() >= training.max_participants:
            messages.error(request, 'Training is full.')
            return redirect('training_detail', pk=pk)
    
    TrainingEnrollment.objects.create(training=training, cadet=cadet)
    messages.success(request, f'Successfully enrolled in "{training.title}"!')
    return redirect('training_detail', pk=pk)


@officer_required
def training_enrollments(request, pk):
    """Manage training enrollments"""
    training = get_object_or_404(Training, pk=pk)
    enrollments = training.enrollments.all().select_related('cadet__user')
    
    context = {
        'training': training,
        'enrollments': enrollments,
        'stats': {
            'total': enrollments.count(),
            'completed': enrollments.filter(completion_status=True).count(),
            'in_progress': enrollments.filter(completion_status=False).count(),
        }
    }
    
    return render(request, 'training/training_enrollments.html', context)


@officer_required
def training_assess(request, pk):
    """Assess trainees"""
    training = get_object_or_404(Training, pk=pk)
    enrollments = training.enrollments.all().select_related('cadet__user')
    
    if request.method == 'POST':
        for enrollment in enrollments:
            attendance = request.POST.get(f'attendance_{enrollment.id}')
            theory = request.POST.get(f'theory_{enrollment.id}')
            practical = request.POST.get(f'practical_{enrollment.id}')
            overall = request.POST.get(f'overall_{enrollment.id}')
            completed = request.POST.get(f'completed_{enrollment.id}')
            
            if attendance:
                enrollment.attendance_percentage = float(attendance)
            if theory:
                enrollment.theory_score = float(theory)
            if practical:
                enrollment.practical_score = float(practical)
            if overall:
                enrollment.overall_score = float(overall)
                enrollment.grade = enrollment.calculate_grade()
            
            enrollment.completion_status = completed == 'on'
            enrollment.save()
        
        messages.success(request, 'Assessment data saved successfully!')
        return redirect('training_enrollments', pk=pk)
    
    return render(request, 'training/training_assess.html', {
        'training': training,
        'enrollments': enrollments
    })


@login_required
def cadet_trainings_view(request):
    """Cadet's training dashboard"""
    if request.user.role != 'CADET' or not hasattr(request.user, 'cadet_profile'):
        messages.error(request, 'Access denied.')
        return redirect('dashboard')
    
    cadet = request.user.cadet_profile
    
    enrollments = TrainingEnrollment.objects.filter(
        cadet=cadet
    ).select_related('training').order_by('-enrollment_date')
    
    available_trainings = Training.objects.filter(
        unit=cadet.unit,
        status='SCHEDULED',
        is_active=True
    ).exclude(
        enrollments__cadet=cadet
    ).order_by('start_date')
    
    context = {
        'enrollments': enrollments,
        'available_trainings': available_trainings,
        'completed_count': enrollments.filter(completion_status=True).count(),
    }
    
    return render(request, 'training/cadet_trainings.html', context)
