# accounts/authentication.py
from rest_framework.authentication import SessionAuthentication

class CsrfExemptSessionAuthentication(SessionAuthentication):
    """
    A custom session authentication class that does not enforce CSRF checks.
    (Use only in development; for production, handle CSRF properly or use token-based auth.)
    """
    def enforce_csrf(self, request):
        return  # Do nothing – this disables CSRF validation
