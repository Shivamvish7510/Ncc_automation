from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from accounts.decorators import officer_required
from .models import Certificate
from .forms import CertificateForm

@login_required
def certificate_list(request):
    """List all certificates based on user role"""
    user = request.user
    
    if user.role in ['ADMIN', 'OFFICER']:
        if hasattr(user, 'officer_profile') and user.role == 'OFFICER':
            certificates = Certificate.objects.filter(
                cadet__unit=user.officer_profile.unit
            ).select_related('cadet__user', 'issued_by__user')
        else:
            certificates = Certificate.objects.all().select_related('cadet__user', 'issued_by__user')
    elif user.role == 'CADET' and hasattr(user, 'cadet_profile'):
        certificates = Certificate.objects.filter(cadet=user.cadet_profile)
    else:
        certificates = Certificate.objects.none()
    
    # Filters
    cert_type = request.GET.get('type')
    status = request.GET.get('status')
    
    if cert_type:
        certificates = certificates.filter(certificate_type=cert_type)
    if status:
        certificates = certificates.filter(status=status)
    
    context = {
        'certificates': certificates,
        'certificate_types': Certificate.CERTIFICATE_TYPE_CHOICES,
        'statuses': Certificate.STATUS_CHOICES,
    }
    
    return render(request, 'certificates/certificate_list.html', context)


@login_required
def certificate_detail(request, pk):
    """Certificate detail view"""
    certificate = get_object_or_404(Certificate, pk=pk)
    
    # Permission check
    if request.user.role == 'CADET':
        if not hasattr(request.user, 'cadet_profile') or certificate.cadet != request.user.cadet_profile:
            messages.error(request, 'You can only view your own certificates.')
            return redirect('certificate_list')
    
    return render(request, 'certificates/certificate_detail.html', {'certificate': certificate})


@officer_required
def certificate_create(request):
    """Create new certificate"""
    if request.method == 'POST':
        form = CertificateForm(request.POST, request.FILES)
        if form.is_valid():
            certificate = form.save(commit=False)
            if hasattr(request.user, 'officer_profile'):
                certificate.issued_by = request.user.officer_profile
            certificate.save()
            messages.success(request, f'Certificate {certificate.certificate_number} created successfully!')
            return redirect('certificate_detail', pk=certificate.pk)
    else:
        form = CertificateForm()
    
    return render(request, 'certificates/certificate_form.html', {
        'form': form,
        'action': 'Create'
    })


@officer_required
def certificate_update(request, pk):
    """Update certificate"""
    certificate = get_object_or_404(Certificate, pk=pk)
    
    if request.method == 'POST':
        form = CertificateForm(request.POST, request.FILES, instance=certificate)
        if form.is_valid():
            certificate = form.save()
            messages.success(request, 'Certificate updated successfully!')
            return redirect('certificate_detail', pk=certificate.pk)
    else:
        form = CertificateForm(instance=certificate)
    
    return render(request, 'certificates/certificate_form.html', {
        'form': form,
        'action': 'Update',
        'certificate': certificate
    })


@login_required
def cadet_certificates_view(request):
    """Cadet's certificate dashboard"""
    if request.user.role != 'CADET' or not hasattr(request.user, 'cadet_profile'):
        messages.error(request, 'Access denied.')
        return redirect('dashboard')
    
    cadet = request.user.cadet_profile
    certificates = Certificate.objects.filter(cadet=cadet, status='ISSUED').order_by('-issued_date')
    
    context = {
        'certificates': certificates,
        'total_certificates': certificates.count(),
        'a_certificates': certificates.filter(certificate_type='A').count(),
        'b_certificates': certificates.filter(certificate_type='B').count(),
        'c_certificates': certificates.filter(certificate_type='C').count(),
    }
    
    return render(request, 'certificates/cadet_certificates.html', context)
