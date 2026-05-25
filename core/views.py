from django.views.generic import TemplateView
from django.shortcuts import redirect


class HomeView(TemplateView):
    template_name = 'core/index.html'

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            role = getattr(request.user, 'role', 'USER')
            if role == 'ADMIN':
                return redirect('accounts:admin_dashboard')
            elif role == 'BRANCH_MANAGER':
                return redirect('accounts:manager_dashboard')
            elif role == 'EMPLOYEE':
                return redirect('accounts:employee_dashboard')
            else:
                return redirect('accounts:user_dashboard')
        return super().dispatch(request, *args, **kwargs)

