from django.core.management.base import BaseCommand
from dashboard.models import Tricycle

class Command(BaseCommand):
    help = 'Seeds the database with realistic Angeles City Tricycle data'

    def handle(self, *args, **kwargs):
        # List of realistic mock data for Angeles City
        tricycles_data = [
            {'body_number': 'SMH-088', 'driver_name': 'Roberto Santos', 'toda_branch': 'SMH TODA (SM Clark)', 'plate_number': '123-QWE', 'status': 'Active'},
            {'body_number': 'SV-142', 'driver_name': 'Eduardo Macapagal', 'toda_branch': 'SV TODA (Pampang)', 'plate_number': '456-RTY', 'status': 'Active'},
            {'body_number': 'PG-024', 'driver_name': 'Luisito Pineda', 'toda_branch': 'PGTODA (Pandan Grotto)', 'plate_number': '789-UIO', 'status': 'Active'},
            {'body_number': 'BOTDA-005', 'driver_name': 'Arthur Manaloto', 'toda_branch': 'BOTDA (Balibago)', 'plate_number': '321-ASD', 'status': 'Maintenance'},
            {'body_number': 'CCA-011', 'driver_name': 'Mark Dizon', 'toda_branch': 'CCA TODA (City College)', 'plate_number': '555-XYZ', 'status': 'Active'},
            {'body_number': 'CCA-042', 'driver_name': 'Joel Reyes', 'toda_branch': 'CCA TODA (City College)', 'plate_number': '777-ABC', 'status': 'Active'},
            {'body_number': 'HTODA-099', 'driver_name': 'Dennis Garcia', 'toda_branch': 'HTODA (Holy Angel)', 'plate_number': '888-DEF', 'status': 'Suspended'},
            {'body_number': 'CTODA-076', 'driver_name': 'Arnel Bautista', 'toda_branch': 'CTODA (Carmelite)', 'plate_number': '222-GHI', 'status': 'Active'},
            {'body_number': 'NPTODA-018', 'driver_name': 'Ricky Tolentino', 'toda_branch': 'NPTODA (Nepo Quad)', 'plate_number': '444-JKL', 'status': 'Active'},
            {'body_number': 'FBTODA-033', 'driver_name': 'Crisanto Cruz', 'toda_branch': 'FBTODA (Marquee Mall)', 'plate_number': '999-MNO', 'status': 'Active'},
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