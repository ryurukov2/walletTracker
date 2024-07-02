import asyncio
import time
from django_eventstream import send_event
import os
from django.conf import settings
import json

from ..models import Transaction, Wallet
from .async_api_calls import initial_etherscan_api_request_tasks, query_current_prices, query_historic_and_current_prices
from .database_connections import get_latest_transaction, get_wallet_balances, save_wallet_info_to_db
from .data_processing import calculate_balances_and_txns, calculate_purchase_exchange_rate, calculate_total_token_p_l, combine_records, filter_out_transaction_type, filter_suspicious_tokens, match_historic_prices, reverse_dict, separate_balances_data_for_p_l, separate_suspicious_token_entries, take_last_n_from_dict


def query_balances_and_txns(address, start_block=None, balances=None, tokens_list=None):
    datasets_list = asyncio.run(
        initial_etherscan_api_request_tasks(address, start_block))
    combined_data = combine_records(*datasets_list)

    return calculate_balances_and_txns(address, combined_data, balances=balances, tokens_list=tokens_list)


def wallet_calaulations_thread_worker(address_queried):
    'Thread worker function to perform calculations for a wallet'
    # datasets_list = asyncio.run(initial_etherscan_api_request_tasks(address_queried))
    # combined_data = combine_records(*datasets_list)

    tokentx = json.loads(
        open(os.path.join(settings.BASE_DIR, 'tokentx.txt')).read())
    txlist = json.loads(
        open(os.path.join(settings.BASE_DIR, 'txlist.txt')).read())
    txlistinternal = json.loads(
        open(os.path.join(settings.BASE_DIR, 'txlistinternal.txt')).read())
    combined_data = combine_records(tokentx, txlist, txlistinternal)

    balances, transactions, tokens_list = calculate_balances_and_txns(
        address_queried, combined_data)

    # balances, transactions, tokens_list = query_balances_and_txns(address_queried)

    # needed during dev as reading from file is quicker than the render and event is sent before render
    time.sleep(1)

    send_event('test', 'message', data={
               'balances': balances, 'transactions': reverse_dict(filter_out_transaction_type(take_last_n_from_dict(transactions, 20), "Approve"))})

    # check_current_token_prices(balances)
    # print(calculate_purchase_exchange_rate(transactions))
    transactions_details, timestamps_of_eth_trades = calculate_purchase_exchange_rate(
        transactions)
    send_event('test', 'message', data={
               'transactions_details': transactions_details})
    # print(timestamps_of_eth_trades)

    balances_prices_info, normalized_historic_prices = asyncio.run(query_historic_and_current_prices(
        timestamps_of_eth_trades, balances, tokens_list))
    suspicious_tokens = []
    suspicious_tokens = filter_suspicious_tokens(
        balances, balances_prices_info)
    suspicious_data = separate_suspicious_token_entries(
        balances, transactions, tokens_list, suspicious_tokens)
    suspicious_transactions = [
        h for h in suspicious_data['suspicious_transactions'].keys()]
    suspicious_balances = [
        c for c in suspicious_data['suspicious_balances'].keys()]
    send_event('test', 'message', data={
        'suspicious_data': {'suspicious_transactions': suspicious_transactions,
                            'suspicious_balances': suspicious_balances}
    })
    # match the closest historic price time to each of the txns
    calculated_historic_prices, historic_balances_p_l = match_historic_prices(
        normalized_historic_prices, transactions_details)
    # send message
    send_event('test', 'message', data={
               'finalized_usd_prices': calculated_historic_prices})
    send_event('test', 'message', data={
               'historic_balances_p_l': historic_balances_p_l})
    # send_event('test', 'message', data={'balances_prices_info': balances_prices_info})
    tokens_and_wallet_p_l_info = calculate_total_token_p_l(
        balances_prices_info, historic_balances_p_l)
    send_event('test', 'message', data={
               'tokens_and_wallet_p_l_info': tokens_and_wallet_p_l_info})
    db_data = {}
    db_data.update({'balances': balances,
                    'transactions': transactions,
                    'calculated_historic_prices': calculated_historic_prices,
                    'historic_balances_p_l': historic_balances_p_l,
                    'transactions_details': transactions_details,
                    'tokens_list': tokens_list,
                    'suspicious_tokens': suspicious_tokens,
                    'balances_prices_info': balances_prices_info,
                    'tokens_and_wallet_p_l_info': tokens_and_wallet_p_l_info,
                    'normalized_historic_prices': normalized_historic_prices})
    # write to db both balances and historic
    save_wallet_info_to_db(address_queried, db_data)


def data_refresh_thread_worker(wallet: Wallet):
    # refresh interval in seconds
    REFRESH_INTERVAL = 10
    last_balance_check_at = wallet.last_calculated_balance_timestamp.timestamp()
    current_timestamp = time.time()

    if current_timestamp - last_balance_check_at >= REFRESH_INTERVAL:
        last_transaction = get_latest_transaction(wallet)

        old_balances_from_db = separate_balances_data_for_p_l(
            get_wallet_balances(wallet))

        db_data = {}

    #
        balances, transactions, tokens_list = query_balances_and_txns(
            wallet.address, last_transaction.block + 1,
            old_balances_from_db['old_balances'], old_balances_from_db['old_tokens_list'])
        db_data.update({'balances': balances,
                        'tokens_list': tokens_list})
        
        if len(transactions) != 0:
            transactions_details, timestamps_of_eth_trades = calculate_purchase_exchange_rate(
                transactions)

            balances_prices_info, normalized_historic_prices = asyncio.run(query_historic_and_current_prices(
                timestamps_of_eth_trades, balances, tokens_list))
            suspicious_tokens = filter_suspicious_tokens(
                balances, balances_prices_info)

        #
            calculated_historic_prices, historic_balances_p_l = match_historic_prices(
                normalized_historic_prices, transactions_details, old_balances_from_db['old_tokens_p_l'])
        #

            tokens_and_wallet_p_l_info = calculate_total_token_p_l(
                balances_prices_info, historic_balances_p_l)

            db_data.update({'transactions': transactions,
                            'calculated_historic_prices': calculated_historic_prices,
                            'historic_balances_p_l': historic_balances_p_l,
                            'transactions_details': transactions_details,
                            'suspicious_tokens': suspicious_tokens,
                            'balances_prices_info': balances_prices_info,
                            'tokens_and_wallet_p_l_info': tokens_and_wallet_p_l_info,
                            'normalized_historic_prices': normalized_historic_prices})
        else:
            updated_current_prices = asyncio.run(query_current_prices(balances))
            calculate_total_balance_values(balances, updated_current_prices['result'])
            updated_p_l = calculate_total_token_p_l(updated_current_prices['result'], old_balances_from_db['old_tokens_p_l'])
            db_data.update({'tokens_and_wallet_p_l_info': updated_p_l,
                            'historic_balances_p_l': old_balances_from_db['old_tokens_p_l'],
                            'balances_prices_info': updated_current_prices['result']})
        address_queried = wallet.address
        send_event('test', 'message', data={
            'update_available': True,
        })
        save_wallet_info_to_db(address_queried, db_data)


def calculate_total_balance_values(balances, prices):
    total_usd_value = 0
    for contract, data in balances.items():
        if prices.get(contract):

            usd_price = prices[contract].get('price_usd') or 0
            balance = data['balance'] or 0
            total_value = float(usd_price)*float(balance)
            total_usd_value += total_value
            prices[contract].update({'usd_value': total_value})
    prices.update({'total_usd_value': total_usd_value})