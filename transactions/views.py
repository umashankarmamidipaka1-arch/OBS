from dateutil.relativedelta import relativedelta

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import CreateView, ListView

from transactions.constants import DEPOSIT, WITHDRAWAL
from transactions.forms import (
    DepositForm,
    TransactionDateRangeForm,
    WithdrawForm,
)
from transactions.models import Transaction


class TransactionRepostView(LoginRequiredMixin, ListView):
    template_name = 'transactions/transaction_report.html'
    model = Transaction
    form_data = {}

    def get(self, request, *args, **kwargs):
        form = TransactionDateRangeForm(request.GET or None)
        if form.is_valid():
            self.form_data = form.cleaned_data

        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        queryset = super().get_queryset().filter(
            account=self.request.user.account
        )

        daterange = self.form_data.get("daterange")

        if daterange:
            queryset = queryset.filter(timestamp__date__range=daterange)

        return queryset.distinct()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'account': self.request.user.account,
            'form': TransactionDateRangeForm(self.request.GET or None)
        })

        return context


class TransactionCreateMixin(LoginRequiredMixin, CreateView):
    template_name = 'transactions/transaction_form.html'
    model = Transaction
    title = ''
    success_url = reverse_lazy('transactions:transaction_report')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({
            'account': self.request.user.account
        })
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'title': self.title
        })

        return context


class DepositMoneyView(TransactionCreateMixin):
    form_class = DepositForm
    title = 'Deposit Money to Your Account'

    def get_initial(self):
        initial = {'transaction_type': DEPOSIT}
        return initial

    def form_valid(self, form):
        amount = form.cleaned_data.get('amount')
        account = self.request.user.account

        if not account.initial_deposit_date:
            now = timezone.now()
            next_interest_month = int(
                12 / account.account_type.interest_calculation_per_year
            )
            account.initial_deposit_date = now
            account.interest_start_date = (
                now + relativedelta(
                    months=+next_interest_month
                )
            )

        account.balance += amount
        account.save(
            update_fields=[
                'initial_deposit_date',
                'balance',
                'interest_start_date'
            ]
        )

        messages.success(
            self.request,
            f'{amount}$ was deposited to your account successfully'
        )

        return super().form_valid(form)


class WithdrawMoneyView(TransactionCreateMixin):
    form_class = WithdrawForm
    title = 'Withdraw Money from Your Account'

    def get_initial(self):
        initial = {'transaction_type': WITHDRAWAL}
        return initial

    def form_valid(self, form):
        amount = form.cleaned_data.get('amount')

        self.request.user.account.balance -= form.cleaned_data.get('amount')
        self.request.user.account.save(update_fields=['balance'])

        messages.success(
            self.request,
            f'Successfully withdrawn {amount}$ from your account'
        )

        return super().form_valid(form)


from django.views.generic.edit import FormView
from django.views import View
from django.shortcuts import get_object_or_404, redirect
from django.db import transaction
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import UserPassesTestMixin

from accounts.models import UserBankAccount, VirtualCard
from transactions.forms import P2PTransferForm, LoanApplyForm, OTCForm
from transactions.models import Loan
import random

User = get_user_model()


class P2PTransferView(LoginRequiredMixin, FormView):
    template_name = 'transactions/transfer.html'
    form_class = P2PTransferForm
    success_url = reverse_lazy('accounts:user_dashboard')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['sender_account'] = self.request.user.account
        return kwargs

    @transaction.atomic
    def form_valid(self, form):
        sender_account = self.request.user.account
        receiver_account = form.cleaned_data['receiver_account']
        amount = form.cleaned_data['amount']

        sender_account.balance -= amount
        sender_account.save()

        receiver_account.balance += amount
        receiver_account.save()

        tx_sender = Transaction.objects.create(
            account=sender_account,
            receiver=receiver_account,
            amount=amount,
            balance_after_transaction=sender_account.balance,
            transaction_type=4
        )

        tx_receiver = Transaction.objects.create(
            account=receiver_account,
            receiver=sender_account,
            amount=amount,
            balance_after_transaction=receiver_account.balance,
            transaction_type=5
        )

        messages.success(
            self.request,
            f"Successfully transferred ${amount} to {receiver_account.user.get_full_name() or receiver_account.user.email} (Acct: {receiver_account.account_no})"
        )
        return super().form_valid(form)


class LoanApplyView(LoginRequiredMixin, FormView):
    template_name = 'transactions/loan_apply.html'
    form_class = LoanApplyForm
    success_url = reverse_lazy('accounts:user_dashboard')

    def form_valid(self, form):
        account = self.request.user.account
        amount = form.cleaned_data['amount']
        term = form.cleaned_data['term_months']
        
        interest_rate = account.account_type.annual_interest_rate + 2.00

        Loan.objects.create(
            account=account,
            amount=amount,
            term_months=term,
            interest_rate=interest_rate,
            status=Loan.Status.PENDING
        )

        messages.success(
            self.request,
            f"Loan request of ${amount} for {term} months submitted successfully. Awaiting approval."
        )
        return super().form_valid(form)


class GenerateVirtualCardView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        account = request.user.account
        
        if account.virtual_cards.count() >= 3:
            messages.error(request, "You can have a maximum of 3 virtual cards.")
            return redirect('accounts:user_dashboard')

        card_no = "".join([str(random.randint(0, 9)) for _ in range(16)])
        cvv = "".join([str(random.randint(0, 9)) for _ in range(3)])
        expiry = timezone.now().date() + relativedelta(years=4)
        
        VirtualCard.objects.create(
            account=account,
            card_number=card_no,
            cvv=cvv,
            expiry_date=expiry,
            card_holder=f"{request.user.first_name} {request.user.last_name}".strip().upper() or "VALUED CUSTOMER",
            limit=1000.00
        )
        messages.success(request, "New virtual debit card generated successfully!")
        return redirect('accounts:user_dashboard')


