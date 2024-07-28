
from datetime import datetime
from decimal import Decimal
from django import db
import numpy as np
from ..models import HistoricalETHPrice, SuspiciousTokens, TradeTransactionDetails, Transaction, Wallet, WalletTokenBalance, Token





def query_all_wallet_info_from_database(wallet):
    'Queries all information about the wallet from the database'
    wallet_balances = list(WalletTokenBalance.objects.filter(wallet=wallet).select_related('token').order_by("-last_calculated_balance_usd"))
    # wallet_transactions = list(Transaction.objects.filter(related_wallet=wallet).order_by('-timestamp').values())
    wallet_transactions = list(Transaction.objects.filter(related_wallet=wallet, type_of_transaction__in=['Trade', 'Send', 'Receive']).select_related('sent_token', 'received_token').order_by('-timestamp'))[:20]
    wallet_trade_details = list(TradeTransactionDetails.objects.filter(transaction__related_wallet=wallet))
    
    return {'wallet_balances': wallet_balances, 
            'wallet_transactions': wallet_transactions,
            'wallet_trade_details':wallet_trade_details,
            'wallet_obj': wallet}



def wallet_data_available_in_db(address_queried):
    'Checks if the wallet has already been saved to the database'
    db_wallet, created = Wallet.objects.get_or_create(address=address_queried)

    if not created and not db_wallet.is_being_calculated:
        # wallet existed already, will add further checks for timestamp after
        # return db_wallet
        wallet_data = query_all_wallet_info_from_database(db_wallet)

        return wallet_data
        # return False
    else:
        db_wallet.is_being_calculated = True
        db_wallet.save()
        return False
    

def get_all_suspicious_tokens():
    return SuspiciousTokens.objects.all().values_list('contract', flat=True)

def get_latest_transaction(wallet):
    return Transaction.objects.filter(related_wallet=wallet).order_by("block").last()

def get_wallet_balances(wallet):
    return WalletTokenBalance.objects.filter(wallet=wallet)

