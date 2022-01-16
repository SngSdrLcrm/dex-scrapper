import math
from multiprocessing import pool
from thor_requests.connect import Connect
from thor_requests.contract import Contract


contract = Contract.fromFile('./zumo_abis/UniswapV2Pair.json')

def getReserves(connector, caller, pool_addr, block_number="best"):
    ''' Raises exception if pool not found in the old blocks '''
    result = connector.call(
        caller,
        contract,
        'getReserves',
        [],
        pool_addr,
        block=block_number
    )
    return {
        '0': int(result['decoded']['0']),
        '1': int(result['decoded']['1'])
    }

def getTotalSupply(connector, caller, pool_addr, block_number="best"):
    ''' Raises exception if pool not found in the old blocks '''
    result = connector.call(
        caller,
        contract,
        'totalSupply',
        [],
        pool_addr,
        block=block_number
    )

    return int(result['decoded']['0'])

def calc_apy(token0_old:int, token1_old:int, token0_new:int, token1_new:int, duration_days:float) -> float:
    ''' Calculate the growth of tokens in a pool, with duration of days '''
    a = math.sqrt(token0_old * token1_old)
    b = math.sqrt(token0_new * token1_new)
    growth_apy = (b / a - 1) / duration_days * 365
    return growth_apy

def inspect_apy(connector, pool_interested:str, day_near:int, day_older:int) -> float:
    '''
        Inspect apy of a pool, inspection period of day_near of day_older.
        If you inspect from today to 15 days ago, do 0, 15
        If you inspect from today to 30 days ago, do 0, 30
        If you inspect from 15 days ago to 30 days ago (15 days), do 15, 30
    '''
    # Caller
    caller = '0x0000000000000000000000000000000000000000'

    # Best block (now)
    block_best_number = int(connector.get_block()['number'])

    a = getReserves(
        connector,
        caller,
        pool_interested,
        int(block_best_number - day_near * (60 * 60 * 24 / 10)) # Go back day_near days
    )

    b = getTotalSupply(
        connector,
        caller,
        pool_interested,
        int(block_best_number - day_near * (60 * 60 * 24 / 10)) # Go back day_near days
    )

    # print(a['0'], a['1'])
    # print(b)

    token0_per_share = a['0'] / b
    token1_per_share = a['1'] / b
    # print(token0_per_share)
    # print(token1_per_share)


    c = getReserves(
        connector,
        caller,
        pool_interested,
        int(block_best_number - day_older * (60 * 60 * 24 / 10)) # Go back 30 days
    )

    d = getTotalSupply(
        connector,
        caller,
        pool_interested,
        int(block_best_number - day_older * (60 * 60 * 24 / 10)) # Go back X days
    )

    # print(c['0'], c['1'])
    # print(d)

    token0_per_share_old = c['0'] / d
    token1_per_share_old = c['1'] / d
    # print(token0_per_share_old)
    # print(token1_per_share_old)

    growth_apy = calc_apy(
        token0_per_share_old,
        token1_per_share_old,
        token0_per_share,
        token1_per_share, 
        abs(day_near - day_older)
        )
    return abs(growth_apy)


import json
import sys

if __name__ == "__main__":
    node_url = sys.argv[1].lower()
    print(f'Connecting: {node_url}')

    day_near = int(sys.argv[2]) # for example, 0 (days) ago
    day_old = int(sys.argv[3]) # for example, 7 (days) ago

    print(f'Inspectin APY, from {day_near} days to {day_old} days ago:')
    connector = Connect('https://mainnet.veblocks.net')

    pools = []
    with open('./zumo_info/pools.json', 'r') as f:
        pools = json.load(f)
    
    for pool in pools:
        try:
            the_apy = inspect_apy(connector, pool['address'], day_near, day_old)
            growth_apy_display_str = "{0:.2f} %".format(the_apy * 100)
            print(f'{pool["name"]}: {growth_apy_display_str}')
        except:
            pass