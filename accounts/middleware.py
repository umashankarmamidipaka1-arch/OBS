from django.shortcuts import redirect
from django.urls import reverse
from accounts.models import UserBankAccount

class KYCRequiredMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            # Only restrict user role
            if request.user.role == 'USER' and hasattr(request.user, 'account'):
                account = request.user.account
                if account.status in [UserBankAccount.Status.PENDING, UserBankAccount.Status.REJECTED]:
                    allowed_paths = [
                        reverse('accounts:user_dashboard'),
                        reverse('accounts:user_logout'),
                        reverse('accounts:reset_registration'),
                    ]
                    # Check if requested path is allowed or is media
                    if request.path not in allowed_paths and not request.path.startswith('/media/') and not request.path.startswith('/static/'):
                        return redirect('accounts:user_dashboard')
        return self.get_response(request)
