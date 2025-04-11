# accounts/authentication.py
from rest_framework.authentication import SessionAuthentication

from django.contrib.auth.backends import BaseBackend
from django.contrib.auth import get_user_model

class CustomAuthenticationBackend(BaseBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        User = get_user_model()
        if not username:
            return None

        # Try email first
        if '@' in username:
            try:
                user = User.objects.get(email=username)
            except User.DoesNotExist:
                return None
        else:
            # Try phone number
            try:
                user = User.objects.get(phone_number=username)
            except User.DoesNotExist:
                return None

        if user and user.check_password(password):
            return user
        return None

    def get_user(self, user_id):
        try:
            return get_user_model().objects.get(pk=user_id)
        except User.DoesNotExist:
            return None




class CsrfExemptSessionAuthentication(SessionAuthentication):
    """
    A custom session authentication class that does not enforce CSRF checks.
    (Use only in development; for production, handle CSRF properly or use token-based auth.)
    """
    def enforce_csrf(self, request):
        return  # Do nothing – this disables CSRF validation