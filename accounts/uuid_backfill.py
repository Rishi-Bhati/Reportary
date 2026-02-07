from uuid6 import uuid7

def backfill_user_uuids(apps, schema_editor):
    User = apps.get_model("accounts", "User")
    for user in User.objects.filter(uuid__isnull=True):
        user.uuid = uuid7()
        user.save(update_fields=["uuid"])