from django import forms
from .models import Page


class PageForm(forms.ModelForm):
    class Meta:
        model = Page
        fields = [
            'name', 'category', 'bio', 'description', 'avatar', 'cover_photo',
            'website', 'email', 'phone', 'address'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Page Name'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'bio': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Brief tagline or headline...'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Describe what your page is about...'}),
            'avatar': forms.FileInput(attrs={'class': 'form-control'}),
            'cover_photo': forms.FileInput(attrs={'class': 'form-control'}),
            'website': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://example.com'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'contact@example.com'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+1 555-0199'}),
            'address': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'City, State or Full Address'}),
        }
