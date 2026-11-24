from django import forms
from .models import Event


class EventForm(forms.ModelForm):
    start_time = forms.DateTimeField(widget=forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}))
    end_time = forms.DateTimeField(required=False, widget=forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}))

    class Meta:
        model = Event
        fields = ['title', 'description', 'venue', 'start_time', 'end_time', 'privacy', 'cover_image']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Event Title'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Tell guests about your event...'}),
            'venue': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Location, Venue or Online URL'}),
            'privacy': forms.Select(attrs={'class': 'form-select'}),
            'cover_image': forms.FileInput(attrs={'class': 'form-control'}),
        }
