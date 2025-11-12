from django import forms
from .models import Event, EventRegistration, EventResource, EventAnnouncement, EventParticipation

from django.core.exceptions import ValidationError

class EventForm(forms.ModelForm):
    class Meta:
        model = Event
        fields = ['title', 'description', 'event_type', 'priority', 'start_date', 'end_date',
                  'start_time', 'end_time', 'registration_start_date', 'registration_end_date',
                  'location', 'venue_details', 'unit', 'max_participants', 'min_participants',
                  'is_mandatory', 'required_rank', 'status', 'is_featured', 'banner_image', 'attachment']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Event Title', 'required': True}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Event Description', 'required': True}),
            'event_type': forms.Select(attrs={'class': 'form-control', 'required': True}),
            'priority': forms.Select(attrs={'class': 'form-control'}),
            'start_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date', 'required': True}),
            'end_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date', 'required': True}),
            'start_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'end_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'registration_start_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'registration_end_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'location': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Event Location', 'required': True}),
            'venue_details': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'unit': forms.Select(attrs={'class': 'form-control', 'required': True}),
            'max_participants': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'min_participants': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'value': 0}),
            'required_rank': forms.TextInput(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
            'is_mandatory': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_featured': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'banner_image': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
            'attachment': forms.FileInput(attrs={'class': 'form-control'}),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        start_time = cleaned_data.get('start_time')
        end_time = cleaned_data.get('end_time')
        reg_start = cleaned_data.get('registration_start_date')
        reg_end = cleaned_data.get('registration_end_date')
        max_participants = cleaned_data.get('max_participants')
        min_participants = cleaned_data.get('min_participants')
        
        # Validate dates
        if start_date and end_date:
            if end_date < start_date:
                raise ValidationError('End date cannot be before start date.')
        
        # Validate times if provided
        if start_time and end_time and start_date == end_date:
            if end_time <= start_time:
                raise ValidationError('End time must be after start time for same-day events.')
        
        # Validate registration dates
        if reg_start and reg_end:
            if reg_end < reg_start:
                raise ValidationError('Registration end date cannot be before start date.')
        
        if reg_end and start_date:
            if reg_end > start_date:
                raise ValidationError('Registration must close before event starts.')
        
        # Validate participant numbers
        if max_participants and min_participants:
            if max_participants < min_participants:
                raise ValidationError('Maximum participants cannot be less than minimum participants.')
        
        return cleaned_data




class EventResourceForm(forms.ModelForm):
    class Meta:
        model = EventResource
        fields = ['resource_type', 'name', 'description', 'quantity', 'estimated_cost', 'is_available']
        widgets = {
            'resource_type': forms.Select(attrs={'class': 'form-control'}),
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control'}),
            'estimated_cost': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'is_available': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class EventAnnouncementForm(forms.ModelForm):
    class Meta:
        model = EventAnnouncement
        fields = ['title', 'message', 'is_important']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'message': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'is_important': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class EventParticipationForm(forms.ModelForm):
    class Meta:
        model = EventParticipation
        fields = ['attendance_status', 'performance_rating', 'position', 'award', 'feedback', 'certificate_issued']
        widgets = {
            'attendance_status': forms.Select(attrs={'class': 'form-control'}),
            'performance_rating': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 10}),
            'position': forms.NumberInput(attrs={'class': 'form-control'}),
            'award': forms.TextInput(attrs={'class': 'form-control'}),
            'feedback': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'certificate_issued': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }