from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import (
    UserCreationForm, PasswordChangeForm, PasswordResetForm, SetPasswordForm
)
from django.utils import timezone
from .models import UserProfile, UserPreference, UserPrivacySetting

User = get_user_model()

RESERVED_USERNAMES = {
    'admin', 'administrator', 'accounts', 'friends', 'chat', 'stories', 'notifications',
    'settings', 'login', 'logout', 'register', 'api', 'static', 'media',
    'dashboard', 'connectbook', 'groups', 'pages', 'events', 'marketplace',
    'live', 'feed', 'search', 'password-reset', 'forgot-password'
}


class RegisterForm(UserCreationForm):
    first_name = forms.CharField(max_length=30, required=True, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'First name'}))
    last_name = forms.CharField(max_length=30, required=True, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Last name'}))
    username = forms.CharField(max_length=150, required=True, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Username'}))
    email = forms.EmailField(required=True, widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email address'}))
    date_of_birth = forms.DateField(required=False, widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}))
    gender = forms.ChoiceField(choices=User.GENDER_CHOICES, required=False, widget=forms.Select(attrs={'class': 'form-select'}))

    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'username', 'email', 'date_of_birth', 'gender')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'password1' in self.fields:
            self.fields['password1'].widget.attrs.update({
                'class': 'form-control',
                'placeholder': 'New password',
                'autocomplete': 'new-password'
            })
        if 'password2' in self.fields:
            self.fields['password2'].widget.attrs.update({
                'class': 'form-control',
                'placeholder': 'Confirm password',
                'autocomplete': 'new-password'
            })

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip()
        if email and User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email

    def clean_username(self):
        username = self.cleaned_data.get('username', '').strip()
        if username:
            if username.lower() in RESERVED_USERNAMES:
                raise forms.ValidationError("This username is reserved. Please choose another username.")
            if User.objects.filter(username__iexact=username).exists():
                raise forms.ValidationError("A user with this username already exists.")
        return username

    def clean_date_of_birth(self):
        dob = self.cleaned_data.get('date_of_birth')
        if dob:
            if dob > timezone.now().date():
                raise forms.ValidationError("Date of birth cannot be in the future.")
            if dob.year < 1900:
                raise forms.ValidationError("Please enter a valid date of birth (after 1900).")
        return dob


class LoginForm(forms.Form):
    login = forms.CharField(label="Username or Email", widget=forms.TextInput(attrs={'class': 'form-control form-control-lg', 'placeholder': 'Email or username'}))
    password = forms.CharField(label="Password", widget=forms.PasswordInput(attrs={'class': 'form-control form-control-lg', 'placeholder': 'Password'}))
    remember_me = forms.BooleanField(required=False, widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}))


class UserProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = [
            'bio', 'avatar', 'cover_photo', 'city', 'hometown',
            'work', 'education', 'website', 'relationship_status',
            'profile_visibility', 'show_email', 'show_dob'
        ]
        widgets = {
            'bio': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Add a short bio...'}),
            'avatar': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
            'cover_photo': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
            'city': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Current city'}),
            'hometown': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Hometown'}),
            'work': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Workplace / Company'}),
            'education': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'School or University'}),
            'website': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://example.com'}),
            'relationship_status': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Single, In a relationship, etc.'}),
            'profile_visibility': forms.Select(attrs={'class': 'form-select'}),
            'show_email': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'show_dob': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def clean_avatar(self):
        avatar = self.cleaned_data.get('avatar')
        if avatar and hasattr(avatar, 'size') and avatar.size > 5 * 1024 * 1024:
            raise forms.ValidationError("Avatar image size must be under 5MB.")
        return avatar

    def clean_cover_photo(self):
        cover = self.cleaned_data.get('cover_photo')
        if cover and hasattr(cover, 'size') and cover.size > 5 * 1024 * 1024:
            raise forms.ValidationError("Cover photo size must be under 5MB.")
        return cover


class UserBasicInfoForm(forms.ModelForm):
    first_name = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    last_name = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    email = forms.EmailField(required=True, widget=forms.EmailInput(attrs={'class': 'form-control'}))
    date_of_birth = forms.DateField(required=False, widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}))
    gender = forms.ChoiceField(choices=User.GENDER_CHOICES, required=False, widget=forms.Select(attrs={'class': 'form-select'}))

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'date_of_birth', 'gender']

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email:
            qs = User.objects.filter(email__iexact=email)
            if self.instance and self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError("An account with this email already exists.")
        return email

    def clean_date_of_birth(self):
        dob = self.cleaned_data.get('date_of_birth')
        if dob:
            if dob > timezone.now().date():
                raise forms.ValidationError("Date of birth cannot be in the future.")
            if dob.year < 1900:
                raise forms.ValidationError("Please enter a valid date of birth (after 1900).")
        return dob


class ConnectBookPasswordChangeForm(PasswordChangeForm):
    """Custom PasswordChangeForm providing uniform Bootstrap form-control styling."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'form-control'})


class ConnectBookPasswordResetForm(PasswordResetForm):
    """Custom PasswordResetForm providing uniform Bootstrap form-control styling."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['email'].widget.attrs.update({
            'class': 'form-control form-control-lg',
            'placeholder': 'Enter your registered email address',
            'autocomplete': 'email'
        })
        self.reset_url_name = 'accounts:password_reset_confirm'


class ConnectBookSetPasswordForm(SetPasswordForm):
    """Custom SetPasswordForm providing uniform Bootstrap form-control styling."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({
                'class': 'form-control',
                'autocomplete': 'new-password'
            })



class UserPrivacySettingForm(forms.ModelForm):
    tagging_permission = forms.ChoiceField(
        choices=UserPrivacySetting.PERMISSION_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    mention_permission = forms.ChoiceField(
        choices=UserPrivacySetting.PERMISSION_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    class Meta:
        model = UserPrivacySetting
        fields = [
            'profile_visibility', 'post_default_audience', 'story_privacy',
            'friend_request_permission', 'message_permission',
            'tagging_permission', 'mention_permission',
            'search_discoverability', 'read_receipts', 'online_status_visible',
            'friends_list_visibility'
        ]
        widgets = {
            'profile_visibility': forms.Select(attrs={'class': 'form-select'}),
            'post_default_audience': forms.Select(attrs={'class': 'form-select'}),
            'story_privacy': forms.Select(attrs={'class': 'form-select'}),
            'friend_request_permission': forms.Select(attrs={'class': 'form-select'}),
            'message_permission': forms.Select(attrs={'class': 'form-select'}),
            'friends_list_visibility': forms.Select(attrs={'class': 'form-select'}),
            'search_discoverability': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'read_receipts': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'online_status_visible': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def clean_tagging_permission(self):
        val = self.cleaned_data.get('tagging_permission')
        if not val and self.instance:
            return self.instance.tagging_permission or 'friends'
        return val or 'friends'

    def clean_mention_permission(self):
        val = self.cleaned_data.get('mention_permission')
        if not val and self.instance:
            return self.instance.mention_permission or 'everyone'
        return val or 'everyone'

