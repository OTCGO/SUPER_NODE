import json
import asyncio
import aiohttp
from logzero import logger
import uvloop; asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiohttp import web
from coreweb import add_routes
from config import Config as C
from task import scan, update_height
from db import DB


async def logger_factory(app, handler):
    async def mylogger(request):
        logger.info('request:%s %s' % (request.method, request.path))
        return (await handler(request))
    return mylogger

async def response_factory(app, handler):
    async def response(request):
        logger.info('Response handler..')
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
    conn = aiohttp.TCPConnector(limit=10000, limit_per_host=10)#, ssl=False)
    session = aiohttp.ClientSession(connector=conn)
    cache = {'height':0, 'fast':[], 'rpc':[],'log':[]}
    scheduler = AsyncIOScheduler(job_defaults = {
                    'coalesce': True,
                    'max_instances': 1,
                    'misfire_grace_time': 3
        })
    scheduler.add_job(scan, 'interval', seconds=30, args=[session, cache], id='super_node')
    scheduler.add_job(update_height, 'interval', seconds=4, args=[session, cache], id='update_height')
    scheduler.start()
    app = web.Application(loop=loop, middlewares=[
        logger_factory, response_factory
    ])
    listen_ip = C.get_listen_ip()
    listen_port = C.get_listen_port()
    app['session'] = session
    app['cache'] = cache
    app['scheduler'] = scheduler
    app['db'] = DB(C.get_mysql_args())
    await app['db'].init_pool()
    add_routes(app, 'handlers')
    srv = await loop.create_server(app.make_handler(), listen_ip, listen_port)
    logger.info('server started at http://%s:%s...' % (listen_ip, listen_port))
    return srv


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(init(loop))
    loop.run_forever()
