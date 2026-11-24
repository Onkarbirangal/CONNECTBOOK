from django import forms
from .models import MarketplaceListing


class MarketplaceListingForm(forms.ModelForm):
    class Meta:
        model = MarketplaceListing
        fields = ['title', 'category', 'condition', 'price', 'location', 'description', 'image', 'status']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'What are you selling?'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'condition': forms.Select(attrs={'class': 'form-select'}),
            'price': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '0.00', 'step': '0.01'}),
            'location': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'City, State or Neighborhood'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Describe condition, features, pickup instructions...'}),
            'image': forms.FileInput(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
        }
