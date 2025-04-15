from rest_framework.authentication import SessionAuthentication
from django.contrib.auth.backends import BaseBackend
from django.contrib.auth import get_user_model
import logging

logger = logging.getLogger(__name__)

class CustomAuthenticationBackend(BaseBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        User = get_user_model()
        if not username:
            logger.warning("Authentication attempted with no username.")
            return None

        # Validate username length to prevent malformed inputs
        if len(username) > 255:
            logger.warning("Authentication attempted with excessively long username.")
            return None

        # Normalize phone number by removing spaces and dashes
        if not '@' in username:
            username = username.replace(" ", "").replace("-", "")

        # Try email first
        if '@' in username:
            try:
                user = User.objects.get(email=username)
            except User.DoesNotExist:
                logger.info(f"User with email not found (length: {len(username)}).")
                return None
        else:
            # Try phone number
            try:
                user = User.objects.get(phone_number=username)
            except User.DoesNotExist:
                logger.info(f"User with phone number not found (length: {len(username)}).")
                return None

        if user and user.is_active and user.check_password(password):
            logger.info(f"User {user.id} authenticated successfully.")
            return user
        logger.warning(f"Authentication failed for user ID {user.id if user else 'unknown'}: Invalid password or inactive user.")
        return None

    def get_user(self, user_id):
        try:
            user = get_user_model().objects.get(pk=user_id)
            return user
        except User.DoesNotExist:
            logger.warning(f"User with ID {user_id} not found.")
            return None


class CsrfExemptSessionAuthentication(SessionAuthentication):
    """
    A custom session authentication class that does not enforce CSRF checks.
    WARNING: Use only in development. In production, use proper CSRF handling or token-based auth.
    """
    def enforce_csrf(self, request):
        return  # Do nothing – disables CSRF validation