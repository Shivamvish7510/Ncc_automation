from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from accounts.decorators import admin_required, officer_required
from .models import Unit
from .forms import UnitForm

@login_required
def unit_list(request):
    units = Unit.objects.all()
    return render(request, 'units/unit_list.html', {'units': units})

@admin_required
def unit_create(request):
    if request.method == 'POST':
        form = UnitForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Unit created successfully!')
            return redirect('unit_list')
    else:
        form = UnitForm()
    return render(request, 'units/unit_form.html', {'form': form, 'action': 'Create'})

@admin_required
def unit_update(request, pk):
    unit = get_object_or_404(Unit, pk=pk)
    if request.method == 'POST':
        form = UnitForm(request.POST, instance=unit)
        if form.is_valid():
            form.save()
            messages.success(request, 'Unit updated successfully!')
            return redirect('unit_list')
    else:
        form = UnitForm(instance=unit)
    return render(request, 'units/unit_form.html', {'form': form, 'action': 'Update', 'unit': unit})

@admin_required
def unit_delete(request, pk):
    unit = get_object_or_404(Unit, pk=pk)
    if request.method == 'POST':
        unit.delete()
        messages.success(request, 'Unit deleted successfully!')
        return redirect('unit_list')
    return render(request, 'units/unit_confirm_delete.html', {'unit': unit})

