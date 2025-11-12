from django import forms
from .models import Achievement

class AchievementForm(forms.ModelForm):
    class Meta:
        model = Achievement
        fields = ['cadet', 'title', 'achievement_type', 'level', 'description', 
                  'date_awarded', 'awarded_by', 'event', 'training', 'position', 
                  'citation', 'certificate_file', 'photo', 'verified', 'remarks']
        widgets = {
            'cadet': forms.Select(attrs={'class': 'form-control'}),
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Achievement Title'}),
            'achievement_type': forms.Select(attrs={'class': 'form-control'}),
            'level': forms.Select(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'date_awarded': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'awarded_by': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Authority Name'}),
            'event': forms.Select(attrs={'class': 'form-control'}),
            'training': forms.Select(attrs={'class': 'form-control'}),
            'position': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Rank/Position'}),
            'citation': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'certificate_file': forms.FileInput(attrs={'class': 'form-control'}),
            'photo': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
            'verified': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'remarks': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }
