from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from dashboard.models import UserProfile

class Command(BaseCommand):
    help = 'Wipes existing test accounts and builds the production LGU and TODA base roles'

    def handle(self, *args, **kwargs):
        self.stdout.write("Initializing System Roles...")

        # 1. Create the LGU / PTRO Officer
        lgu_user, created = User.objects.get_or_create(username='ptro_admin', email='ptro@angelescity.gov.ph')
        if created:
            lgu_user.set_password('fair_admin2026')
            lgu_user.is_staff = True # Required to access admin panel
            lgu_user.save()
            
            UserProfile.objects.create(
                user=lgu_user,
                user_type='LGU',
                auth_provider='SYSTEM',
                is_discount_verified=False
            )
            self.stdout.write(self.style.SUCCESS('Successfully created LGU Admin (ptro_admin)'))

        # 2. Create the TODA President
        toda_user, created = User.objects.get_or_create(username='toda_pres', email='toda@angelescity.gov.ph')
        if created:
            toda_user.set_password('fair_toda2026')
            toda_user.is_staff = True
            toda_user.save()
            
            UserProfile.objects.create(
                user=toda_user,
                user_type='TODA',
                auth_provider='SYSTEM',
                is_discount_verified=False
            )
            self.stdout.write(self.style.SUCCESS('Successfully created TODA President (toda_pres)'))

        self.stdout.write(self.style.SUCCESS('System initialization complete!'))