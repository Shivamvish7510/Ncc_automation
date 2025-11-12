from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from accounts.decorators import officer_required
from .models import Achievement
from .forms import AchievementForm

@login_required
def achievement_list(request):
    """List all achievements based on user role"""
    user = request.user
    
    if user.role in ['ADMIN', 'OFFICER']:
        if hasattr(user, 'officer_profile') and user.role == 'OFFICER':
            achievements = Achievement.objects.filter(
                cadet__unit=user.officer_profile.unit
            ).select_related('cadet__user', 'event', 'training')
        else:
            achievements = Achievement.objects.all().select_related('cadet__user', 'event', 'training')
    elif user.role == 'CADET' and hasattr(user, 'cadet_profile'):
        achievements = Achievement.objects.filter(cadet=user.cadet_profile)
    else:
        achievements = Achievement.objects.none()
    
    # Filters
    achievement_type = request.GET.get('type')
    level = request.GET.get('level')
    verified = request.GET.get('verified')
    
    if achievement_type:
        achievements = achievements.filter(achievement_type=achievement_type)
    if level:
        achievements = achievements.filter(level=level)
    if verified:
        achievements = achievements.filter(verified=(verified == 'true'))
    
    context = {
        'achievements': achievements,
        'achievement_types': Achievement.ACHIEVEMENT_TYPE_CHOICES,
        'levels': Achievement.LEVEL_CHOICES,
    }
    
    return render(request, 'achievements/achievement_list.html', context)


@login_required
def achievement_detail(request, pk):
    """Achievement detail view"""
    achievement = get_object_or_404(Achievement, pk=pk)
    
    # Permission check
    if request.user.role == 'CADET':
        if not hasattr(request.user, 'cadet_profile') or achievement.cadet != request.user.cadet_profile:
            messages.error(request, 'You can only view your own achievements.')
            return redirect('achievement_list')
    
    return render(request, 'achievements/achievement_detail.html', {'achievement': achievement})


@officer_required
def achievement_create(request):
    """Create new achievement"""
    if request.method == 'POST':
        form = AchievementForm(request.POST, request.FILES)
        if form.is_valid():
            achievement = form.save(commit=False)
            if achievement.verified and hasattr(request.user, 'officer_profile'):
                achievement.verified_by = request.user.officer_profile
                achievement.verification_date = timezone.now().date()
            achievement.save()
            
            # Create notification for cadet
            from notifications.models import Notification
            Notification.objects.create(
                title='New Achievement Awarded',
                message=f'You have been awarded: {achievement.title}',
                notification_type='ACHIEVEMENT',
                recipient=achievement.cadet.user,
                sender=request.user
            )
            
            messages.success(request, 'Achievement created successfully!')
            return redirect('achievement_detail', pk=achievement.pk)
    else:
        form = AchievementForm()
    
    return render(request, 'achievements/achievement_form.html', {
        'form': form,
        'action': 'Create'
    })


@officer_required
def achievement_update(request, pk):
    """Update achievement"""
    achievement = get_object_or_404(Achievement, pk=pk)
    
    if request.method == 'POST':
        form = AchievementForm(request.POST, request.FILES, instance=achievement)
        if form.is_valid():
            achievement = form.save(commit=False)
            if achievement.verified and not achievement.verified_by:
                if hasattr(request.user, 'officer_profile'):
                    achievement.verified_by = request.user.officer_profile
                    achievement.verification_date = timezone.now().date()
            achievement.save()
            messages.success(request, 'Achievement updated successfully!')
            return redirect('achievement_detail', pk=achievement.pk)
    else:
        form = AchievementForm(instance=achievement)
    
    return render(request, 'achievements/achievement_form.html', {
        'form': form,
        'action': 'Update',
        'achievement': achievement
    })


@officer_required
def achievement_verify(request, pk):
    """Verify achievement"""
    achievement = get_object_or_404(Achievement, pk=pk)
    
    if not achievement.verified:
        achievement.verified = True
        if hasattr(request.user, 'officer_profile'):
            achievement.verified_by = request.user.officer_profile
        achievement.verification_date = timezone.now().date()
        achievement.save()
        
        # Notify cadet
        from notifications.models import Notification
        Notification.objects.create(
            title='Achievement Verified',
            message=f'Your achievement "{achievement.title}" has been verified.',
            notification_type='ACHIEVEMENT',
            recipient=achievement.cadet.user,
            sender=request.user
        )
        
        messages.success(request, 'Achievement verified successfully!')
    
    return redirect('achievement_detail', pk=pk)


@login_required
def cadet_achievements_view(request):
    """Cadet's achievement dashboard"""
    if request.user.role != 'CADET' or not hasattr(request.user, 'cadet_profile'):
        messages.error(request, 'Access denied.')
        return redirect('dashboard')
    
    cadet = request.user.cadet_profile
    achievements = Achievement.objects.filter(cadet=cadet).order_by('-date_awarded')
    
    context = {
        'achievements': achievements,
        'total_achievements': achievements.count(),
        'medals': achievements.filter(achievement_type='MEDAL').count(),
        'trophies': achievements.filter(achievement_type='TROPHY').count(),
        'awards': achievements.filter(achievement_type='AWARD').count(),
        'national_level': achievements.filter(level='NATIONAL').count(),
        'verified_count': achievements.filter(verified=True).count(),
    }
    
    return render(request, 'achievements/cadet_achievements.html', context)

