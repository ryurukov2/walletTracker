import asyncio
from collections import OrderedDict
import math
import os

import aiohttp

from .data_processing import normalize_historic_prices, process_current_prices


async def initial_etherscan_api_request_tasks(address_queried, start_block=None):
    'Prepares and executes asynchronously API requests to gather the initial wallet data'
    url = 'https://api.etherscan.io/api'
    ETHERSCAN_API_KEY = os.environ.get('ETHERSCAN_API_KEY')
    action_list = ['tokentx', 'txlistinternal', 'txlist']
    # print(address_queried)
    async with aiohttp.ClientSession() as session:
        tasks = []
        for action in action_list:
            params = {
                'module': 'account',
                'action': action,
                'address': address_queried,
                'apikey': ETHERSCAN_API_KEY,
            }
            if start_block is not None:
                params['startblock'] = start_block
            
            tasks.append(make_fetch(session, url, params=params))

        datasets_list = await asyncio.gather(*tasks)
    return datasets_list

async def query_historic_and_current_prices(timestamps_of_eth_trades, balances, tokens_list):
    'Creates and executes tasks to asyncronously query current token prices and historic token prices'
    
    async with aiohttp.ClientSession() as session:
        
        # current_tasks = await gather_current_prices(session, _a)
        tasks = [asyncio.create_task(gather_historic_prices(
            session, timestamps_of_eth_trades)), asyncio.create_task(gather_current_prices(session, list(balances.keys())))]
        # _r = await asyncio.gather(*tasks)
        # print(_r)

        balances_prices_info, normalized_prices = OrderedDict(), OrderedDict()
        for completed_task in asyncio.as_completed(tasks):
            result = await completed_task
            if result['result_from'] == 'current':
                balances_prices_info = await process_current_prices(result['result'], balances, tokens_list)

            elif result['result_from'] == 'historic':
                normalized_prices = await normalize_historic_prices(result['result'])
                # print(normalized_prices)
            else:
                print('Result not recognized')
        # print(balances_prices_info)
        return balances_prices_info, normalized_prices

async def query_current_prices(balances):
    'Creates and executes tasks to query current token prices'

    async with aiohttp.ClientSession() as session:

        return await gather_current_prices(session, list(balances.keys()), isUpdate=True)


async def make_fetch(session, url, params={}):
    'Basic fetch function for async API requests'
    try:
        async with session.get(url, params=params) as resp:
            print(resp.status)
            assert resp.status == 200, f'Fetch to {resp.url}failed.'
            response_body = await resp.json()
            return response_body
    except Exception as e:
        print(e)
        print(resp)






async def gather_current_prices(session, items_list: list, isUpdate = False):
    'Query the current values of the tokens in the wallet'
    def chunks(lst, n):
        'split a list into chunks of n items'
        for i in range(0, len(lst), n):
            yield ','.join(lst[i:i + n])

    tasks = []
    # if there is ETH balance in the wallet, create the task since it has a different url
    if 'eth' in items_list:
        cryptocompare_eth_url = 'https://min-api.cryptocompare.com/data/price?fsym=ETH&tsyms=USD'
        tasks.append(asyncio.create_task(make_fetch(session, cryptocompare_eth_url)))
        items_list.remove('eth')

    
    chunked_list = list(chunks(items_list, 30))

    GECKOTERMINAL_BASE_URL = 'https://api.geckoterminal.com/api/v2'
    network = 'eth'
    if isUpdate:
        gecko_url = f'{GECKOTERMINAL_BASE_URL}/simple/networks/{network}/token_price/'
    else:
        gecko_url = f'{GECKOTERMINAL_BASE_URL}/networks/{network}/tokens/multi/'

    tasks.extend([asyncio.create_task(make_fetch(session, url=gecko_url+chunk))
             for chunk in chunked_list])
    
    
    # all_results = await asyncio.gather(*tasks)
    # return await asyncio.gather(*tasks)
    results = []
    processed = {}
    for completed_task in asyncio.as_completed(tasks):
        result = await completed_task
        
        if 'USD' in result:
            # means it is the ETH price, which has different layout - {USD:$USD}
            # image_url is missing.png for now because that's the default for the api that also provides the images
            processed.update({'eth': {'image_url': 'missing.png', 'price_usd': result['USD']}})

        if 'data' in result:
            # means it is one of the non eth batches
            if isUpdate:
                processed.update({contract: {'price_usd': result['data']['attributes']['token_prices'][contract]} 
                                   for contract in result['data']['attributes']['token_prices'].keys()})
            else:
                results.extend(result['data'])
    
    if not isUpdate:
        processed.update({att['attributes']['address']: {'image_url': att['attributes']['image_url'], 'price_usd': att['attributes']['price_usd']} for att in results})
    
        # print(result)
    # print(results)
    return {'result_from': 'current', 'result': processed}


async def gather_historic_prices(session, timestamps_of_eth_trades):
    'query the prices of ETH from the start to the end of the wallet transactions'
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
    # await asyncio.sleep(1)
    # f = open('historic_results.txt', 'a')
    # f.write(json.dumps(results))
    return {'result_from': 'historic', 'result': results}