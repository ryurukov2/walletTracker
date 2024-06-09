import asyncio
import time
from django_eventstream import send_event
import os
from django.conf import settings
import json

from ..models import Transaction, Wallet
from .async_api_calls import initial_etherscan_api_request_tasks, query_historic_and_current_prices
from .database_connections import get_latest_transaction, get_wallet_balances, save_wallet_info_to_db
from .data_processing import calculate_balances_and_txns, calculate_purchase_exchange_rate, calculate_total_token_p_l, combine_records, filter_out_transaction_type, filter_suspicious_tokens, match_historic_prices, reverse_dict, separate_balances_data_for_p_l, separate_suspicious_token_entries, take_last_n_from_dict


def query_balances_and_txns(address, start_block=None, balances = None, tokens_list = None):
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
    # write to db both balances and historic
    save_wallet_info_to_db(address_queried, balances, transactions, transactions_details, balances_prices_info,
                           normalized_historic_prices, calculated_historic_prices, historic_balances_p_l, tokens_and_wallet_p_l_info, tokens_list, suspicious_tokens)


def data_refresh_thread_worker(wallet: Wallet):
    # refresh interval in seconds
    REFRESH_INTERVAL = 300
    last_balance_check_at = wallet.last_calculated_balance_timestamp.timestamp()
    current_timestamp = time.time()

    if current_timestamp - last_balance_check_at >= REFRESH_INTERVAL:
        # query current token prices
        print('need refresh')

    last_transaction = get_latest_transaction(wallet)

    # jj = json.loads(serializers.serialize('json', [ wallet, ]))[0]

    old_balances_from_db = separate_balances_data_for_p_l(get_wallet_balances(wallet))
    

    # need to have the balances and transactions so far and add them to the query balances and txns function args+

# 
    balances, transactions, tokens_list = query_balances_and_txns(
        wallet.address, last_transaction.block + 1, old_balances_from_db['old_balances'], old_balances_from_db['old_tokens_list'])
    transactions_details, timestamps_of_eth_trades = calculate_purchase_exchange_rate(
        transactions)
# 

    balances_prices_info, normalized_historic_prices = asyncio.run(query_historic_and_current_prices(
    timestamps_of_eth_trades, balances, tokens_list))
    suspicious_tokens = []
    suspicious_tokens = filter_suspicious_tokens(
        balances, balances_prices_info)
    
    # print(balances_prices_info)
    
#   
    # calculated_historic_prices, historic_balances_p_l = match_historic_prices(
    #     normalized_historic_prices, transactions_details)
# 

    # 1. get the current balances = {contract: {balances}} from the database
    # 2. combine with the balances variable above
    # 3. do the same with tokens_list
    # 4. call the 'query current and historic prices' function with the new balances and tokens_list dict
    # 5. match the new transactions to the ETH prices returned
    # 6. query the rest of the WalletTokenBalance fields
    # 7. call the calculate p/l function to update the values
