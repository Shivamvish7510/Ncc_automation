from django.core.management.base import BaseCommand
from units.models import Unit
from accounts.models import User, Officer, Cadet

class Command(BaseCommand):
    help = 'Create sample Unit, Officer, and Cadet data for NCC automation.'

    def handle(self, *args, **options):
        # Create Unit
        unit, created = Unit.objects.get_or_create(
            name="1st Delhi NCC",
            defaults={
                "wing": "ARMY",
                "unit_code": "DLI001",
                "location": "Delhi University",
                "contact_email": "delhi@ncc.in",
                "contact_phone": "9876543210"
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f"Unit '{unit.name}' created."))
        else:
            self.stdout.write(self.style.WARNING(f"Unit '{unit.name}' already exists."))

        # Create Officer
        officer_user, created = User.objects.get_or_create(
            username="officer1",
            defaults={
                "first_name": "John",
                "last_name": "Doe",
                "role": "OFFICER"
            }
        )
        if created:
            officer_user.set_password("officer123")
            officer_user.save()
            self.stdout.write(self.style.SUCCESS("Officer user 'officer1' created."))
        else:
            self.stdout.write(self.style.WARNING("Officer user 'officer1' already exists."))
        officer, created = Officer.objects.get_or_create(
            user=officer_user,
            defaults={
                "rank": "CAPT",
                "unit": unit,
                "employee_id": "OFF001",
                "joining_date": "2020-01-01"
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS("Officer profile created."))
        else:
            self.stdout.write(self.style.WARNING("Officer profile already exists."))

        # Create Cadet
        cadet_user, created = User.objects.get_or_create(
            username="cadet1",
            defaults={
                "first_name": "Rahul",
                "last_name": "Sharma",
                "role": "CADET"
            }
        )
        if created:
            cadet_user.set_password("cadet123")
            cadet_user.save()
            self.stdout.write(self.style.SUCCESS("Cadet user 'cadet1' created."))
        else:
            self.stdout.write(self.style.WARNING("Cadet user 'cadet1' already exists."))
        cadet, created = Cadet.objects.get_or_create(
            user=cadet_user,
            defaults={
                "rank": "CDT",
                "unit": unit,
                "enrollment_number": "NCC2024001",
                "enrollment_date": "2024-01-01",
                "college_name": "Delhi University",
                "course": "B.Tech",
                "year_of_study": 2,
                "roll_number": "DU2022001",
                "parent_name": "Mr. Sharma",
                "parent_phone": "9876543210",
                "emergency_contact": "9876543210"
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS("Cadet profile created."))
        else:
            self.stdout.write(self.style.WARNING("Cadet profile already exists."))

        self.stdout.write(self.style.SUCCESS("Sample data creation complete."))
