# Generated by Django 4.2.1 on 2024-05-23 16:57

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('wallet', '0028_remove_wallet_wallet_unrealized_p_l'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='wallettokenbalance',
            name='token_unrealized_p_l',
        ),
    ]
