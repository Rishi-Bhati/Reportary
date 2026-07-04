from django.db import migrations, models
from uuid6 import uuid7

def backfill_user_uuids(apps, schema_editor):
    User = apps.get_model("accounts", "User")
    for user in User.objects.all():
        user.uuid = uuid7()
        user.save(update_fields=["uuid"])


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0004_user_uuid"),
    ]

    operations = [
        # 1️⃣ Ensure field is nullable (safe state)
        migrations.AlterField(
            model_name="user",
            name="uuid",
            field=models.UUIDField(
                null=True,
                editable=False,
                db_index=True,
            ),
        ),

        # 2️⃣ ACTUALLY RUN THE BACKFILL
        migrations.RunPython(backfill_user_uuids),
    ]