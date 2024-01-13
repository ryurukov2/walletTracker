import asyncio
from bisect import bisect_left
from collections import OrderedDict
import json
import math
import threading
import time
from django_eventstream import send_event
import aiohttp
from django.conf import settings
from django.shortcuts import render, redirect
from dotenv import load_dotenv
import os
from asgiref.sync import sync_to_async
from .models import Wallet, Token, Transaction, WalletTokenBalance
load_dotenv()

# Create your views here.


def index(request):
    return render(request, 'index.html')


def combine_records(token_tx, internal_tx, normal_tx):
    combined_data = {}

    def add_entry(entry):
        hash_value = entry['hash']
        hash_list = combined_data.setdefault(hash_value, {})
        hash_list[len(hash_list)] = entry
    for dataset in [normal_tx, token_tx, internal_tx]:
        for entry in dataset['result']:
            add_entry(entry)

    return combined_data


def calculate_balances_and_txns(address, combined_data):
    transactions, balances = {}, {}
    eth_decimal = 18
    for hash, transaction_entries in combined_data.items():
        # print(transaction_entries)
        tx_fee = 0
        tx_moves = {}

        for transaction_entry_data in transaction_entries.values():
            isReceiver = False
            amount_transfered = int(transaction_entry_data['value'])
            tx_moves['timeStamp'] = transaction_entry_data['timeStamp']

            if transaction_entry_data['to'].lower() == address.lower():
                isReceiver = True
            else:
                if tx_fee == 0 and transaction_entry_data['gasPrice'] != '' and transaction_entry_data['gasUsed'] != '':
                    # check that fee hasn'transaction_entry_data been set yet, and check that fee numbers exist in dataset
                    tx_fee = int(
                        transaction_entry_data['gasPrice'])*int(transaction_entry_data['gasUsed'])
            if 'isError' in transaction_entry_data.keys() and transaction_entry_data['isError'] == '1':
                tx_moves['isError'] = '1'
                continue
            tx_moves['isError'] = '0'

            if amount_transfered == 0:
                continue

            if transaction_entry_data['contractAddress'] == "":
                token_name = 'Ethereum'
                token_contract = 'eth'
                token_symbol = 'ETH'
                token_decimal = eth_decimal
            else:
                # eth doesn't have a contract address in the api response
                token_name = transaction_entry_data['tokenName']
                token_contract = transaction_entry_data['contractAddress']
                token_symbol = transaction_entry_data['tokenSymbol']
                token_decimal = int(transaction_entry_data['tokenDecimal'])

            action = 'received' if isReceiver else 'sent'
            _trade_info = {
                'token_symbol': token_symbol,
                'final_amount': amount_transfered/(10**token_decimal),
                'precise_amount': amount_transfered,
                'token_decimal': token_decimal,
                'token_name': token_name
            }
            if action not in tx_moves.keys() or token_contract not in tx_moves[action].values():

                tx_moves.setdefault(action, {}).update(
                    {token_contract: _trade_info})
            else:

                # issue here
                tx_moves[action][token_contract]['precise_amount'] = float(
                    tx_moves[action]['precise_amount']) + amount_transfered/(10**token_decimal)
                tx_moves[action][token_contract]['final_amount'] = float(
                    tx_moves[action]['final_amount']) + amount_transfered/(10**token_decimal)

            if token_contract not in balances.keys():
                balance_change = amount_transfered/(10**token_decimal)
                balances[token_contract] = {
                    'tokenSymbol': token_symbol, 'balance': balance_change}
            else:
                balance_modifier = 1 if isReceiver else -1
                balance_change = (amount_transfered /
                                  (10**token_decimal)) * balance_modifier
                balances[token_contract]['balance'] = balances[token_contract]['balance'] + \
                    balance_change
            # print()

            # if token_symbol not in balances.keys():
            #     balances[token_symbol] = amount_transfered/(10**token_decimal)
            # else:
            #     balance_modifier = 1 if isReceiver else -1
            #     balance_change = (amount_transfered /
            #                       (10**token_decimal)) * balance_modifier
            #     balances[token_symbol] = balances[token_symbol] + \
            #         balance_change

        # deduct fee
        balances["eth"]["balance"] = balances["eth"]["balance"] - \
            tx_fee/(10**eth_decimal)
        tx_moves['tx_fee'] = tx_fee/(10**eth_decimal)
        # set values in 'transactions'
        transactions[hash] = tx_moves

    return balances, transactions


