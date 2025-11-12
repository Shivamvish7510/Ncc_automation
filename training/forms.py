from django import forms
from .models import Training, TrainingEnrollment

class TrainingForm(forms.ModelForm):
    class Meta:
        model = Training
        fields = ['title', 'description', 'training_type', 'duration_hours', 'instructor',
                  'start_date', 'end_date', 'unit', 'location', 'venue_details',
                  'max_participants', 'prerequisites', 'status', 'syllabus']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Training Title'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'training_type': forms.Select(attrs={'class': 'form-control'}),
            'duration_hours': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'instructor': forms.Select(attrs={'class': 'form-control'}),
            'start_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'end_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'unit': forms.Select(attrs={'class': 'form-control'}),
            'location': forms.TextInput(attrs={'class': 'form-control'}),
            'venue_details': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'max_participants': forms.NumberInput(attrs={'class': 'form-control'}),
            'prerequisites': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'status': forms.Select(attrs={'class': 'form-control'}),
            'syllabus': forms.FileInput(attrs={'class': 'form-control'}),
        }


class TrainingAssessmentForm(forms.ModelForm):
    class Meta:
        model = TrainingEnrollment
        fields = ['attendance_percentage', 'theory_score', 'practical_score', 
                  'overall_score', 'grade', 'completion_status', 'feedback', 'remarks']
        widgets = {
            'attendance_percentage': forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'min': 0, 'max': 100, 'step': 0.01}),
            'theory_score': forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'min': 0, 'max': 100, 'step': 0.01}),
            'practical_score': forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'min': 0, 'max': 100, 'step': 0.01}),
            'overall_score': forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'min': 0, 'max': 100, 'step': 0.01}),
            'grade': forms.TextInput(attrs={'class': 'form-control form-control-sm', 'placeholder': 'A+, A, B+, etc.'}),
            'completion_status': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'feedback': forms.Textarea(attrs={'class': 'form-control form-control-sm', 'rows': 2}),
            'remarks': forms.Textarea(attrs={'class': 'form-control form-control-sm', 'rows': 2}),
        }