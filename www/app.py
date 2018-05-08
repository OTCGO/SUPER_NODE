import logging; logging.basicConfig(level=logging.INFO)
import asyncio
import aiohttp
import json
import os
import time
import uvloop; asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from io import StringIO
from aiohttp import web
from coreweb import add_routes
from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv(), override=True)

def get_seeds():
    seeds = []
    seed_num = int(os.environ.get('SEEDNUM'))
    for i in range(1, seed_num+1):
        seeds.append(os.environ.get('SEED{}'.format(i)))
    return seeds

async def get_rpc(session,uri,method,params):
    async with session.post(uri,
            json={'jsonrpc':'2.0','method':method,'params':params,'id':1}) as resp:
        if 200 != resp.status:
            logging.error('Unable to visit %s %s' % (uri, method))
            return '404'
        j = await resp.json()
        if 'error' in j.keys():
            logging.error('result error when %s %s' % (uri, method))
            return '404'
        return j['result']

async def get_peers(session, uri):
    try:
        return await get_rpc(session, uri, 'getpeers', [])
    except Exception as e:
        logging.error('error to get peers of {}'.format(uri))
        return None

async def scan(cache, session):
    print('Begin to scanning: %s' % datetime.now())
    seeds = get_seeds()
    result = await asyncio.gather(*[get_peers(session,seed) for seed in seeds])
    peers = []
    for r in result:
        if r:
            peers.extend([i['address'][7:]+':'+str(i['port']-1) for i in r['connected']])
    cache.seek(0)
    cache.write(json.dumps(list(set(peers))))

get_listen_ip = lambda:os.environ.get('LISTENIP')
get_listen_port = lambda:os.environ.get('LISTENPORT')

async def logger_factory(app, handler):
    async def logger(request):
        logging.info('request:%s %s' % (request.method, request.path))
        return (await handler(request))
    return logger

async def response_factory(app, handler):
    async def response(request):
        logging.info('Response handler..')
        r = await handler(request)
        if isinstance(r, web.StreamResponse):
            return r
        if isinstance(r, bytes):
            resp = web.Response(body=r)
            resp = content_type = 'Application/octet-stream'
            return resp
        if isinstance(r, str):
            if r.startswith('redirect:'):
                return web.HTTPFound(r[9:])
            resp = web.Response(body=r.encode('utf-8'))
            resp.content_type = 'text/html;charset=utf-8'
            resp.headers["access-control-allow-origin"] = "*"
            resp.headers["Access-Control-Allow-Headers"] = "content-type, x-requested-with"
            resp.headers['Access-Control-Allow-Methods'] = 'POST, GET'
            return resp
        if isinstance(r, dict):
            template = r.get('__template__')
            if template is None:
                resp = web.Response(body=json.dumps(r, ensure_ascii=False, default=lambda o:o.__dict__).encode('utf-8'))
                resp.content_type = 'Application/json;charset=utf-8'
                resp.headers["access-control-allow-origin"] = "*"
                resp.headers["Access-Control-Allow-Headers"] = "x-requested-with"
                resp.headers['Access-Control-Allow-Methods'] = 'POST, GET'
                return resp
            else:
                resp = web.Response(body=app['__templating__'].get_template(template).render(**r).encode('utf-8'))
                resp.content_type = 'text/html;charset=utf-8'
                return resp
        if isinstance(r, int) and r >= 100 and r < 600:
            return web.Response(r)
        if isinstance(r, tuple) and len(r) == 2:
            t, m = r
            if isinstance(t, int) and t>= 100 and t < 600:
                return web.Response(t, str(m))
        #default
        resp = web.Response(body=str(r).encode('utf-8'))
        resp.content_type = 'text/plain;charset=utf-8'
        return resp
    return response


async def init(loop):
    cache = StringIO()
    session = aiohttp.ClientSession(loop=loop,connector_owner=False)
    scheduler = AsyncIOScheduler(job_defaults = {
                    'coalesce': True,
                    'max_instances': 1,
                    'misfire_grace_time': 20
        })
    scheduler.add_job(scan, 'interval', minutes=1, args=[cache,session], id='super_node')
    scheduler.start()
    app = web.Application(loop=loop, middlewares=[
        logger_factory, response_factory
    ])
    listen_ip = get_listen_ip()
    listen_port = get_listen_port()
    app['cache'] = cache
    app['session'] = session
    app['scheduler'] = scheduler
    add_routes(app, 'handlers')
    srv = await loop.create_server(app.make_handler(), listen_ip, listen_port)
    logging.info('server started at http://%s:%s...' % (listen_ip, listen_port))
    return srv

loop = asyncio.get_event_loop()
loop.run_until_complete(init(loop))
loop.run_forever()
