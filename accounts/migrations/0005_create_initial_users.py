from django.db import migrations
from django.contrib.auth.hashers import make_password

def create_users(apps, schema_editor):
    User = apps.get_model('accounts', 'User')
    
    # Create Admin
    admin_email = "admin@adityabanking.com"
    if not User.objects.filter(email=admin_email).exists():
        admin = User(
            email=admin_email,
            first_name="System",
            last_name="Admin",
            role="ADMIN",
            password=make_password("SecureAdminPassword123!"),
            is_superuser=True,
            is_staff=True
        )
        admin.save()
        
    # Create Manager
    manager_email = "manager@adityabanking.com"
    if not User.objects.filter(email=manager_email).exists():
        manager = User(
            email=manager_email,
            first_name="Branch",
            last_name="Manager",
            role="BRANCH_MANAGER",
            password=make_password("SecureManagerPassword123!"),
            is_staff=False
        )
        manager.save()

class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0004_auto_20260525_1831'),
    ]

    operations = [
        migrations.RunPython(create_users),
    ]