class ToggleVirtualCardFreezeView(LoginRequiredMixin, View):
    def post(self, request, card_id, *args, **kwargs):
        card = get_object_or_404(VirtualCard, id=card_id, account=request.user.account)
        card.is_frozen = not card.is_frozen
        card.save()
        status_text = "frozen" if card.is_frozen else "unfrozen"
        messages.success(request, f"Card ending in {card.card_number[-4:]} has been {status_text}.")
        return redirect('accounts:user_dashboard')


class DeleteVirtualCardView(LoginRequiredMixin, View):
    def post(self, request, card_id, *args, **kwargs):
        card = get_object_or_404(VirtualCard, id=card_id, account=request.user.account)
        card.delete()
        messages.success(request, "Virtual card deleted successfully.")
        return redirect('accounts:user_dashboard')


class EmployeeOTCTransactionView(LoginRequiredMixin, UserPassesTestMixin, FormView):
    template_name = 'transactions/otc_transaction.html'
    form_class = OTCForm
    success_url = reverse_lazy('accounts:employee_dashboard')

    def get_initial(self):
        initial = super().get_initial()
        account_no = self.request.GET.get('account')
        if account_no:
            initial['customer_account_no'] = account_no
        return initial

    def test_func(self):
        return self.request.user.role in ['EMPLOYEE', 'BRANCH_MANAGER', 'ADMIN']

    @transaction.atomic
    def form_valid(self, form):
        customer_account = form.cleaned_data['customer_account']
        amount = form.cleaned_data['amount']
        tx_type = int(form.cleaned_data['transaction_type'])

        if tx_type == 1:
            customer_account.balance += amount
            customer_account.save()
            Transaction.objects.create(
                account=customer_account,
                amount=amount,
                balance_after_transaction=customer_account.balance,
                transaction_type=1
            )
            messages.success(self.request, f"Successfully deposited ${amount} to account {customer_account.account_no}.")
        else:
            customer_account.balance -= amount
            customer_account.save()
            Transaction.objects.create(
                account=customer_account,
                amount=amount,
                balance_after_transaction=customer_account.balance,
                transaction_type=2
            )
            messages.success(self.request, f"Successfully withdrew ${amount} from account {customer_account.account_no}.")

        return super().form_valid(form)


class EmployeeKYCVerifyView(LoginRequiredMixin, UserPassesTestMixin, View):
    def post(self, request, account_id, *args, **kwargs):
        account = get_object_or_404(UserBankAccount, id=account_id)
        account.kyc_verified = True
        account.save()
        messages.success(request, f"Account {account.account_no} KYC verified successfully.")
        return redirect('accounts:employee_dashboard')

    def test_func(self):
        return self.request.user.role in ['EMPLOYEE', 'BRANCH_MANAGER', 'ADMIN']


class ManagerApproveLoanView(LoginRequiredMixin, UserPassesTestMixin, View):
    def post(self, request, loan_id, action, *args, **kwargs):
        loan = get_object_or_404(Loan, id=loan_id)
        if action == 'approve':
            with transaction.atomic():
                loan.status = Loan.Status.APPROVED
                loan.save()
                account = loan.account
                account.balance += loan.amount
                account.save()
                Transaction.objects.create(
                    account=account,
                    amount=loan.amount,
                    balance_after_transaction=account.balance,
                    transaction_type=1
                )
            messages.success(request, f"Loan of ${loan.amount} for account {loan.account.account_no} approved and disbursed.")
        else:
            loan.status = Loan.Status.REJECTED
            loan.save()
            messages.success(request, f"Loan of ${loan.amount} for account {loan.account.account_no} rejected.")

        return redirect('accounts:manager_dashboard')

    def test_func(self):
        return self.request.user.role in ['BRANCH_MANAGER', 'ADMIN']


class ManagerApproveAccountView(LoginRequiredMixin, UserPassesTestMixin, View):
    def post(self, request, account_id, action, *args, **kwargs):
        account = get_object_or_404(UserBankAccount, id=account_id)
        if action == 'approve':
            account.status = UserBankAccount.Status.ACTIVE
            account.kyc_verified = True
            messages.success(request, f"Account {account.account_no} activated and KYC verified successfully.")
        elif action == 'suspend':
            account.status = UserBankAccount.Status.SUSPENDED
            messages.success(request, f"Account {account.account_no} suspended successfully.")
        elif action == 'reject':
            rejection_reason = request.POST.get('rejection_reason', 'Identity documents or details did not match KYC requirements.')
            account.status = UserBankAccount.Status.REJECTED
            account.rejection_reason = rejection_reason
            messages.warning(request, f"Account {account.account_no} registration request has been rejected.")
        account.save()
        return redirect('accounts:manager_dashboard')

    def test_func(self):
        return self.request.user.role in ['BRANCH_MANAGER', 'ADMIN']


class AdminUpdateRoleView(LoginRequiredMixin, UserPassesTestMixin, View):
    def post(self, request, user_id, *args, **kwargs):
        target_user = get_object_or_404(User, id=user_id)
        new_role = request.POST.get('role')
        if new_role in User.Role.values:
            target_user.role = new_role
            target_user.save()
            messages.success(request, f"Updated role for {target_user.email} to {target_user.get_role_display()}.")
        else:
            messages.error(request, "Invalid role selection.")
        return redirect('accounts:admin_dashboard')

    def test_func(self):
        return self.request.user.role == 'ADMIN'

