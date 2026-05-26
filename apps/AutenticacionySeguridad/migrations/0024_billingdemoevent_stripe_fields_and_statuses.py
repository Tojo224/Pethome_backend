from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("AutenticacionySeguridad", "0023_fix_backupconfig_encoded_columns"),
    ]

    operations = [
        migrations.AddField(
            model_name="billingdemoevent",
            name="stripe_session_id",
            field=models.CharField(blank=True, max_length=120, null=True),
        ),
        migrations.AddField(
            model_name="billingdemoevent",
            name="stripe_payment_intent_id",
            field=models.CharField(blank=True, max_length=120, null=True),
        ),
        migrations.AddField(
            model_name="billingdemoevent",
            name="stripe_event_id",
            field=models.CharField(blank=True, max_length=120, null=True),
        ),
        migrations.AddField(
            model_name="billingdemoevent",
            name="amount",
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True),
        ),
        migrations.AddField(
            model_name="billingdemoevent",
            name="currency",
            field=models.CharField(blank=True, max_length=10, null=True),
        ),
    ]

