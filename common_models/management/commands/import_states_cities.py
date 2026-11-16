import csv
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from common_models.models import City, State

DATA_DIR = Path(__file__).resolve().parents[2]


class Command(BaseCommand):
    help = "Import Indian states/UTs and major cities from CSV files"

    def add_arguments(self, parser):
        parser.add_argument("--states", default=str(DATA_DIR / "indian_states.csv"))
        parser.add_argument("--cities", default=str(DATA_DIR / "indian_cities.csv"))
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Delete all existing State and City records before importing",
        )

    def handle(self, *args, **options):
        states_file = Path(options["states"])
        cities_file = Path(options["cities"])

        for path in (states_file, cities_file):
            if not path.exists():
                raise CommandError(f"File not found: {path}")

        with transaction.atomic():
            if options["clear"]:
                self._clear_existing()
            state_map = self._import_states(states_file)
            self._import_cities(cities_file, state_map)

        self.stdout.write(self.style.SUCCESS("Import completed successfully."))

    def _read_rows(self, path, columns):
        with open(path, newline="", encoding="utf-8-sig") as handle:
            reader = csv.DictReader(handle)
            missing = set(columns) - set(reader.fieldnames or [])
            if missing:
                raise CommandError(f"{path.name} is missing columns: {', '.join(sorted(missing))}")
            yield from reader

    def _clear_existing(self):
        city_count, _ = City.objects.all().delete()
        state_count, _ = State.objects.all().delete()
        self.stdout.write(
            self.style.WARNING(f"Cleared {state_count} states and {city_count} cities.")
        )

    def _import_states(self, path):
        state_map = {}
        created_count = 0
        skipped_count = 0

        self.stdout.write("Importing states and union territories...")
        for row in self._read_rows(path, ("id", "name")):
            try:
                csv_id = int(row["id"])
            except (TypeError, ValueError):
                raise CommandError(f"Invalid state row: {row}")
            name = (row["name"] or "").strip()
            if not name:
                raise CommandError(f"Invalid state row: {row}")

            state = State.objects.filter(name=name).first()
            if state is None:
                state = State.objects.create(name=name)
                created_count += 1
            else:
                skipped_count += 1
            state_map[csv_id] = state

        self.stdout.write(f"  States - created: {created_count}, already existed: {skipped_count}")
        return state_map

    def _import_cities(self, path, state_map):
        existing = set(City.objects.values_list("state_id", "name"))
        cities_to_create = []
        skipped_count = 0

        self.stdout.write("Importing cities...")
        for row in self._read_rows(path, ("state_id", "city_name")):
            try:
                csv_state_id = int(row["state_id"])
            except (TypeError, ValueError):
                raise CommandError(f"Invalid city row: {row}")
            city_name = (row["city_name"] or "").strip()

            state = state_map.get(csv_state_id)
            if state is None or not city_name:
                self.stdout.write(
                    self.style.WARNING(f"  Skipping '{city_name}': invalid state_id {csv_state_id}.")
                )
                continue

            key = (state.pk, city_name)
            if key in existing:
                skipped_count += 1
                continue

            existing.add(key)
            cities_to_create.append(City(state=state, name=city_name, available=False))

        City.objects.bulk_create(cities_to_create, batch_size=500)
        self.stdout.write(
            f"  Cities - created: {len(cities_to_create)}, already existed: {skipped_count}"
        )
