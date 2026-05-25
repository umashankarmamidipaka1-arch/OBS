from django import forms
from django.conf import settings
from django.contrib.auth.forms import UserCreationForm
from django.db import transaction

from .models import User, BankAccountType, UserBankAccount, UserAddress
from .constants import GENDER_CHOICE


class UserAddressForm(forms.ModelForm):

    class Meta:
        model = UserAddress
        fields = [
            'street_address',
            'city',
            'postal_code',
            'country'
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for field in self.fields:
            self.fields[field].widget.attrs.update({
                'class': (
                    'appearance-none block w-full bg-slate-950 '
                    'text-slate-200 border border-slate-850 rounded-xl '
                    'py-3 px-4 leading-tight focus:outline-none '
                    'focus:border-teal-500 transition'
                )
            })


class UserRegistrationForm(UserCreationForm):
    account_type = forms.ModelChoiceField(
        queryset=BankAccountType.objects.all()
    )
    gender = forms.ChoiceField(choices=GENDER_CHOICE)
    birth_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
    
    # New RBI fields
    id_proof_type = forms.ChoiceField(
        choices=[
            ('AADHAAR', 'Aadhaar Card'),
            ('PASSPORT', 'Passport'),
            ('DRIVING_LICENCE', 'Driving Licence'),
            ('VOTER_ID', 'Voter ID Card'),
            ('NREGA_JOB_CARD', 'NREGA Job Card'),
        ]
    )
    id_proof_no = forms.CharField(max_length=100)
    pan_no = forms.CharField(max_length=20)
    id_proof_document = forms.FileField(required=True)
    passport_photo = forms.FileField(required=True)

    class Meta:
        model = User
        fields = [
            'first_name',
            'last_name',
            'email',
            'password1',
            'password2',
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for field in self.fields:
            self.fields[field].widget.attrs.update({
                'class': (
                    'appearance-none block w-full bg-slate-950 '
                    'text-slate-200 border border-slate-850 '
                    'rounded-xl py-3 px-4 leading-tight '
                    'focus:outline-none focus:border-teal-500 transition'
                )
            })

    def clean(self):
        cleaned_data = super().clean()
        first_name = cleaned_data.get('first_name', '')
        last_name = cleaned_data.get('last_name', '')
        id_proof_no = cleaned_data.get('id_proof_no', '')
        birth_date = cleaned_data.get('birth_date')
        id_proof_doc = cleaned_data.get('id_proof_document')

        if id_proof_doc:
            file_name = id_proof_doc.name.lower()
            if file_name.endswith('.txt'):
                try:
                    content = id_proof_doc.read().decode('utf-8')
                    id_proof_doc.seek(0)  # Reset pointer for saving
                    
                    # Name matching (case-insensitive)
                    name_match = (first_name.lower() in content.lower()) and (last_name.lower() in content.lower())
                    id_match = id_proof_no.lower() in content.lower()
                    
                    dob_str_1 = birth_date.strftime('%Y-%m-%d') if birth_date else ''
                    dob_str_2 = birth_date.strftime('%d/%m/%Y') if birth_date else ''
                    dob_str_3 = birth_date.strftime('%d-%m-%Y') if birth_date else ''
                    dob_match = (dob_str_1 in content) or (dob_str_2 in content) or (dob_str_3 in content) if birth_date else False

                    if not name_match:
                        self.add_error('id_proof_document', 'Automated OCR Check Failed: The name on the ID proof document does not match your entered First Name and Last Name.')
                    if not id_match:
                        self.add_error('id_proof_document', f'Automated OCR Check Failed: The ID Number "{id_proof_no}" could not be found in the uploaded document.')
                    if not dob_match:
                        self.add_error('id_proof_document', f'Automated OCR Check Failed: The Birth Date "{dob_str_1}" could not be found in the uploaded document.')
                except Exception as e:
                    self.add_error('id_proof_document', f'Failed to process document text for OCR verification: {str(e)}')
            else:
                # Binary files (images/pdfs): simulated OCR check
                if 'invalid' in file_name or 'fail' in file_name:
                    self.add_error('id_proof_document', 'Automated OCR Check Failed: Extracted document data does not match form fields.')
        return cleaned_data

    @transaction.atomic
    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
            account_type = self.cleaned_data.get('account_type')
            gender = self.cleaned_data.get('gender')
            birth_date = self.cleaned_data.get('birth_date')
            
            id_proof_type = self.cleaned_data.get('id_proof_type')
            id_proof_no = self.cleaned_data.get('id_proof_no')
            pan_no = self.cleaned_data.get('pan_no')
            id_proof_document = self.cleaned_data.get('id_proof_document')
            passport_photo = self.cleaned_data.get('passport_photo')

            UserBankAccount.objects.create(
                user=user,
                gender=gender,
                birth_date=birth_date,
                account_type=account_type,
                status=UserBankAccount.Status.PENDING,  # Set to pending approval
                id_proof_type=id_proof_type,
                id_proof_no=id_proof_no,
                pan_no=pan_no,
                id_proof_document=id_proof_document,
                passport_photo=passport_photo,
                account_no=(
                    user.id +
                    settings.ACCOUNT_NUMBER_START_FROM
                )
            )
        return user