def wallet_data_available_in_db(address_queried):
    db_wallet, created = Wallet.objects.get_or_create(address=address_queried)
    if not created:
        # wallet existed already, will add further checks for timestamp after

        # return db_wallet

        return False
    else:
        db_wallet.is_being_calculated = True
        return False


async def make_fetch(session, url, params={}):
    # print(time.time())
    # await asyncio.sleep(2)
    # return {'status':'asd', 'called_from':called_from}
    try:
        async with session.get(url, params=params) as resp:
            print(resp.status)
            assert resp.status == 200, f'Fetch to {resp.url}failed.'
            response_body = await resp.json()
            return response_body
    except Exception as e:
        print(e)
        print(resp)


async def initial_etherscan_api_request_tasks(address_queried):
    url = 'https://api.etherscan.io/api'
    ETHERSCAN_API_KEY = os.environ.get('ETHERSCAN_API_KEY')
    action_list = ['tokentx', 'txlistinternal', 'txlist']
    # print(address_queried)
    async with aiohttp.ClientSession() as session:
        tasks = [make_fetch(session, url, params={
            'module': 'account',
            'action': f'{action}',
            'address': address_queried,
            'apikey': ETHERSCAN_API_KEY,
        }) for action in action_list]

        datasets_list = await asyncio.gather(*tasks)
    return datasets_list


async def gather_current_prices(session, items_list):

    # Function to split the list into chunks of 30 items

    def chunks(lst, n):
        for i in range(0, len(lst), n):
            yield ','.join(lst[i:i + n])

    # Splitting the list into chunks of 30
    # items_list.remove('eth')
    chunked_list = list(chunks(items_list, 30))

    GECKOTERMINAL_BASE_URL = 'https://api.geckoterminal.com/api/v2'
    network = 'eth'
    url = f'{GECKOTERMINAL_BASE_URL}/simple/networks/{network}/token_price/'

    tasks = [asyncio.create_task(make_fetch(session, url=url+chunk))
             for chunk in chunked_list]
    # all_results = await asyncio.gather(*tasks)
    # return await asyncio.gather(*tasks)
    results = {}
    for completed_task in asyncio.as_completed(tasks):
        result = await completed_task
        results.update(result['data']['attributes']['token_prices'])
        # print(result)
    # print(results)
    return {'result_from': 'current', 'result': results}


async def gather_historic_prices(session, timestamps_of_eth_trades):
    timeFrom = int(min(timestamps_of_eth_trades))
    timeTo = int(max(timestamps_of_eth_trades))
    walletTransactionsTimespan = timeTo - timeFrom
    max_api_timeframe = 7200000
    limit = 2000
    api_calls_required = math.ceil(
        walletTransactionsTimespan / max_api_timeframe)
    # api supports max limit of 2000 data points at 1 hour intervals - 72000000 seconds in total
    CRYPTOCOMPARE_URL = 'https://min-api.cryptocompare.com/data/v2/histohour'
    CRYPTOCOMPARE_API_KEY = os.environ.get('CRYPTOCOMPARE_API_KEY')

    historic_tasks = [asyncio.create_task(make_fetch(session, CRYPTOCOMPARE_URL, params={
        'fsym': 'ETH',
        'tsym': 'USD',
        'toTs': timeTo-iteration*max_api_timeframe,
        'limit': limit,
        'api_key': CRYPTOCOMPARE_API_KEY, })) for iteration in range(api_calls_required)]
    # rr = await asyncio.gather(*historic_tasks)
    results = []
    for completed_task in asyncio.as_completed(historic_tasks):
        result = await completed_task
        results = [*results, *result["Data"]["Data"]]
        # print(time.time())
        # print(result)
    await asyncio.sleep(1)
    # f = open('historic_results.txt', 'a')
    # f.write(json.dumps(results))
    return {'result_from': 'historic', 'result': results}


