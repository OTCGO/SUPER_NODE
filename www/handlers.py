import os
import asyncio
from coreweb import get, post, options
from aiohttp import web
import logging
logging.basicConfig(level=logging.DEBUG)
from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv(), override=True)
from io import StringIO

NET = os.environ.get('NET')

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
            'random':request.app['cache'].getvalue(),
            }
