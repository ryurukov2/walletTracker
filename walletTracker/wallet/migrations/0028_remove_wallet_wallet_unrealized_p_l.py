# Generated by Django 4.2.1 on 2024-05-22 19:08

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('wallet', '0027_alter_transaction_type_of_transaction'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='wallet',
            name='wallet_unrealized_p_l',
        ),
    ]