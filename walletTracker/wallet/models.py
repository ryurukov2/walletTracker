from django.db import models

class Wallet(models.Model):
    address = models.CharField(max_length=255, null=False, blank=False)
    amount_spent_for_purchases_usd = models.DecimalField(max_digits=19, decimal_places=2, null=True, blank=True)
    last_calculated_balance_usd = models.DecimalField(max_digits=19, decimal_places=2, null=True, blank=True)
    last_calculated_balance_timestamp = models.DateTimeField(null=True,blank=True)

class Token(models.Model):
    contract = models.CharField(max_length=255, null=False)
    token_name = models.CharField(max_length=255, null=False)
    token_symbol = models.CharField(max_length=10, null=False)
    token_decimal = models.IntegerField(null=False)
    last_checked_price_usd = models.DecimalField(max_digits=19, decimal_places=10, null=True)
    last_checked_price_timestamp = models.DateTimeField(null=True,blank=True)

class Transaction(models.Model):
    block = models.IntegerField(null=False)
    timestamp = models.DateTimeField(null=False)
    hash = models.CharField(max_length=255, null=False)
    from_wallet = models.ForeignKey(Wallet, related_name='transactions_from', on_delete=models.CASCADE, null=False)
    to_wallet = models.ForeignKey(Wallet, related_name='transactions_to', on_delete=models.CASCADE, null=False)
    token = models.ForeignKey(Token, on_delete=models.CASCADE, null=True)
    value = models.DecimalField(max_digits=19, decimal_places=10, null=False)
    gas_price = models.DecimalField(max_digits=19, decimal_places=10)
    gas_used = models.DecimalField(max_digits=19, decimal_places=10)
    function_name = models.CharField(max_length=255)

class WalletTokenBalance(models.Model):
    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, null=False)
    token = models.ForeignKey(Token, on_delete=models.CASCADE, null=False)
    balance = models.DecimalField(max_digits=19, decimal_places=10, null=False)
    last_updated = models.DateTimeField(auto_now=True)