def save_wallet_info_to_db(address_queried: str, db_data: dict):
    'Saves the information gathered from the API calls to the database'
    
    # WalletTokenBalance.objects.all().delete()
    # TradeTransactionDetails.objects.all().delete()
    # Transaction.objects.all().delete()
    # Token.objects.all().delete()

    wallet = Wallet.objects.get(address=address_queried)
    balances = db_data.get('balances') or {}

    
    def save_tokens_and_wallet_token_balance():
        tokens_list = db_data.get('tokens_list')
        balances_prices_info = db_data.get('balances_prices_info') or {}
        historic_balances_p_l = db_data.get('historic_balances_p_l') or {}
        tokens_and_wallet_p_l_info = db_data.get('tokens_and_wallet_p_l_info') or {}


        for contract, token_data in tokens_list.items():
            current_token_balance, current_token_price = 0, 0
            #create Token, WalletTokenBalance objects
            token, created = Token.objects.update_or_create(
                contract=contract, defaults=token_data)
            # try:
            if contract in balances_prices_info:
                current_token_price = balances_prices_info[contract].get('price_usd') or 0

            token.last_checked_price_usd = current_token_price
            token.last_checked_price_timestamp = datetime.now()
            token.save()

            wallet_token_defaults = {}

            if contract in balances:
                current_token_balance = balances[contract].get('balance') or 0
                wallet_token_defaults.setdefault('balance', current_token_balance)
                wallet_token_defaults.setdefault('last_calculated_balance_usd', Decimal(current_token_balance) * Decimal(current_token_price))
            if contract in historic_balances_p_l:
                _data = historic_balances_p_l.get(contract)
                wallet_token_defaults.setdefault('average_purchase_price', _data.get('average_purchase_price') or 0)
                wallet_token_defaults.setdefault('net_purchase_price', _data.get('net_purchase_price') or 0)
                wallet_token_defaults.setdefault('purchased_token_amount', _data.get('purchased_token_amount') or 0)
                wallet_token_defaults.setdefault('sold_token_amount', _data.get('sold_token_amount') or 0)
                wallet_token_defaults.setdefault('total_usd_spent_for_token',_data.get('total_usd_spent_for_token') or 0)
                wallet_token_defaults.setdefault('total_usd_received_from_selling',_data.get('total_usd_received_from_selling') or 0)
                wallet_token_defaults.setdefault('token_realized_p_l',_data.get('token_realized_p_l') or 0)



            if contract in tokens_and_wallet_p_l_info:
                token_total_p_l = tokens_and_wallet_p_l_info.get(contract) or 0
                wallet_token_defaults.setdefault('token_total_p_l', token_total_p_l)


            wallet_token_balance, _created = WalletTokenBalance.objects.update_or_create(
                wallet=wallet, token=token, defaults=wallet_token_defaults)

    def save_transactions_and_trade_details():


        transactions = db_data.get('transactions') or {}
        transactions_details = db_data.get('transactions_details') or {}
        calculated_historic_prices = db_data.get('calculated_historic_prices') or {}
        for hash, tx_details in transactions.items():
                #create Transaction, TradeTransactionDetails db objects
                timestamp = tx_details.get('timeStamp')
                tx_block = tx_details.get('blockNumber')
                tx_fee = tx_details.get('tx_fee')
                tx_is_error = tx_details.get('isError')
                transaction_type = tx_details.get('transaction_type')
                # received_keys= tx_details.get('received', {}).keys()
                # sent_keys= tx_details.get('sent', {}).keys()
                sent_contract = next(iter(tx_details.get('sent', {}).keys()), None)
                received_contract = next(
                    iter(tx_details.get('received', {}).keys()), None)
                # print(f'{hash} - sent: {sent_contract}--------- received: {received_contract}')
                sent_amount, received_amount = None, None
                if sent_contract is not None:
                    sent_amount = tx_details['sent'][sent_contract]['final_amount']
                if received_contract is not None:
                    received_amount = tx_details['received'][received_contract]['final_amount']
                # print(tx_details)

                try:
                    _db_txn_data = {'block': tx_block, 'timestamp': timestamp, 'hash': hash, 'is_error': tx_is_error,
                                    'related_wallet': wallet,
                                    'sent_token_id': token_ids.get(sent_contract), 'sent_amount': sent_amount,
                                    'received_token_id': token_ids.get(received_contract),
                                    'received_amount': received_amount, 'transaction_fee': tx_fee, 'type_of_transaction': transaction_type}
                    transaction, created = Transaction.objects.update_or_create(
                        hash=hash, defaults=_db_txn_data)
                    if hash in transactions_details.keys():

                        additional_details = transactions_details[hash]
                        price_in_usd = np.format_float_positional(
                            (calculated_historic_prices.get(hash) or {}).get('price_in_usd') or 0)
                        price_in_denominated_token = np.format_float_positional(
                            additional_details['price_in_denominated_token'])
                        trade_transaction_defaults = {'exchanged_token_id':token_ids.get(
                                additional_details['exchanged_token_contract']),
                            'exchanged_token_amount':additional_details['exchanged_token_amount'],
                            'is_receiver':additional_details['is_receiver'],
                            'denominated_in':additional_details['denominated_in'],
                            'price_in_denominated_token':price_in_denominated_token,
                            'price_in_usd':price_in_usd,
                            'value_of_trade_in_denominated_token':additional_details['value_of_trade_in_eth']}
                        TradeTransactionDetails.objects.update_or_create(
                            transaction=transaction, defaults=trade_transaction_defaults
                        )
                except Exception as e:
                    print(f'Exception in save_transactions_and_trade_details - {e}')
    
    def save_historical_eth_prices():
        normalized_historic_prices = db_data.get('normalized_historic_prices') or {}
        for at_timestamp, eth_price in normalized_historic_prices.items():
                HistoricalETHPrice.objects.update_or_create(timestamp=at_timestamp, 
                                                            defaults={'timestamp':at_timestamp, 
                                                                    'price':eth_price})

    def save_suspicious_tokens():
        suspicious_tokens = db_data.get('suspicious_tokens') or {}
        for contract in suspicious_tokens:
            SuspiciousTokens.objects.update_or_create(contract=contract)

    if 'tokens_list' in db_data:
        save_tokens_and_wallet_token_balance()
    tokens = Token.objects.all().values_list('contract', 'id')
    token_ids = {contract: id for contract, id in tokens}
    if 'transactions' in db_data:
        save_transactions_and_trade_details()

    wallet.fill_total_wallet_p_l_data()
    wallet.is_being_calculated = False
    wallet.save()

    if 'normalized_historic_prices' in db_data:
        save_historical_eth_prices()

    if 'suspicious_tokens' in db_data:
        save_suspicious_tokens()
    
    # # save suspicious tokens to database
