import json
import asyncio
from aiohttp import web
from config import Config as C
from coreweb import get, post, options
from task import get_log, get_blockcount, get_block_timepoint

NET = C.get_net()

def valid_net(net):
    return NET == net

def valid_height(height):
    try:
        h = int(height)
        if h >= 0: return True
        return False
    except: return False

def valid_txid(txid):
    if 66 == len(txid) and txid.startswith('0x'): return txid[2:]
    if 64 == len(txid): return txid
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
            'height':request.app['cache']['height'],
            'fast':request.app['cache']['fast'],
            'rpc':request.app['cache']['rpc'],
            'log':request.app['cache']['log'],
            }

@get('/{net}/log/{txid}')
async def get_applicationlog(net, txid, request):
    #args verification
    if not valid_net(net): return {'error':'wrong net'}
    txid = valid_txid(txid) 
    if not txid: return {'error':'wrong txid'}
    #db query
    log = await request.app['db'].get_applog(txid)
    if log:
        del log['_id']
        return log
    #node query
    if request.app['cache']['log']:
        results = await asyncio.gather(*[get_log(request.app['session'], uri,txid) for uri in request.app['cache']['log']])
        for r in results:
            if r:
                await request.app['db'].update_applog(txid, r)
                return r
        else:
            return {'error':'fail to get applicationlog'}
    else:
        return {'error':'no node for get applicationlog'}

@get('/{net}/height')
async def get_height(net, request):
    if not valid_net(net): return {'error':'wrong net'}
    return {'height':request.app['cache']['height']}

@get('/{net}/timepoint/{height}')
async def get_timepoint(net, height, request):
    if not valid_net(net): return {'error':'wrong net'}
    if not valid_height(height): return {'error':'wrong height'}
    h = int(height)
    if h > request.app['cache']['height']: return {'error':'wrong height'}
    if request.app['cache']['fast']:
        tp = await get_block_timepoint(request.app['session'], request.app['cache']['fast'][0], h)
        if tp: return {'timepoint':tp}
        return {'error':'can not to get timepoint'}
    return {'error':'can not to get timepoint'}
