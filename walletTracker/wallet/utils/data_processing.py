from bisect import bisect_left
from collections import OrderedDict
import json
from asgiref.sync import sync_to_async
from django_eventstream import send_event

from .database_connections import get_all_suspicious_tokens
from django.core import serializers


def combine_records(token_tx, internal_tx, normal_tx):
    'Combines records from the three types of transactions'
    combined_data = {}

    def add_entry(entry):
        hash_value = entry['hash']
        hash_list = combined_data.setdefault(hash_value, {})
        hash_list[len(hash_list)] = entry

    for dataset in [token_tx, internal_tx, normal_tx]:
        for entry in dataset['result']:
            add_entry(entry)

    return combined_data


async def process_current_prices(prices, balances, tokens_list):
    'Processes the response data for the current prices of tokens in the wallet'
    balances_prices_info = {}
    total_usd_value = 0
    for contract, token_data in prices.items():
        if token_data['price_usd'] != "None" and token_data['price_usd'] != None:
            usd_value = float(
                token_data['price_usd']) * balances[contract]['balance']
            balances_prices_info[contract] = {
                'latest_price': token_data['price_usd']}
            balances_prices_info[contract]['usd_value'] = usd_value
            total_usd_value += usd_value
        else:
            balances_prices_info[contract] = {'latest_price': '0'}
            balances_prices_info[contract]['usd_value'] = 0
        if token_data['image_url'] != 'missing.png':
            tokens_list[contract].update(
                {'token_image_url': token_data['image_url']})
            balances_prices_info[contract].update(
                {'token_image_url': token_data['image_url']})

    balances_prices_info['total_usd_value'] = total_usd_value

    await sync_to_async(send_event)('test', 'message', data={'current_token_prices': balances_prices_info})

    return balances_prices_info


async def normalize_historic_prices(prices_list):
    'Processes the data returned from the historic ETH prices API, normalizes it to db requirements'
    return {candle['time']: (float(candle["open"]) + float(candle["close"]))/2 for candle in prices_list}


def calculate_purchase_exchange_rate(transactions):
    'Calculates exchange rates at the time of each transaction'
    # eth contract addresses for the tokens most often used as currency to buy/sell
    denominators = {'ETH': 'eth', 'USDT': '0xdAC17F958D2ee523a2206206994597C13D831ec7',
                    'USDC': '0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48'}

    transaction_details = OrderedDict()
    timestamps_of_eth_trades = []
    for tx, moves in transactions.items():
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

            # check if the wallet 'bought' or 'sold' a currency to determine which one the denominator should be
            if received_contract in denominators.values():
                # sold
                eth_traded = received_info['final_amount']
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

            _txn_details_info = {'timeStamp': transaction_timestamp,
                                 'blockNumber': transaction_block,
                                 'exchanged_token_symbol': traded_token_symbol,
                                 'exchanged_token_contract': traded_token,
                                 'is_receiver': is_receiver_of_traded_token,
                                 'exchanged_token_amount': traded_amount,
                                 'price_in_denominated_token': price_in_denominated_token,
                                 'denominated_in': denominated_in,
                                 'price_in_usd': price_of_token_in_usd,
                                 'value_of_trade_in_eth': eth_traded}
            transaction_details.setdefault(tx, {}).update(_txn_details_info)

    return transaction_details, timestamps_of_eth_trades


def find_closest_to(price_list, timestamp):
    'Returns the entry closest to a target value from a list'
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


