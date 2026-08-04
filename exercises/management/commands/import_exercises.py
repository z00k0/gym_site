import json
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from jsonschema import Draft202012Validator

from exercises.models import Exercise


class Command(BaseCommand):
    help = "Import or update the pinned exercises dataset"

    def add_arguments(self, parser):
        parser.add_argument("--path", type=Path, default=settings.DATASET_ROOT)

    def handle(self, *args, **options):
        root = options["path"]
        source = root / "data" / "exercises.json"
        if not source.exists():
            raise CommandError(f"Dataset not found: {source}")
        with source.open(encoding="utf-8") as stream:
            rows = json.load(stream)
        schema_path = root / "data" / "exercises.schema.json"
        if not schema_path.exists():
            raise CommandError(f"Dataset schema not found: {schema_path}")
        with schema_path.open(encoding="utf-8") as stream:
            schema = json.load(stream)
        errors = list(Draft202012Validator(schema).iter_errors(rows))
        if errors:
            raise CommandError(f"Dataset schema validation failed: {errors[0].message}")
        source_ids = {row["id"] for row in rows}
        existing_ids = set(
            Exercise.objects.filter(source_id__in=source_ids).values_list("source_id", flat=True)
        )
        objects = []
        for row in rows:
            instructions = row.get("instructions") or {}
            defaults = {
                "name": row["name"],
                "instructions_ru": instructions.get("ru", ""),
                "body_part": row.get("body_part") or row.get("category", ""),
                "equipment": row.get("equipment", ""),
                "target": row.get("target", ""),
                "muscle_group": row.get("muscle_group", ""),
                "secondary_muscles": row.get("secondary_muscles") or [],
                "load_kind": Exercise.LoadKind.BODYWEIGHT
                if row.get("equipment") == "body weight"
                else Exercise.LoadKind.EXTERNAL,
                "image_path": row.get("image", ""),
                "gif_path": row.get("gif_url", ""),
                "attribution": row.get("attribution", ""),
                "is_active": True,
            }
            objects.append(Exercise(source_id=row["id"], **defaults))
        update_fields = [
            "name",
            "instructions_ru",
            "body_part",
            "equipment",
            "target",
            "muscle_group",
            "secondary_muscles",
            "load_kind",
            "image_path",
            "gif_path",
            "attribution",
            "is_active",
        ]
        with transaction.atomic():
            Exercise.objects.bulk_create(
                objects,
                batch_size=250,
                update_conflicts=True,
                update_fields=update_fields,
                unique_fields=["source_id"],
            )
        created = len(source_ids - existing_ids)
        updated = len(source_ids & existing_ids)
        self.stdout.write(self.style.SUCCESS(f"Imported {created}, updated {updated}"))
