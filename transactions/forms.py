import datetime

from django import forms
from django.conf import settings

from .models import Transaction
from accounts.models import UserBankAccount



class TransactionForm(forms.ModelForm):

    class Meta:
        model = Transaction
        fields = [
            'amount',
            'transaction_type'
        ]

    def __init__(self, *args, **kwargs):
        self.account = kwargs.pop('account')
        super().__init__(*args, **kwargs)

        self.fields['transaction_type'].disabled = True
        self.fields['transaction_type'].widget = forms.HiddenInput()

    def save(self, commit=True):
        self.instance.account = self.account
        self.instance.balance_after_transaction = self.account.balance
        return super().save()


class DepositForm(TransactionForm):

    def clean_amount(self):
        min_deposit_amount = settings.MINIMUM_DEPOSIT_AMOUNT
        amount = self.cleaned_data.get('amount')

        if amount < min_deposit_amount:
            raise forms.ValidationError(
                f'You need to deposit at least {min_deposit_amount} $'
            )

        return amount


class WithdrawForm(TransactionForm):

    def clean_amount(self):
        account = self.account
        min_withdraw_amount = settings.MINIMUM_WITHDRAWAL_AMOUNT
        max_withdraw_amount = (
            account.account_type.maximum_withdrawal_amount
        )
        balance = account.balance

        amount = self.cleaned_data.get('amount')

        if amount < min_withdraw_amount:
            raise forms.ValidationError(
                f'You can withdraw at least {min_withdraw_amount} $'
            )

        if amount > max_withdraw_amount:
            raise forms.ValidationError(
                f'You can withdraw at most {max_withdraw_amount} $'
            )

        if amount > balance:
            raise forms.ValidationError(
                f'You have {balance} $ in your account. '
                'You can not withdraw more than your account balance'
            )

        return amount


class TransactionDateRangeForm(forms.Form):
    daterange = forms.CharField(required=False)

    def clean_daterange(self):
        daterange = self.cleaned_data.get("daterange")
        print(daterange)

        try:
            daterange = daterange.split(' - ')
            print(daterange)
            if len(daterange) == 2:
                for date in daterange:
                    datetime.datetime.strptime(date, '%Y-%m-%d')
                return daterange
            else:
                raise forms.ValidationError("Please select a date range.")
        except (ValueError, AttributeError):
            raise forms.ValidationError("Invalid date range")


class P2PTransferForm(forms.Form):
    receiver_account_no = forms.IntegerField(label="Receiver's Account Number")
    amount = forms.DecimalField(decimal_places=2, max_digits=12, label="Amount to Transfer")

    def __init__(self, *args, **kwargs):
        self.sender_account = kwargs.pop('sender_account')
        super().__init__(*args, **kwargs)
        for field in self.fields:
            self.fields[field].widget.attrs.update({
                'class': (
                    'appearance-none block w-full bg-gray-200 '
                    'text-gray-700 border border-gray-200 '
                    'rounded py-3 px-4 leading-tight '
                    'focus:outline-none focus:bg-white '
                    'focus:border-gray-500'
                )
            })

    def clean(self):
        cleaned_data = super().clean()
        receiver_no = cleaned_data.get('receiver_account_no')
        amount = cleaned_data.get('amount')

        if not receiver_no or not amount:
            return cleaned_data

        if amount <= 0:
            raise forms.ValidationError("Transfer amount must be positive.")

        if self.sender_account.account_no == receiver_no:
            raise forms.ValidationError("You cannot transfer money to your own account.")

        if self.sender_account.status != UserBankAccount.Status.ACTIVE:
            raise forms.ValidationError("Your account is not active.")

        if self.sender_account.balance < amount:
            raise forms.ValidationError(
                f"Insufficient balance. Your current balance is ${self.sender_account.balance}"
            )

        try:
            receiver_account = UserBankAccount.objects.get(account_no=receiver_no)
            if receiver_account.status != UserBankAccount.Status.ACTIVE:
                raise forms.ValidationError("The recipient account is suspended or pending approval.")
            cleaned_data['receiver_account'] = receiver_account
        except UserBankAccount.DoesNotExist:
            raise forms.ValidationError("Recipient account number does not exist.")

        return cleaned_data


class LoanApplyForm(forms.Form):
    amount = forms.DecimalField(decimal_places=2, max_digits=12, label="Loan Amount")
    term_months = forms.IntegerField(label="Duration (Months)")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields:
            self.fields[field].widget.attrs.update({
                'class': (
                    'appearance-none block w-full bg-gray-200 '
                    'text-gray-700 border border-gray-200 '
                    'rounded py-3 px-4 leading-tight '
                    'focus:outline-none focus:bg-white '
                    'focus:border-gray-500'
                )
            })

    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        if amount <= 0:
            raise forms.ValidationError("Loan amount must be greater than zero.")
        return amount

    def clean_term_months(self):
        term = self.cleaned_data.get('term_months')
        if term <= 0:
            raise forms.ValidationError("Term duration must be greater than zero.")
        return term


class OTCForm(forms.Form):
    customer_account_no = forms.IntegerField(label="Customer Account Number")
    amount = forms.DecimalField(decimal_places=2, max_digits=12, label="Amount")
    transaction_type = forms.ChoiceField(
        choices=[(1, 'Deposit'), (2, 'Withdrawal')],
        label="Transaction Type"
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields:
            self.fields[field].widget.attrs.update({
                'class': (
                    'appearance-none block w-full bg-gray-200 '
                    'text-gray-700 border border-gray-200 '
                    'rounded py-3 px-4 leading-tight '
                    'focus:outline-none focus:bg-white '
                    'focus:border-gray-500'
                )
            })

    def clean(self):
        cleaned_data = super().clean()
        account_no = cleaned_data.get('customer_account_no')
        amount = cleaned_data.get('amount')
        tx_type = int(cleaned_data.get('transaction_type') or 0)

        if not account_no or not amount:
            return cleaned_data

        if amount <= 0:
            raise forms.ValidationError("Amount must be positive.")

        try:
            customer_account = UserBankAccount.objects.get(account_no=account_no)
            if customer_account.status != UserBankAccount.Status.ACTIVE:
                raise forms.ValidationError("The customer account is suspended or pending.")
            cleaned_data['customer_account'] = customer_account
        except UserBankAccount.DoesNotExist:
            raise forms.ValidationError("Customer account number does not exist.")

        if tx_type == 2:  # Withdrawal
            if customer_account.balance < amount:
                raise forms.ValidationError(f"Customer has insufficient funds (Balance: ${customer_account.balance}).")
            if amount > customer_account.account_type.maximum_withdrawal_amount:
                raise forms.ValidationError(
                    f"Withdrawal amount exceeds account type limit of ${customer_account.account_type.maximum_withdrawal_amount}."
                )

        return cleaned_data


class SavingGoalForm(forms.Form):
    saving_goal_title = forms.CharField(max_length=128, label="Goal Title")
    saving_goal = forms.DecimalField(decimal_places=2, max_digits=12, label="Target Savings Goal ($)")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields:
            self.fields[field].widget.attrs.update({
                'class': (
                    'appearance-none block w-full bg-gray-200 '
                    'text-gray-700 border border-gray-200 '
                    'rounded py-3 px-4 leading-tight '
                    'focus:outline-none focus:bg-white '
                    'focus:border-gray-500'
                )
            })

    def clean_saving_goal(self):
        goal = self.cleaned_data.get('saving_goal')
        if goal < 0:
            raise forms.ValidationError("Savings goal cannot be negative.")
        return goal

