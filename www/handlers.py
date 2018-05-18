import os
import asyncio
from coreweb import get, post, options
from aiohttp import web
import logging
import json
logging.basicConfig(level=logging.DEBUG)
from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv(), override=True)
from task import get_log, get_blockcount

NET = os.environ.get('NET')

def valid_net(net):
    return NET == net

def valid_txid(txid):
    if 66 == len(txid) and txid.startswith('0x'): return txid
    if 64 == len(txid): return '0x' + txid
    return None

@get('/')
def index(request):
    return {'hello':'%s' % NET,
            'GET':[
                '/',
                '/{net}/log',
                ],
            'ref':{
                'Source Code':'https://github.com/OTCGO/SUPER_NODE/',
                },
            'rpc':request.app['cache']['rpc'],
            'log':request.app['cache']['log'],
            }

@get('/{net}/log/{txid}')
async def get_applicationlog(net, txid, request):
    if not valid_net(net): return {'error':'wrong net'}
    txid = valid_txid(txid) 
    if not txid: return {'error':'wrong txid'}
    if request.app['cache']['log']:
        results = await asyncio.gather(*[get_log(request.app['session'], uri,txid) for uri in request.app['cache']['log']])
        for r in results:
            if r: return r
        else:
            return {'error':'fail to get applicationlog'}
    else:
        return {'error':'no node for get applicationlog'}

@get('/{net}/height')
async def get_height(net, request):
    if not valid_net(net): return {'error':'wrong net'}
    if request.app['cache']['rpc']:
        results = await asyncio.gather(*[get_blockcount(request.app['session'], uri) for uri in request.app['cache']['rpc']])
        result = list(filter(lambda i:i is not None, results))
        if result:
            return {'height':max(result)}
        else:
            return {'error':'fail to get height'}
    else:
        return {'error':'no node for get height'}
