# Generated by Django 4.2.1 on 2024-01-28 05:03

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('wallet', '0016_alter_tradetransactiondetails_transaction'),
    ]

    operations = [
        migrations.AlterField(
            model_name='tradetransactiondetails',
            name='exchanged_token',
            field=models.ForeignKey(on_delete=django.db.models.deletion.DO_NOTHING, to='wallet.token'),
        ),
    ]
