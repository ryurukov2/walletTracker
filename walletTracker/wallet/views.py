import json
from django.conf import settings
from django.shortcuts import render, redirect
from dotenv import load_dotenv
import os
load_dotenv()

# Create your views here.
def index(request):
    return render(request, 'index.html')


def combine_records(token_tx, internal_tx, normal_tx, combined_data):
    def add_entry(entry):
        hash_value = entry['hash']
        hash_list = combined_data.setdefault(hash_value, {})
        hash_list[len(hash_list)] = entry
    for dataset in [normal_tx, token_tx, internal_tx]:
        for entry in dataset['result']:
            add_entry(entry)


def calculate_balances_and_txns(address, combined_data, balances, transactions):
    eth_decimal = 18
    for hash, tx in combined_data.items():
        # print(tx)
        tx_fee = 0
        tx_moves = {}

        for t in tx.values():
            isReceiver = False
            amount_transfered = int(t['value'])
            tx_moves['timeStamp'] = t['timeStamp']

            if t['to'].lower() == address.lower():
                isReceiver = True
            else:
                if tx_fee == 0 and t['gasPrice'] != '' and t['gasUsed'] != '':
                    tx_fee = int(t['gasPrice'])*int(t['gasUsed'])
                # print(t)
                if 'isError' in t.keys() and t['isError'] == '1':
                    tx_moves['isError'] = '1'
                    continue

                isReceiver = False
            if t['contractAddress'] != "":
                token_name = t['tokenName']
                token_contract = t['contractAddress']
                token_symbol = t['tokenSymbol']
                token_decimal = int(t['tokenDecimal'])
            else:
                token_name = 'Ethereum'
                token_contract = 'eth'
                token_symbol = 'ETH'
                token_decimal = eth_decimal

            action = 'received' if isReceiver else 'sent'
            if action not in tx_moves.keys():
                tx_moves[action] = {
                    'token_symbol': token_symbol,
                    'amount': amount_transfered/(10**token_decimal),
                    'token_contract': token_contract,
                    'token_name': token_name
                }
            else:
                if token_symbol not in tx_moves[action].values():
                    tx_moves[action]['token_symbol'] = token_symbol
                    tx_moves[action]['token_contract'] = token_contract
                    tx_moves[action]['token_name'] = token_name
                    tx_moves[action]['amount'] = amount_transfered / \
                        (10**token_decimal)
                else:
                    tx_moves[action]['amount'] = float(
                        tx_moves[action]['amount']) + amount_transfered/(10**token_decimal)

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
        balances["eth"]["balance"] = balances["eth"]["balance"] - \
            tx_fee/(10**eth_decimal)
        tx_moves['tx_fee'] = tx_fee/(10**eth_decimal)

        transactions[hash] = tx_moves


def wallet_search(request):
    if request.method=='POST':
        # print(request)
        wallet_address = request.POST.get('address')
        #check if data available in DB ( and if recent)
        #if yes - redirect to GET/{wallet}
        #if no - full API+data processing flow, then redirect to GET/{wallet}

        # return render(request, 'wallet/wallet_results.html')
        return redirect(f'/wallet/search/?address={wallet_address}')
    elif request.method=='GET':
        #check if data available in DB (and if recent)
        #if yes = render it
        #if not = redirect to the search page
        wallet_address = request.GET.get('address')




        #simulating API response data
        tokentx = json.loads(open(os.path.join(settings.BASE_DIR, 'tokentx.txt')).read())
        txlist = json.loads(open(os.path.join(settings.BASE_DIR, 'txlist.txt')).read())
        txlistinternal = json.loads(open(os.path.join(settings.BASE_DIR, 'txlistinternal.txt')).read())
        print(wallet_address)
        # print(tokentx['result'])
        combined_data = {}
        combine_records(tokentx, txlistinternal, txlist, combined_data)
        
        return render(request, 'wallet/wallet_search.html', context = {'address': wallet_address})