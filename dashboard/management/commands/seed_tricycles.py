from django.core.management.base import BaseCommand
from dashboard.models import Tricycle

class Command(BaseCommand):
    help = 'Seeds the database with realistic Angeles City Tricycle data'

    def handle(self, *args, **kwargs):
        # List of realistic mock data for Angeles City (Numbers only for body_number)
        tricycles_data = [
            # Exact unit from your reference photo
            {
                "body_number": "3-1838",
                "driver_name": "Roberto P. Mallari",
                "toda_branch": "UCPB TODA (FEDTODA)",
                "status": "Verified",
            },
            # Zone 1: Balibago / Astro Park / Diamond Subdivision
            {
                "body_number": "1-0412",
                "driver_name": "Efren M. Laxamana",
                "toda_branch": "BALIBAGO TODA (FEDTODA)",
                "status": "Verified",
            },
            {
                "body_number": "1-1109",
                "driver_name": "RodelIO G. Pangilinan",
                "toda_branch": "ASTRO MARISOL TODA (FEDTODA)",
                "status": "Verified",
            },
            {
                "body_number": "1-2045",
                "driver_name": "Danilo S. Dizon",
                "toda_branch": "DIAMOND TODA (FEDTODA)",
                "status": "Verified",
            },
            # Zone 2: Pampang / Cutcut / Nepo Mart / Santo Rosario
            {
                "body_number": "2-0819",
                "driver_name": "Arnel T.Quiambao",
                "toda_branch": "PAMPANG TODA (FEDTODA)",
                "status": "Verified",
            },
            {
                "body_number": "2-1540",
                "driver_name": "Joselito B. Manalo",
                "toda_branch": "NEPO CUTCUT TODA (FEDTODA)",
                "status": "Verified",
            },
            {
                "body_number": "2-2291",
                "driver_name": "Reynaldo C. David",
                "toda_branch": "VILLA SOL TODA (FEDTODA)",
                "status": "Verified",
            },
            # Zone 3: Pandan / Cutud / Mining / Marquee
            {
                "body_number": "3-0924",
                "driver_name": "Noli V. Henson",
                "toda_branch": "PANDAN CITICENTER TODA (FEDTODA)",
                "status": "Verified",
            },
            {
                "body_number": "3-1402",
                "driver_name": "Ferdinand R.ineda",
                "toda_branch": "CUTUD MINING TODA (FEDTODA)",
                "status": "Verified",
            },
            {
                "body_number": "3-2350",
                "driver_name": "Noel A. Guevarra",
                "toda_branch": "PULUNG MARAGUL TODA (FEDTODA)",
                "status": "Verified",
            },
            # Zone 4: Malabanias / Clark Perimeter / Friendship
            {
                "body_number": "4-0633",
                "driver_name": "Edgardo L. Bondoc",
                "toda_branch": "MALABANIAS TODA (FEDTODA)",
                "status": "Verified",
            },
            {
                "body_number": "4-1788",
                "driver_name": "Lito M. Tayag",
                "toda_branch": "FRIENDSHIP ANUNAS TODA (FEDTODA)",
                "status": "Verified",
            },
            # Zone 5: Sapangbato / Margot
            {
                "body_number": "5-0315",
                "driver_name": "Ruben D. Aguas",
                "toda_branch": "SAPANGBATO TODA (FEDTODA)",
                "status": "Verified",
            },
            # 🚨 Edge Cases for Defense Demo (Unverified / Crowdsourced Flagged / Suspended)
            {
                "body_number": "3-4910",
                "driver_name": "⚠️ URGENT REVIEW (3+ Reports)",
                "toda_branch": "Unknown (Flagged via App)",
                "status": "Unverified",
            },
            {
                "body_number": "1-3877",
                "driver_name": "Rommel C. Sarmiento",
                "toda_branch": "BALIBAGO TODA (FEDTODA)",
                "status": "Suspended",
            },
        ]

        self.stdout.write('Seeding Tricycle data...')

        count = 0
        for data in tricycles_data:
            # get_or_create prevents duplicates if you run the script twice!
            obj, created = Tricycle.objects.get_or_create(
                body_number=data['body_number'],
                defaults=data
            )
            if created:
                count += 1

        self.stdout.write(self.style.SUCCESS(f'Successfully added {count} tricycles to the registry!'))