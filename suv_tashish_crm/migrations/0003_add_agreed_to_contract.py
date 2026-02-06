from django.db import migrations


class Migration(migrations.Migration):

    # This migration was converted to a no-op because a later migration
    # (0007_client_agreed_to_contract.py) already adds the
    # `agreed_to_contract` field. Keeping a no-op migration here ensures
    # migration graph consistency for older working copies.

    dependencies = [
        ('suv_tashish_crm', '0006_userprofile'),
    ]

    operations = []
