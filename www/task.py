import logging; logging.basicConfig(level=logging.INFO)
import asyncio
import aiohttp
import os
from datetime import datetime
from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv(), override=True)

NET = os.environ.get('NET')

def get_seeds():
    seeds = []
    seed_num = int(os.environ.get('SEEDNUM'))
    for i in range(1, seed_num+1):
        seeds.append(os.environ.get('SEED{}'.format(i)))
    return seeds

async def get_rpc(session, uri, method, params, timeout=10):
    async with session.post(uri,
            json={'jsonrpc':'2.0','method':method,'params':params,'id':1}, timeout=timeout) as resp:
        if 200 != resp.status:
            logging.error('Unable to visit %s %s' % (uri, method))
            return None
        j = await resp.json()
        if 'error' in j.keys():
            logging.error('result error when %s %s' % (uri, method))
            return None
        return j['result']

async def get_peers(session, uri):
    try:
        return await get_rpc(session, uri, 'getpeers', [])
    except Exception as e:
        logging.error('error to get peers of %s %s' % (uri,e))
        return None

async def get_log(session, uri, txid=None):
    if not txid:
        if 'mainnet' == NET: txid = '0xc920b2192e74eda4ca6140510813aa40fef1767d00c152aa6f8027c24bdf14f2'
        if 'testnet' == NET: txid = '0x1bae5666ef5d645bb7d6edbe53a179763fda44a1b4ec6a49c2051883e03d0ba1'
    try:
        return await get_rpc(session, uri, 'getapplicationlog', [txid])
    except Exception as e:
        #logging.error('error to get log of %s %s' % (uri,e))
        return None

async def scan(session, cache):
    print('Begin to scanning: %s' % datetime.now())
    seeds = get_seeds()
    result = await asyncio.gather(*[get_peers(session, seed) for seed in seeds])
    peers = []
    for r in result:
        if r:
            peers.extend([i['address'][7:]+':'+str(i['port']-1) for i in r['connected'] if i['port']>0])
    cache['peers'] = list(set(peers))
    urls = ['http://'+peer for peer in cache['peers']] + ['https://'+peer for peer in cache['peers']]
    urls.extend(cache['log'])
    urls.extend(seeds)
    urls = list(set(urls))
    log_peers = []
    log_result = await asyncio.gather(*[get_log(session, url) for url in urls])
    for i in range(len(log_result)):
        if log_result[i]:
            log_peers.append(urls[i])
    cache['log'] = log_peers

