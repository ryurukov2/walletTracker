import asyncio
import time
from django_eventstream import send_event
import os
from django.conf import settings
import json
from .async_api_calls import initial_etherscan_api_request_tasks, query_historic_and_current_prices
from .database_connections import save_wallet_info_to_db
from .data_processing import calculate_balances_and_txns, calculate_purchase_exchange_rate, calculate_total_token_p_l, combine_records, filter_out_transaction_type, match_historic_prices, take_first_n_from_dict

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

    # needed during dev as reading from file is quicker than the render and event is sent before render
    time.sleep(1)

    send_event('test', 'message', data={
               'balances': balances, 'transactions': filter_out_transaction_type(take_first_n_from_dict(transactions, 20), "Approve")})

    # check_current_token_prices(balances)
    # print(calculate_purchase_exchange_rate(transactions))
    transactions_details, timestamps_of_eth_trades = calculate_purchase_exchange_rate(
        transactions)
    send_event('test', 'message', data={
               'transactions_details': transactions_details})
    # print(timestamps_of_eth_trades)

    balances_prices_info, normalized_historic_prices = asyncio.run(query_historic_and_current_prices(
        timestamps_of_eth_trades, balances, tokens_list))

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
                           normalized_historic_prices, calculated_historic_prices, historic_balances_p_l, tokens_and_wallet_p_l_info, tokens_list)