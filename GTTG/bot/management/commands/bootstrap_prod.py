import os
from pathlib import Path
from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.contrib.auth import get_user_model

class Command(BaseCommand):
	help = "Create superuser from env and load fixtures (muscle groups, exercises). Idempotent."

	def handle(self, *args, **options):
		self._create_superuser_from_env()
		self._load_fixtures()

	def _create_superuser_from_env(self):
		username = os.getenv("DJANGO_SUPERUSER_USERNAME")
		email = os.getenv("DJANGO_SUPERUSER_EMAIL")
		password = os.getenv("DJANGO_SUPERUSER_PASSWORD")
		if not (username and password):
			self.stdout.write(self.style.WARNING("DJANGO_SUPERUSER_* not set, skipping superuser creation."))
			return
		User = get_user_model()
		if User.objects.filter(username=username).exists():
			self.stdout.write(self.style.SUCCESS(f"Superuser '{username}' already exists."))
			return
		User.objects.create_superuser(username=username, email=email or "", password=password)
		self.stdout.write(self.style.SUCCESS(f"Superuser '{username}' created."))

	def _load_fixtures(self):
		base_dir = Path(__file__).resolve().parents[3]
		fixtures_dir = base_dir / "bot" / "fixtures"
		if not fixtures_dir.exists():
			self.stdout.write(self.style.WARNING(f"No fixtures dir: {fixtures_dir}"))
			return

		candidates = [
			"muscle_groups_fixture.json",
			"exercises_fixture.json",
		]
		paths = [fixtures_dir / name for name in candidates if (fixtures_dir / name).exists()]
		if not paths:
			self.stdout.write(self.style.WARNING(f"No known fixtures found in {fixtures_dir}"))
			return

		for p in paths:
			try:
				self.stdout.write(f"Loading fixture: {p}")
				call_command("loaddata", str(p), verbosity=1)
				self.stdout.write(self.style.SUCCESS(f"Loaded: {p.name}"))
			except Exception as e:
				self.stdout.write(self.style.WARNING(f"Skipped {p.name}: {e}"))
