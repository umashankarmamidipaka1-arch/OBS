from django.contrib import messages
from django.contrib.auth import get_user_model, login, logout
from django.contrib.auth.views import LoginView
from django.shortcuts import HttpResponseRedirect, redirect, render
from django.urls import reverse_lazy
from django.views.generic import TemplateView, RedirectView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db import models

from .forms import UserRegistrationForm, UserAddressForm
from .models import UserBankAccount, VirtualCard
from transactions.models import Transaction, Loan
from transactions.forms import SavingGoalForm

User = get_user_model()


class UserRegistrationView(TemplateView):
    model = User
    form_class = UserRegistrationForm
    template_name = 'accounts/user_registration.html'

    def dispatch(self, request, *args, **kwargs):
        if self.request.user.is_authenticated:
            return HttpResponseRedirect(
                reverse_lazy('accounts:user_dashboard')
            )
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        registration_form = UserRegistrationForm(self.request.POST, self.request.FILES)
        address_form = UserAddressForm(self.request.POST)

        if registration_form.is_valid() and address_form.is_valid():
            user = registration_form.save()
            address = address_form.save(commit=False)
            address.user = user
            address.save()

            login(self.request, user)
            messages.success(
                self.request,
                (
                    f'Your account request has been successfully submitted! '
                    f'Your Account Number is {user.account.account_no}. '
                    f'Please wait for the Branch Manager to approve your credentials.'
                )
            )
            return HttpResponseRedirect(
                reverse_lazy('accounts:user_dashboard')
            )

        return self.render_to_response(
            self.get_context_data(
                registration_form=registration_form,
                address_form=address_form
            )
        )

    def get_context_data(self, **kwargs):
        if 'registration_form' not in kwargs:
            kwargs['registration_form'] = UserRegistrationForm()
        if 'address_form' not in kwargs:
            kwargs['address_form'] = UserAddressForm()

        return super().get_context_data(**kwargs)


class UserLoginView(LoginView):
    template_name = 'accounts/user_login.html'
    redirect_authenticated_user = True

    def get_success_url(self):
        url = self.get_redirect_url()
        if url:
            return url
        
        user = self.request.user
        if user.role == User.Role.ADMIN:
            return reverse_lazy('accounts:admin_dashboard')
        elif user.role == User.Role.BRANCH_MANAGER:
            return reverse_lazy('accounts:manager_dashboard')
        elif user.role == User.Role.EMPLOYEE:
            return reverse_lazy('accounts:employee_dashboard')
        else:
            return reverse_lazy('accounts:user_dashboard')


class LogoutView(RedirectView):
    pattern_name = 'home'

    def get_redirect_url(self, *args, **kwargs):
        if self.request.user.is_authenticated:
            logout(self.request)
        return super().get_redirect_url(*args, **kwargs)


class UserDashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'accounts/user_dashboard.html'

    def get(self, request, *args, **kwargs):
        if hasattr(request.user, 'account'):
            account = request.user.account
            if account.status in [UserBankAccount.Status.PENDING, UserBankAccount.Status.REJECTED]:
                return render(request, 'accounts/user_pending.html', {'account': account})
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        if not hasattr(user, 'account'):
            context['has_account'] = False
            return context
            
        account = user.account
        context['has_account'] = True
        context['account'] = account
        context['transactions'] = Transaction.objects.filter(account=account).order_by('-timestamp')[:5]
        context['loans'] = Loan.objects.filter(account=account).order_by('-created_at')
        context['virtual_cards'] = VirtualCard.objects.filter(account=account)
        
        # Category totals for spending chart (withdrawals & sent transfers)
        withdrawals = Transaction.objects.filter(account=account, transaction_type=2)
        transfers_sent = Transaction.objects.filter(account=account, transaction_type=4)
        
        context['total_withdrawn'] = sum(t.amount for t in withdrawals)
        context['total_transferred'] = sum(t.amount for t in transfers_sent)
        
        context['saving_goal_form'] = SavingGoalForm(initial={
            'saving_goal_title': account.saving_goal_title,
            'saving_goal': account.saving_goal
        })
        
        if account.saving_goal > 0:
            context['goal_percentage'] = min(int((account.balance / account.saving_goal) * 100), 100)
        else:
            context['goal_percentage'] = 0
            
        return context

    def post(self, request, *args, **kwargs):
        if not hasattr(request.user, 'account'):
            return redirect('home')
        account = request.user.account
        form = SavingGoalForm(request.POST)
        if form.is_valid():
            account.saving_goal_title = form.cleaned_data['saving_goal_title']
            account.saving_goal = form.cleaned_data['saving_goal']
            account.save(update_fields=['saving_goal_title', 'saving_goal'])
            messages.success(request, "Savings goal updated successfully!")
        return redirect('accounts:user_dashboard')


class EmployeeDashboardView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'accounts/employee_dashboard.html'

    def test_func(self):
        return self.request.user.role in ['EMPLOYEE', 'BRANCH_MANAGER', 'ADMIN']

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        query = self.request.GET.get('q', '')
        if query:
            accounts = UserBankAccount.objects.filter(
                models.Q(account_no__icontains=query) |
                models.Q(user__email__icontains=query) |
                models.Q(user__first_name__icontains=query) |
                models.Q(user__last_name__icontains=query)
            )
        else:
            accounts = UserBankAccount.objects.all()[:10]
            
        context['accounts'] = accounts
        context['query'] = query
        context['pending_kyc'] = UserBankAccount.objects.filter(kyc_verified=False)
        return context


class ManagerDashboardView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'accounts/manager_dashboard.html'

    def test_func(self):
        return self.request.user.role in ['BRANCH_MANAGER', 'ADMIN']

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['pending_loans'] = Loan.objects.filter(status=Loan.Status.PENDING)
        context['pending_accounts'] = UserBankAccount.objects.filter(status=UserBankAccount.Status.PENDING)
        context['all_accounts'] = UserBankAccount.objects.all()[:10]
        context['all_accounts_count'] = UserBankAccount.objects.count()
        context['total_bank_balance'] = sum(acc.balance for acc in UserBankAccount.objects.all())
        context['total_loans_approved'] = Loan.objects.filter(status=Loan.Status.APPROVED).count()
        return context



class AdminDashboardView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'accounts/admin_dashboard.html'

    def test_func(self):
        return self.request.user.role == 'ADMIN'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['users'] = User.objects.all().order_by('email')
        context['global_transactions'] = Transaction.objects.all().order_by('-timestamp')[:20]
        context['role_choices'] = User.Role.choices
        return context


class ResetRegistrationView(LoginRequiredMixin, UserPassesTestMixin, RedirectView):
    pattern_name = 'accounts:user_registration'

    def test_func(self):
        return (
            self.request.user.role == User.Role.USER and
            hasattr(self.request.user, 'account') and
            self.request.user.account.status == UserBankAccount.Status.REJECTED
        )

    def post(self, request, *args, **kwargs):
        user = request.user
        logout(request)
        user.delete()
        messages.success(request, "Your application has been cleared. You may now fill in the details again.")
        return redirect('accounts:user_registration')


