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

async def get_blockcount(session, uri, timeout=10):
    try:
        return await get_rpc(session, uri, 'getblockcount', [], timeout)
    except Exception as e:
        logging.error('error to get blockcount of %s %s' % (uri,e))
        return None

async def get_peers(session, uri, timeout=10):
    try:
        return await get_rpc(session, uri, 'getpeers', [], timeout)
    except Exception as e:
        logging.error('error to get peers of %s %s' % (uri,e))
        return None

async def get_log(session, uri, txid=None, timeout=30):
    if not txid:
        if 'mainnet' == NET: txid = '0xd4e01144f6088028bc5af0e7e5e5dc9a0d133d54154275a966abd346d2319ff0'
        if 'testnet' == NET: txid = '0x1bae5666ef5d645bb7d6edbe53a179763fda44a1b4ec6a49c2051883e03d0ba1'
    try:
        return await get_rpc(session, uri, 'getapplicationlog', [txid], timeout)
    except Exception as e:
        #logging.error('error to get log of %s %s' % (uri,e))
        return None


async def scan(session, cache):
    print('Begin to scanning: %s' % datetime.now())

    seeds = get_seeds()
    urls = []
    urls.extend(cache['log'])
    urls.extend(seeds)
    urls = list(set(urls))
    rpcs = []
    rpc_result = await asyncio.gather(*[get_blockcount(session, url) for url in urls])
    for i in range(len(rpc_result)):
        if rpc_result[i]:
            rpcs.append(urls[i])
    cache['rpc'] = rpcs

    fasts = []
    height = max([r for r in rpc_result if r])
    for i in range(len(rpc_result)):
        if height == rpc_result[i]:
            fasts.append(urls[i])
    cache['fast'] = fasts

    if cache['height'] < height:
        cache['height'] = height

    logs = []
    log_result = await asyncio.gather(*[get_log(session, url) for url in cache['fast']])
    for i in range(len(log_result)):
        if log_result[i]:
            logs.append(cache['fast'][i])
    cache['log'] = logs

async def update_height(session, cache):
    rpc_result = await asyncio.gather(*[get_blockcount(session, url) for url in cache['fast']])
    if not rpc_result: return

    fasts = []
    height = max([r for r in rpc_result if r])

    if cache['height'] < height:
        cache['height'] = height
