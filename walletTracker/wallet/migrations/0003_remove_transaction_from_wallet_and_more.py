# Generated by Django 4.2.1 on 2023-12-02 20:47

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('wallet', '0002_wallet_is_being_calculated_alter_wallet_address'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='transaction',
            name='from_wallet',
        ),
        migrations.RemoveField(
            model_name='transaction',
            name='function_name',
        ),
        migrations.RemoveField(
            model_name='transaction',
            name='gas_price',
        ),
        migrations.RemoveField(
            model_name='transaction',
            name='gas_used',
        ),
        migrations.RemoveField(
            model_name='transaction',
            name='to_wallet',
        ),
        migrations.RemoveField(
            model_name='transaction',
            name='token',
        ),
        migrations.RemoveField(
            model_name='transaction',
            name='value',
        ),
        migrations.AddField(
            model_name='transaction',
            name='is_error',
            field=models.BooleanField(default=0),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='transaction',
            name='received_amount',
            field=models.IntegerField(null=True),
        ),
        migrations.AddField(
            model_name='transaction',
            name='received_token',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='received_token', to='wallet.token'),
        ),
        migrations.AddField(
            model_name='transaction',
            name='related_wallet',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.CASCADE, related_name='related_wallet', to='wallet.wallet'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='transaction',
            name='sent_amount',
            field=models.IntegerField(null=True),
        ),
        migrations.AddField(
            model_name='transaction',
            name='sent_token',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='sent_token', to='wallet.token'),
        ),
        migrations.AddField(
            model_name='transaction',
            name='transaction_fee',
            field=models.IntegerField(null=True),
        ),
        migrations.AddField(
            model_name='wallettokenbalance',
            name='average_purchase_price',
            field=models.CharField(default=0, max_length=255),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='wallettokenbalance',
            name='net_purchase_price',
            field=models.CharField(default=0, max_length=255),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='token',
            name='last_checked_price_usd',
            field=models.DecimalField(decimal_places=2, max_digits=19, null=True),
        ),
        migrations.AlterField(
            model_name='wallettokenbalance',
            name='balance',
            field=models.IntegerField(null=True),
        ),
    ]