async def process_current_prices(prices, balances):
    balances_prices_info = {}
    total_usd_value = 0
    for contract, price in prices.items():
        if price != "None" and price != None:
            print(price)
            usd_value = float(
                price) * balances[contract]['balance']
            balances_prices_info[contract] = {'latest_price': float(price)}
            balances_prices_info[contract]['usd_value'] = usd_value
            total_usd_value += usd_value
        else:
            balances_prices_info[contract] = {'latest_price': 0}
            balances_prices_info[contract]['usd_value'] = 0
    balances_prices_info['total_usd_value'] = total_usd_value
    await sync_to_async(send_event)('test', 'message', data={'current_token_prices': balances_prices_info})
    return balances_prices_info


async def process_historic_prices(prices, transaction_details):
    pass


async def normalize_historic_prices(prices_list):
    return {candle['time']: (float(candle["open"]) + float(candle["close"]))/2 for candle in prices_list}


async def query_historic_and_current_prices(timestamps_of_eth_trades, balances):

    # print(api_calls_required)
    async with aiohttp.ClientSession() as session:
        # print(f'{time.time()} - before before')
        # historic_tasks = await gather_historic_prices(session, timestamps_of_eth_trades)
        # historic
        _a = list(filter(lambda x: x != 'eth', balances.keys()))
        _a.extend(_a)
        # current_tasks = await gather_current_prices(session, _a)
        print(f'{time.time()} - before')
        tasks = [asyncio.create_task(gather_historic_prices(
            session, timestamps_of_eth_trades)), asyncio.create_task(gather_current_prices(session, _a))]
        # _r = await asyncio.gather(*tasks)
        # print(_r)

        balances_prices_info, normalized_prices = OrderedDict(), OrderedDict()
        for completed_task in asyncio.as_completed(tasks):
            result = await completed_task
            print(f'{time.time()} - result')
            if result['result_from'] == 'current':
                print('current')
                balances_prices_info = await process_current_prices(result['result'], balances)
          
            elif result['result_from'] == 'historic':
                normalized_prices = await normalize_historic_prices(result['result'])
                # print(normalized_prices)
            else:
                print('Result not recognized')
        # print(balanc++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++es_prices_info)
        return balances_prices_info, normalized_prices

    # if walletTransactionsTimespan < 7200000:
    #     toTs = timeTo
    #     limit = 2000
    # else:
    # print(timestamps_of_eth_trades)