def match_historic_prices(historic_prices, transaction_details, tokens_p_l = None):
    'for each transaction where price is pending, get timestamp and find closest value in prices list'
    list_of_timestamps = list(historic_prices.keys())
    calculated_transaction_rates = OrderedDict()
    if tokens_p_l == None:
        tokens_p_l = {}
    for hash, details in transaction_details.items():
        if details['denominated_in'] == "ETH" and details['price_in_usd'] == "pending":
            txn_timestamp = int(details['timeStamp'])
            is_receiver = bool(details['is_receiver'])
            exchanged_token_contract = details['exchanged_token_contract']
            exchanged_token_amount = details['exchanged_token_amount']
            # if receiver -> add average prices

            # calculate trade details for each transaction
            closest_timestamp = find_closest_to(
                list_of_timestamps, txn_timestamp)
            eth_price_at_transaction_time = historic_prices[closest_timestamp]
            trade_eth_price = details['price_in_denominated_token']
            trade_usd_price = trade_eth_price * eth_price_at_transaction_time
            value_of_trade_eth = details['value_of_trade_in_eth']
            value_of_trade_in_usd = value_of_trade_eth * eth_price_at_transaction_time
            calculated_transaction_rates[hash] = {'timeStamp': txn_timestamp,
                                                  'price_in_usd': trade_usd_price}

            # calculations for p/l and final stats

            token_p_l_details = tokens_p_l.setdefault(
                exchanged_token_contract, {})

            if 'balance' not in token_p_l_details.keys():
                token_p_l_details['balance'] = exchanged_token_amount if is_receiver else (
                    -1 * exchanged_token_amount)
                previous_token_balance = 0
            else:
                previous_token_balance = token_p_l_details['balance']
                token_p_l_details['balance'] = (
                    previous_token_balance + exchanged_token_amount) if is_receiver else (previous_token_balance - exchanged_token_amount)
            if 'total_usd_spent_for_token' not in token_p_l_details.keys():
                token_total_spent = value_of_trade_in_usd if is_receiver else 0
                token_p_l_details['total_usd_spent_for_token'] = token_total_spent
            else:
                token_total_spent = token_p_l_details['total_usd_spent_for_token']
                if is_receiver:
                    new_value = token_total_spent + value_of_trade_in_usd
                    token_p_l_details['total_usd_spent_for_token'] = new_value
            if 'total_usd_received_from_selling' not in token_p_l_details.keys():
                token_total_sold = value_of_trade_in_usd if not is_receiver else 0
                token_p_l_details['total_usd_received_from_selling'] = token_total_sold
            else:
                token_total_sold = token_p_l_details['total_usd_received_from_selling']
                if not is_receiver:
                    new_value = token_total_sold + value_of_trade_in_usd
                    token_p_l_details['total_usd_received_from_selling'] = new_value
            if 'purchased_token_amount' not in token_p_l_details.keys():
                token_p_l_details['purchased_token_amount'] = exchanged_token_amount if is_receiver else 0
            else:
                prev_value = token_p_l_details['purchased_token_amount']
                new_entry_value = prev_value + \
                    exchanged_token_amount if is_receiver else prev_value + 0
                token_p_l_details['purchased_token_amount'] = new_entry_value
            if 'sold_token_amount' not in token_p_l_details.keys():
                token_p_l_details['sold_token_amount'] = exchanged_token_amount if not is_receiver else 0
            else:
                prev_value = token_p_l_details['sold_token_amount']
                new_entry_value = prev_value + \
                    exchanged_token_amount if not is_receiver else prev_value + 0
                token_p_l_details['sold_token_amount'] = new_entry_value
            if 'net_purchase_price' not in token_p_l_details.keys():
                token_p_l_details['net_purchase_price'] = trade_usd_price if is_receiver else (
                    -1*trade_usd_price)
            else:
                current_token_balance = token_p_l_details['balance']
                token_net_entry = token_p_l_details['net_purchase_price']
                modifier = 1 if is_receiver else -1
                if current_token_balance == 0:
                    new_entry_value = 0
                else:
                    new_entry_value = ((token_net_entry * previous_token_balance) + (
                        modifier*(trade_usd_price * exchanged_token_amount))) / current_token_balance
                token_p_l_details['net_purchase_price'] = new_entry_value
            if 'average_purchase_price' not in token_p_l_details.keys():
                token_p_l_details['average_purchase_price'] = trade_usd_price if is_receiver else 0
            else:
                if is_receiver:
                    purchased_token_balance = token_p_l_details['purchased_token_amount']
                    if purchased_token_balance == 0:
                        new_entry_value = 0
                    else:
                        new_entry_value = ((token_p_l_details['average_purchase_price'] * previous_token_balance) + (
                            trade_usd_price*exchanged_token_amount)) / purchased_token_balance
                    token_p_l_details['average_purchase_price'] = new_entry_value

            token_historic_p_l = token_p_l_details['total_usd_received_from_selling'] - \
                token_p_l_details['total_usd_spent_for_token']
            token_p_l_details['token_realized_p_l'] = token_historic_p_l
    # print(tokens_p_l)

    return calculated_transaction_rates, tokens_p_l


