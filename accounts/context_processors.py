def user_profile_context(request):
    """Provides current user profile and preferences to all templates."""
    if request.user.is_authenticated:
        profile = getattr(request.user, 'profile', None)
        prefs = getattr(request.user, 'preferences', None)
        theme = prefs.theme if prefs else 'light'
        return {
            'current_user_profile': profile,
            'current_user_theme': theme,
            'current_user_prefs': prefs,
        }
    return {
        'current_user_profile': None,
        'current_user_theme': 'light',
        'current_user_prefs': None,
    }