def calculate_purchase_exchange_rate(transactions):
    denominators = {'ETH': 'eth', 'USDT': '0xdAC17F958D2ee523a2206206994597C13D831ec7',
                    'USDC': '0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48'}
    average_purchase_prices, transaction_details = {}, {}
    timestamps_of_eth_trades = []
    for tx, moves in transactions.items():
        # print(moves)
        price_in_denominated_token = 0
        denominated_in = ''
        traded_token = ''
        traded_token_symbol = ''
        is_receiver_of_traded_token = True

        if 'received' in moves.keys() and 'sent' in moves.keys() and len(moves['received']) == len(moves['sent']) and len(moves['received']) == 1:
            # print(next(iter(moves['received'].values())))
            received_contract, received_info = next(
                iter(moves['received'].items()))
            sent_contract, sent_info = next(iter(moves['sent'].items()))
            transaction_timestamp = moves['timeStamp']
            transaction_block = moves['blockNumber']
            # print(sent_contract, sent_info)
            # for moves_info in [moves['received'], moves['sent']]:
            # print(moves_info)
            # check if the wallet 'bought' or 'sold' a currency to determine which one the denominator should be
            if received_contract in denominators.values():
                # sold
                eth_traded = received_info['final_amount']
                # 0xba1b8cb8d81cf276c941788c1efd6680e85fb817591cfa900aec3cb124fe3ab4 throws error because sent amount shows as 0eth. some data is missing, there's some error in calculate_balances_and_txns
                traded_amount = sent_info['final_amount']
                price_in_denominated_token = eth_traded / \
                    traded_amount
                denominated_in = received_info['token_symbol']
                traded_token = sent_contract
                traded_token_symbol = sent_info['token_symbol']
                is_receiver_of_traded_token = False
            else:
                # bought
                eth_traded = sent_info['final_amount']
                traded_amount = received_info['final_amount']
                price_in_denominated_token = eth_traded / \
                    traded_amount
                denominated_in = sent_info['token_symbol']
                traded_token = received_contract
                traded_token_symbol = received_info['token_symbol']
            # print(denominated_in)

            if denominated_in == 'ETH':
                # change to api function
                # price_of_eth = check_token_price_at_timestamp_a(
                #     'ETH', moves['timeStamp'])
                # price_of_token_in_usd = price_in_denominated_token * price_of_eth
                price_of_token_in_usd = 'pending'

                timestamps_of_eth_trades.append(transaction_timestamp)
            elif denominated_in == denominators['USDT'] or denominated_in == denominators['USDC']:
                price_of_token_in_usd = price_in_denominated_token

            # moves['price_in_denominated_token'] = price_in_denominated_token
            # moves['denominated_in'] = denominated_in
            # moves['price_in_usd'] = price_of_token_in_usd
            # print(transaction_details)
            _txn_details_info = {'timeStamp': transaction_timestamp,
                                 'block': transaction_block,
                                 'exchanged_token_symbol': traded_token_symbol,
                                 'exchanged_token_contract': traded_token,
                                 'is_receiver': is_receiver_of_traded_token,
                                 'price_in_denominated_token': price_in_denominated_token,
                                 'denominated_in': denominated_in,
                                 'price_in_usd': price_of_token_in_usd,
                                 'value_of_trade_in_eth': eth_traded}
            # transaction_details[tx]['price_in_denominated_token'] = price_in_denominated_token
            # transaction_details[tx]['denominated_in'] = denominated_in
            # transaction_details[tx]['price_in_usd'] = price_of_token_in_usd
            transaction_details.setdefault(tx, {}).update(_txn_details_info)

            # calculate net purchase price

            # if traded_token not in average_purchase_prices.keys():
            #     average_purchase_prices[traded_token] = {'average_purchase_price': price_of_token_in_usd,
            #                                              'current_balance': traded_amount}
            # else:
            #     balance_modifier = 1 if is_receiver_of_traded_token else -1
            #     balance_before = average_purchase_prices[traded_token]['current_balance']
            #     average_purchase_prices[traded_token]['current_balance'] = balance_before + \
            #         balance_modifier * (traded_amount)
            #     if average_purchase_prices[traded_token]['current_balance'] != 0:
            #         print(called_from(price_of_token_in_usd))
            #         average_purchase_prices[traded_token]['average_purchase_price'] = (average_purchase_prices[traded_token]['average_purchase_price']*balance_before + balance_modifier*(
            #             price_of_token_in_usd*traded_amount))/average_purchase_prices[traded_token]['current_balance']

    return transaction_details, timestamps_of_eth_trades

def find_closest_to(price_list, timestamp):
    pos = bisect_left(price_list, timestamp)
    if pos == 0:
        return price_list[0]
    if pos == len(price_list):
        return price_list[-1]
    before = price_list[pos - 1]
    after = price_list[pos]
    if after - timestamp < timestamp - before:
        return after
    else:
        return before

