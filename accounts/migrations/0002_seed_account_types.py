from django.db import migrations

def create_default_account_types(apps, schema_editor):
    BankAccountType = apps.get_model('accounts', 'BankAccountType')
    BankAccountType.objects.get_or_create(
        name='Savings Account',
        maximum_withdrawal_amount=50000.00,
        annual_interest_rate=4.50,
        interest_calculation_per_year=12
    )
    BankAccountType.objects.get_or_create(
        name='Current Account',
        maximum_withdrawal_amount=100000.00,
        annual_interest_rate=0.00,
        interest_calculation_per_year=1
    )

def remove_default_account_types(apps, schema_editor):
    BankAccountType = apps.get_model('accounts', 'BankAccountType')
    BankAccountType.objects.filter(name__in=['Savings Account', 'Current Account']).delete()

class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(create_default_account_types, remove_default_account_types),
    ]