def filter_suspicious_tokens(balances, balances_info):
    'Returns a list of tokens that seem suspicious, so they are not displayed and saved in DB'
    suspicious_tokens = []
    for contract in balances.keys():
        if contract not in balances_info.keys():
            suspicious_tokens.append(contract)

    return suspicious_tokens


def separate_suspicious_token_entries(balances: dict, transactions: dict, tokens_list: dict, suspicious_tokens: list):
    'Modifies the balances and transactions dictionaries and returns an object containing the filtered out balances and transactions'
    suspicious_balances, suspicious_transactions = {}, {}
    for contract in suspicious_tokens:
        if contract in tokens_list.keys():
            del tokens_list[contract]

    for contract in suspicious_tokens:
        if contract in balances.keys():
            suspicious_balances.setdefault(contract, balances[contract])
            del balances[contract]

    for hash in list(transactions.keys()):
        if 'received' in transactions[hash].keys():
            for contract in transactions[hash]['received'].keys():

                if contract in suspicious_tokens:
                    suspicious_transactions.setdefault(
                        hash, transactions[hash])
                    del transactions[hash]

    return {'suspicious_balances': suspicious_balances, 'suspicious_transactions': suspicious_transactions}


def filter_out_transaction_type(data_dict, type):
    'Returns a filtered dictionary where all transactions of the selected type are removed.'
    return_dict = dict()
    for hash, data in data_dict.items():
        if data["transaction_type"] == type:
            continue
        return_dict[hash] = data
    return return_dict


def take_first_n_from_dict(data_dict, n):
    return_dict = {}
    for id, k in enumerate(data_dict):
        if id == n:
            break
        return_dict[k] = data_dict[k]

    return return_dict


def take_last_n_from_dict(data_dict, n):
    return_dict = {}
    for id, k in enumerate(data_dict):
        if id < len(data_dict) - n:
            continue
        return_dict[k] = data_dict[k]

    return return_dict


def reverse_dict(data_dict):
    return dict(reversed(list(data_dict.items())))


def calculate_balances_and_txns(address, combined_data, transactions=None, balances=None, tokens_list=None):
    'Parse all transactions and return transactions, balances, token_list'
    suspicious_tokens = set(get_all_suspicious_tokens())
    if transactions is None:
        transactions = {}
    if balances is None:
        balances = {}
    if tokens_list is None:
        tokens_list = {}
    # dict with suspicious transactins and balances, not returned currently as they are not saved in DB
    suspicious_txns, suspicious_balances = {}, {}
    eth_decimal = 18
    for hash, transaction_entries in combined_data.items():
        # print(transaction_entries)
        tx_fee = 0
        tx_moves = {}
        transaction_type = ''
        isSusp = False

        for transaction_entry_data in transaction_entries.values():
            isReceiver = False
            amount_transfered = int(transaction_entry_data['value'])
            tx_moves['timeStamp'] = transaction_entry_data['timeStamp']
            tx_moves['blockNumber'] = transaction_entry_data['blockNumber']

            if transaction_entry_data['to'].lower() == address.lower():
                isReceiver = True
            elif transaction_entry_data['from']:
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

            if token_contract in suspicious_tokens:
                isSusp = True

            action = 'received' if isReceiver else 'sent'
            _trade_info = {
                'token_symbol': token_symbol,
                'final_amount': amount_transfered/(10**token_decimal),
                'precise_amount': amount_transfered,
                'token_decimal': token_decimal,
                'token_name': token_name
            }
            if token_contract not in tokens_list.keys() and not isSusp:
                token_info = {
                    'contract': token_contract,
                    'token_symbol': token_symbol,
                    'token_name': token_name,
                    'token_decimal': token_decimal
                }
                tokens_list[token_contract] = token_info

            if action not in tx_moves.keys() or token_contract not in tx_moves[action].keys():

                tx_moves.setdefault(action, {}).update(
                    {token_contract: _trade_info})
            else:

                tx_moves[action][token_contract]['precise_amount'] = float(
                    tx_moves[action][token_contract]['precise_amount']) + amount_transfered/(10**token_decimal)
                tx_moves[action][token_contract]['final_amount'] = float(
                    tx_moves[action][token_contract]['final_amount']) + amount_transfered/(10**token_decimal)
                # print(tx_moves[action][token_contract]['precise_amount'])

            balance_modifier = 1 if isReceiver else -1
            balance_change = (amount_transfered /
                              (10**token_decimal)) * balance_modifier
            if token_contract not in balances.keys():
                if not isSusp:
                    balances[token_contract] = {
                        'tokenSymbol': token_symbol, 'balance': balance_change}
                else:
                    suspicious_balances[token_contract] = {
                        'tokenSymbol': token_symbol, 'balance': balance_change}
            else:
                if not isSusp:
                    balances[token_contract]['balance'] = balances[token_contract]['balance'] + balance_change
                else:
                    suspicious_balances[token_contract]['balance'] = suspicious_balances[token_contract]['balance'] + balance_change

        # deduct fee
        if tx_fee != 0 and balances.get("eth"):
            balances["eth"]["balance"] = balances["eth"]["balance"] - \
                tx_fee/(10**eth_decimal)
            tx_moves['tx_fee'] = tx_fee/(10**eth_decimal)
        if 'sent' in tx_moves.keys() and 'received' in tx_moves.keys():
            transaction_type = 'Trade'
        elif 'sent' in tx_moves.keys():
            transaction_type = 'Send'
        elif 'received' in tx_moves.keys():
            transaction_type = 'Receive'
        else:
            transaction_type = 'Approve'

        tx_moves['transaction_type'] = transaction_type
        # set values in 'transactions'
        if not isSusp:
            transactions[hash] = tx_moves
        else:
            suspicious_txns[hash] = tx_moves

    # sort transactions by timestamp
    sorted_transactions = dict(
        sorted(transactions.items(), key=lambda item: int(item[1]['timeStamp'])))

    return balances, sorted_transactions, tokens_list


