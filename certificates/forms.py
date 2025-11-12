from django import forms
from .models import Certificate

class CertificateForm(forms.ModelForm):
    class Meta:
        model = Certificate
        fields = ['certificate_type', 'cadet', 'title', 'description', 'issued_date',
                  'valid_until', 'event', 'training', 'grade', 'score', 'certificate_file', 'status', 'remarks']
        widgets = {
            'certificate_type': forms.Select(attrs={'class': 'form-control'}),
            'cadet': forms.Select(attrs={'class': 'form-control'}),
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Certificate Title'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'issued_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'valid_until': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'event': forms.Select(attrs={'class': 'form-control'}),
            'training': forms.Select(attrs={'class': 'form-control'}),
            'grade': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'A+, A, B+, etc.'}),
            'score': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'certificate_file': forms.FileInput(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
            'remarks': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }
