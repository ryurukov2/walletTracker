# Generated by Django 4.2.1 on 2024-01-25 11:39

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('wallet', '0009_alter_transaction_received_amount_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='transaction',
            name='block',
            field=models.BigIntegerField(),
        ),
        migrations.AlterField(
            model_name='transaction',
            name='timestamp',
            field=models.BigIntegerField(),
        ),
    ]