def calculate_total_token_p_l(balances_prices_info, historic_balances_p_l):
    'Calculates the total P/L for each token and the wallet itself'
    current_tokens_p_l = {}
    total_wallet_p_l, total_wallet_spent, total_wallet_sold = 0, 0, 0
    for contract, details in historic_balances_p_l.items():
        token_historic_p_l = details['token_realized_p_l']
        token_current_holdings_value = balances_prices_info[contract]['usd_value']
        token_final_p_l = token_historic_p_l + token_current_holdings_value
        token_total_spent = details['total_usd_spent_for_token']
        token_total_sold = details['total_usd_received_from_selling']

        current_tokens_p_l[contract] = token_final_p_l
        total_wallet_p_l = total_wallet_p_l + token_final_p_l
        total_wallet_spent = total_wallet_spent + token_total_spent
        total_wallet_sold = total_wallet_sold + token_total_sold

    current_tokens_p_l['total'] = total_wallet_p_l
    current_tokens_p_l['total_wallet_spent'] = total_wallet_spent
    current_tokens_p_l['total_wallet_sold'] = total_wallet_sold
    current_tokens_p_l['wallet_realized_p_l'] = total_wallet_sold - \
        total_wallet_spent
    current_tokens_p_l['total_usd_value'] = balances_prices_info['total_usd_value']
    return current_tokens_p_l


def separate_balances_data_for_p_l(balances_from_db):
    print('--------------------------------------------------------')
    old_balances = {token.token.contract: {"tokenSymbol": token.token.token_symbol, "balance": float(token.balance)}
                    for token in balances_from_db}
    token_ids = {token.token.id : token.token.contract for token in balances_from_db}
    
    tokens_list = {token.token.contract: {'contract': token.token.contract,
                                         'token_symbol': token.token.token_symbol,
                                         'token_name': token.token.token_name,
                                         'token_decimal': token.token.token_decimal} for token in balances_from_db}

    old_tokens_p_l = {}
    for json_item in json.loads(serializers.serialize("json", balances_from_db)):
        old_tokens_p_l[token_ids[json_item['fields']['token']]] = json_item['fields']
    return {'old_balances': old_balances,
            'old_tokens_p_l': old_tokens_p_l, 
            'old_tokens_list' : tokens_list}