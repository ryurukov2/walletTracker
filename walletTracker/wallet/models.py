from django.db import models

class Wallet(models.Model):
    address = models.CharField(max_length=255, null=False, blank=False, unique=True)
    amount_spent_for_purchases_usd = models.DecimalField(max_digits=19, decimal_places=2, null=True, blank=True)
    last_calculated_balance_usd = models.DecimalField(max_digits=19, decimal_places=2, null=True, blank=True)
    last_calculated_balance_timestamp = models.DateTimeField(null=True,blank=True)
    is_being_calculated = models.BooleanField(default=True, null=False)

class Token(models.Model):
    contract = models.CharField(max_length=255, null=False)
    token_name = models.CharField(max_length=255, null=False)
    token_symbol = models.CharField(max_length=10, null=False)
    token_decimal = models.IntegerField(null=False)
    last_checked_price_usd = models.DecimalField(max_digits=19, decimal_places=2, null=True)
    last_checked_price_timestamp = models.DateTimeField(null=True,blank=True)

class Transaction(models.Model):
    block = models.IntegerField(null=False)
    timestamp = models.DateTimeField(null=False)
    hash = models.CharField(max_length=255, null=False)
    is_error = models.BooleanField(null=False)
    related_wallet = models.ForeignKey(Wallet, related_name='related_wallet', on_delete=models.CASCADE, null=False)
    sent_token = models.ForeignKey(Token, related_name='sent_token', on_delete=models.DO_NOTHING, null=True)
    sent_amount = models.IntegerField(null=True)
    received_token = models.ForeignKey(Token, related_name='received_token', on_delete=models.DO_NOTHING, null=True)
    received_amount = models.IntegerField(null=True)
    transaction_fee = models.IntegerField(null=True)
    # function_name = models.CharField(max_length=255)



class WalletTokenBalance(models.Model):
    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, null=False)
    token = models.ForeignKey(Token, on_delete=models.CASCADE, null=False)
    balance = models.IntegerField(null=True)
    last_updated = models.DateTimeField(auto_now=True)
    #  = models.DecimalField(max_digits=19, decimal_places=2, null=True, blank=True)
    average_purchase_price = models.CharField(max_length=255, null=False)
    net_purchase_price = models.CharField(max_length=255, null=False)

    @property
    def last_calculated_balance_usd(self):
        return (self.token.last_checked_price_usd * self.balance)


class HistoricalETHPrice(models.Model):
    timestamp = models.IntegerField(null=False)
    price = models.DecimalField(null=False, decimal_places=2, max_digits=32)