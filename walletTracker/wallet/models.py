from decimal import Decimal
from django.db import models


class Wallet(models.Model):
    address = models.CharField(
        max_length=255, null=False, blank=False, unique=True)
    amount_spent_for_purchases_usd = models.DecimalField(
        max_digits=19, decimal_places=2, null=True, blank=True)
    amount_received_from_selling = models.DecimalField(
        max_digits=19, decimal_places=2, null=True, blank=True)
    last_calculated_balance_usd = models.DecimalField(
        max_digits=19, decimal_places=2, null=True, blank=True)
    last_calculated_balance_timestamp = models.DateTimeField(
        null=True, blank=True, auto_now=True)
    wallet_realized_p_l = models.DecimalField(
        max_digits=19, decimal_places=2, null=True, blank=True)
    wallet_total_p_l = models.DecimalField(
        max_digits=19, decimal_places=2, null=True, blank=True)

    is_being_calculated = models.BooleanField(default=True, null=False)

    def fill_total_wallet_p_l_data(self):
        'Fills out the p/l wallet fields based on the token data available in the database'
        wallet_data = WalletTokenBalance.objects.filter(wallet=self).aggregate(models.Sum("token_total_p_l"),
                                                                               models.Sum("token_realized_p_l"), models.Sum("total_usd_spent_for_token"), models.Sum("total_usd_received_from_selling"), models.Sum("last_calculated_balance_usd"))

        try:
            self.wallet_realized_p_l = wallet_data['token_realized_p_l__sum']
            self.wallet_total_p_l = wallet_data['token_total_p_l__sum']
            self.amount_spent_for_purchases_usd = wallet_data['total_usd_spent_for_token__sum']
            self.amount_received_from_selling = wallet_data['total_usd_received_from_selling__sum']
            self.last_calculated_balance_usd = wallet_data['last_calculated_balance_usd__sum']
        except Exception as e:
            print(f'Exception occurred in fill_total_wallet_p_l_data: {e}')


class Token(models.Model):
    contract = models.CharField(max_length=255, null=False, unique=True)
    token_name = models.CharField(max_length=255, null=False)
    token_symbol = models.CharField(max_length=10, null=False)
    token_decimal = models.IntegerField(null=False)
    token_image_url = models.URLField(max_length=255, null=True, blank=True, default=None)
    last_checked_price_usd = models.CharField(max_length=255, null=True)
    last_checked_price_timestamp = models.DateTimeField(null=True, blank=True)

    @property
    def decimal_price(self):
        return Decimal(self.last_checked_price_usd)


class Transaction(models.Model):
    TYPE_OF_TRANSACTION_CHOICES = [
        ("TRADE", "Trade"),
        ("SEND", "Send"),
        ("RECEIVE", "Receive"),
        ("APPROVE", "Approve"),
    ]

    block = models.BigIntegerField(null=False)
    timestamp = models.BigIntegerField(null=False)
    hash = models.CharField(max_length=255, null=False, unique=True)
    is_error = models.BooleanField(null=False)
    related_wallet = models.ForeignKey(
        Wallet, to_field='address', related_name='related_wallet', on_delete=models.CASCADE, null=False)
    sent_token = models.ForeignKey(
        Token, related_name='sent_token', on_delete=models.DO_NOTHING, null=True)
    sent_amount = models.CharField(max_length=128, null=True)
    received_token = models.ForeignKey(
        Token, related_name='received_token', on_delete=models.DO_NOTHING, null=True)
    received_amount = models.CharField(max_length=128, null=True)
    transaction_fee = models.CharField(max_length=32, null=True)
    type_of_transaction = models.CharField(
        max_length=64, null=True, default='Trade', choices=TYPE_OF_TRANSACTION_CHOICES)


class TradeTransactionDetails(models.Model):
    transaction = models.OneToOneField(
        Transaction, to_field='hash', on_delete=models.CASCADE, related_name='trade_details')
    exchanged_token = models.ForeignKey(Token, on_delete=models.DO_NOTHING)
    exchanged_token_amount = models.CharField(max_length=128)
    is_receiver = models.BooleanField(null=True)
    denominated_in = models.CharField(max_length=64, null=True)
    price_in_denominated_token = models.CharField(max_length=128, null=True)
    price_in_usd = models.CharField(max_length=128, null=True)
    value_of_trade_in_denominated_token = models.CharField(
        max_length=128, null=True)
    value_of_trade_in_usd = models.CharField(max_length=128, null=True)


class WalletTokenBalance(models.Model):
    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, null=False)
    token = models.ForeignKey(Token, on_delete=models.CASCADE, null=False)
    balance = models.CharField(max_length=128, null=False, default='0')
    last_updated = models.DateTimeField(auto_now=True)
    average_purchase_price = models.CharField(max_length=128, null=True, blank=True)
    net_purchase_price = models.CharField(max_length=128, null=True, blank=True)
    purchased_token_amount = models.CharField(max_length=128, null=True, blank=True)
    sold_token_amount = models.CharField(max_length=128, null=True, blank=True)
    total_usd_spent_for_token = models.DecimalField(
        max_digits=64, decimal_places=2, null=True, blank=True)
    total_usd_received_from_selling = models.DecimalField(
        max_digits=64, decimal_places=2, null=True, blank=True)
    token_realized_p_l = models.DecimalField(max_digits=64, decimal_places=2, null=True, blank=True)
    token_total_p_l = models.DecimalField(max_digits=64, decimal_places=2, null=True, blank=True)
    last_calculated_balance_usd = models.DecimalField(
        max_digits=64, decimal_places=2, default=0)

    class Meta:
        unique_together = ('wallet', 'token')


class HistoricalETHPrice(models.Model):
    timestamp = models.IntegerField(null=False, unique=True)
    price = models.DecimalField(null=False, decimal_places=2, max_digits=32)

class SuspiciousTokens(models.Model):
    contract = models.CharField(max_length=255, null=False, unique=True)