def match_historic_prices(historic_prices, transaction_details):
    # for each transaction where price is pending, get timestamp and find closest value in prices list
    list_of_timestamps = list(historic_prices.keys())
    calculated_transaction_rates = OrderedDict()
    tokens_p_l = OrderedDict()
    for hash, details in transaction_details.items():
        if details['denominated_in'] == "ETH" and details['price_in_usd'] == "pending":
            txn_timestamp = int(details ['timeStamp'])
            is_receiver = bool(details['is_receiver'])
            exchanged_token = details['exchanged_token_contract']
            # if receiver -> add average prices
            closest_timestamp = find_closest_to(list_of_timestamps, txn_timestamp)
            eth_price_at_transaction_time = historic_prices[closest_timestamp]
            trade_eth_price = details['price_in_denominated_token']
            trade_usd_price = trade_eth_price * eth_price_at_transaction_time
            value_of_trade_eth = details['value_of_trade_in_eth']
            value_of_trade_in_usd = value_of_trade_eth * eth_price_at_transaction_time
            calculated_transaction_rates[hash] = {'timeStamp': txn_timestamp,
                                                  'price_in_usd': trade_usd_price}
            
            # calculations for p/l and final stats
            token_p_l_details = tokens_p_l.setdefault(exchanged_token, {})
            token_total_spent = token_p_l_details.setdefault('token_total_spent', value_of_trade_in_usd if is_receiver else 0)
            token_net_entry = token_p_l_details.setdefault('token_net_entry', trade_usd_price)
            token_gross_entry = token_p_l_details.setdefault('token_gross_entry', trade_usd_price)
            
    return calculated_transaction_rates

def wallet_calaulations_thread_worker(address_queried):
    # datasets_list = asyncio.run(initial_etherscan_api_request_tasks(address_queried))
    # combined_data = combine_records(*datasets_list)

    tokentx = json.loads(
        open(os.path.join(settings.BASE_DIR, 'tokentx.txt')).read())
    txlist = json.loads(
        open(os.path.join(settings.BASE_DIR, 'txlist.txt')).read())
    txlistinternal = json.loads(
        open(os.path.join(settings.BASE_DIR, 'txlistinternal.txt')).read())
    combined_data = combine_records(tokentx, txlist, txlistinternal)
    balances, transactions = calculate_balances_and_txns(
        address_queried, combined_data)

    # needed during dev as reading from file is quicker than the render and event is sent before render
    time.sleep(0.1)

    send_event('test', 'message', data={
               'balances': balances, 'transactions': transactions})

    # check_current_token_prices(balances)
    # print(calculate_purchase_exchange_rate(transactions))
    transactions_details, timestamps_of_eth_trades = calculate_purchase_exchange_rate(
        transactions)
    send_event('test', 'message', data={
               'transactions_details': transactions_details})
    # print(timestamps_of_eth_trades)

    balances_prices_info, normalized_historic_prices = asyncio.run(query_historic_and_current_prices(
        timestamps_of_eth_trades, balances))



    #match the closest historic price time to each of the txns
    calculated_historic_prices = match_historic_prices(normalized_historic_prices, transactions_details)
    # calctd = open('calctd.txt', 'a')
    # calctd.write(json.dumps(calculated_historic_prices))
    # send message
    send_event('test', 'message', data={'finalized_usd_prices': calculated_historic_prices})
    

    # write to db both balances and historic


    # trn = time.time()
    # print(trn)

    # check historic prices (transactions [30x batches/min]) ->
    #   ->    calculate total spent for each token based on historic prices
    # write to DB


def write_to_database_from_thread(balances):
    pass


def wallet_search(request):
    if request.method == 'POST':
        # print(request.__dict__)
        address_queried = request.POST.get('address')
        # check if data available in DB ( and if recent)
        # if yes - redirect to GET/{wallet}
        # if no - full API+data processing flow, then redirect to GET/{wallet}

        # return render(request, 'wallet/wallet_results.html')
        return redirect(f'/wallet/search/?address={address_queried}')
    elif request.method == 'GET':
        # check if data available in DB (and if recent)
        # if yes = render it
        # if not = redirect to the search page
        address_queried = request.GET.get('address')
        if not address_queried:
            return render(request, 'wallet/wallet_search.html')

        data_from_db = wallet_data_available_in_db(address_queried)
        if not data_from_db:
            wallet_data = {"data_status": 'pending'}
            thread = threading.Thread(
                target=wallet_calaulations_thread_worker, args=(address_queried,))
            thread.daemon = True
            thread.start()
        else:
            wallet_data = {"data_status": "ready", "wallet_info": data_from_db}
        return render(request, 'wallet/wallet_search.html', context={'address': address_queried, 'wallet_data': wallet_data})
