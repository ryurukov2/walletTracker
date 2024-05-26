# Generated by Django 4.2.1 on 2024-05-26 13:01

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('wallet', '0029_remove_wallettokenbalance_token_unrealized_p_l'),
    ]

    operations = [
        migrations.AlterField(
            model_name='wallettokenbalance',
            name='average_purchase_price',
            field=models.CharField(blank=True, max_length=128, null=True),
        ),
        migrations.AlterField(
            model_name='wallettokenbalance',
            name='net_purchase_price',
            field=models.CharField(blank=True, max_length=128, null=True),
        ),
        migrations.AlterField(
            model_name='wallettokenbalance',
            name='purchased_token_amount',
            field=models.CharField(blank=True, max_length=128, null=True),
        ),
        migrations.AlterField(
            model_name='wallettokenbalance',
            name='sold_token_amount',
            field=models.CharField(blank=True, max_length=128, null=True),
        ),
        migrations.AlterField(
            model_name='wallettokenbalance',
            name='token_realized_p_l',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=64, null=True),
        ),
        migrations.AlterField(
            model_name='wallettokenbalance',
            name='token_total_p_l',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=64, null=True),
        ),
        migrations.AlterField(
            model_name='wallettokenbalance',
            name='total_usd_received_from_selling',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=64, null=True),
        ),
        migrations.AlterField(
            model_name='wallettokenbalance',
            name='total_usd_spent_for_token',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=64, null=True),
        ),
    ]