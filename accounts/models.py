from decimal import Decimal

from django.contrib.auth.models import AbstractUser
from django.core.validators import (
    MinValueValidator,
    MaxValueValidator,
)
from django.db import models

from .constants import GENDER_CHOICE
from .managers import UserManager


class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = 'ADMIN', 'Admin'
        BRANCH_MANAGER = 'BRANCH_MANAGER', 'Branch Manager'
        EMPLOYEE = 'EMPLOYEE', 'Employee'
        USER = 'USER', 'Customer'

    username = None
    email = models.EmailField(unique=True, null=False, blank=False)
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.USER
    )

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    def __str__(self):
        return self.email

    @property
    def balance(self):
        if hasattr(self, 'account'):
            return self.account.balance
        return 0


class BankAccountType(models.Model):
    name = models.CharField(max_length=128)
    maximum_withdrawal_amount = models.DecimalField(
        decimal_places=2,
        max_digits=12
    )
    annual_interest_rate = models.DecimalField(
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        decimal_places=2,
        max_digits=5,
        help_text='Interest rate from 0 - 100'
    )
    interest_calculation_per_year = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(12)],
        help_text='The number of times interest will be calculated per year'
    )

    def __str__(self):
        return self.name

    def calculate_interest(self, principal):
        """
        Calculate interest for each account type.

        This uses a basic interest calculation formula
        """
        p = principal
        r = self.annual_interest_rate
        n = Decimal(self.interest_calculation_per_year)

        # Basic Future Value formula to calculate interest
        interest = (p * (1 + ((r/100) / n))) - p

        return round(interest, 2)


class UserBankAccount(models.Model):
    class Status(models.TextChoices):
        ACTIVE = 'ACTIVE', 'Active'
        SUSPENDED = 'SUSPENDED', 'Suspended'
        PENDING = 'PENDING', 'Pending Approval'
        REJECTED = 'REJECTED', 'Rejected'

    user = models.OneToOneField(
        User,
        related_name='account',
        on_delete=models.CASCADE,
    )
    account_type = models.ForeignKey(
        BankAccountType,
        related_name='accounts',
        on_delete=models.CASCADE
    )
    account_no = models.PositiveIntegerField(unique=True)
    gender = models.CharField(max_length=1, choices=GENDER_CHOICE)
    birth_date = models.DateField(null=True, blank=True)
    balance = models.DecimalField(
        default=0,
        max_digits=12,
        decimal_places=2
    )
    interest_start_date = models.DateField(
        null=True, blank=True,
        help_text=(
            'The month number that interest calculation will start from'
        )
    )
    initial_deposit_date = models.DateField(null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE
    )
    kyc_verified = models.BooleanField(default=False)
    saving_goal = models.DecimalField(
        default=0,
        max_digits=12,
        decimal_places=2
    )
    saving_goal_title = models.CharField(
        max_length=128,
        default="",
        blank=True
    )
    
    # RBI KYC details
    id_proof_type = models.CharField(
        max_length=50,
        choices=[
            ('AADHAAR', 'Aadhaar Card'),
            ('PASSPORT', 'Passport'),
            ('DRIVING_LICENCE', 'Driving Licence'),
            ('VOTER_ID', 'Voter ID Card'),
            ('NREGA_JOB_CARD', 'NREGA Job Card'),
        ],
        null=True,
        blank=True
    )
    id_proof_no = models.CharField(max_length=100, null=True, blank=True)
    pan_no = models.CharField(max_length=20, null=True, blank=True)
    id_proof_document = models.FileField(upload_to='id_proofs/', null=True, blank=True)
    passport_photo = models.FileField(upload_to='passport_photos/', null=True, blank=True)
    rejection_reason = models.TextField(default='', blank=True)

    def __str__(self):
        return str(self.account_no)

    def get_interest_calculation_months(self):
        """
        List of month numbers for which the interest will be calculated

        returns [2, 4, 6, 8, 10, 12] for every 2 months interval
        """
        interval = int(
            12 / self.account_type.interest_calculation_per_year
        )
        start = self.interest_start_date.month
        return [i for i in range(start, 13, interval)]


class UserAddress(models.Model):
    user = models.OneToOneField(
        User,
        related_name='address',
        on_delete=models.CASCADE,
    )
    street_address = models.CharField(max_length=512)
    city = models.CharField(max_length=256)
    postal_code = models.PositiveIntegerField()
    country = models.CharField(max_length=256)

    def __str__(self):
        return self.user.email


class VirtualCard(models.Model):
    account = models.ForeignKey(
        UserBankAccount,
        related_name='virtual_cards',
        on_delete=models.CASCADE
    )
    card_number = models.CharField(max_length=16, unique=True)
    cvv = models.CharField(max_length=3)
    expiry_date = models.DateField()
    limit = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=1000.00
    )
    is_frozen = models.BooleanField(default=False)
    card_holder = models.CharField(max_length=256)

    def __str__(self):
        return f"{self.card_holder} - **** **** **** {self.card_number[-4:]}"

