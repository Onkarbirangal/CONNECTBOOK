from django import forms
from .models import LiveStream


class LiveStreamForm(forms.ModelForm):
    scheduled_start = forms.DateTimeField(widget=forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}))
    category = forms.ChoiceField(choices=LiveStream.CATEGORY_CHOICES, required=False, initial='General', widget=forms.Select(attrs={'class': 'form-select'}))
    audience = forms.ChoiceField(choices=LiveStream.AUDIENCE_CHOICES, required=False, initial='public', widget=forms.Select(attrs={'class': 'form-select'}))
    slow_mode_seconds = forms.IntegerField(required=False, initial=0, widget=forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'max': 300, 'placeholder': 'Chat delay (seconds)'}))

    class Meta:
        model = LiveStream
        fields = ['title', 'description', 'category', 'audience', 'scheduled_start', 'thumbnail', 'slow_mode_seconds']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Live Stream Title'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'What will you be broadcasting about?'}),
            'thumbnail': forms.FileInput(attrs={'class': 'form-control'}),
        }
