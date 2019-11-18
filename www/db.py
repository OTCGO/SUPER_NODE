import asyncio
import aiomysql
from logzero import logger
import json
import sys


class DB:
    def __init__(self, mysql_args):  
        self.mysql_args = mysql_args

    async def init_pool(self):
        self.pool = await self.get_mysql_pool()

    async def get_mysql_pool(self):
        try:
            logger.info('start to connect db')
            pool = await aiomysql.create_pool(**self.mysql_args)
            logger.info('succeed to connet db!')
            return pool
        except asyncio.CancelledError:
            raise asyncio.CancelledError
        except Exception as e:
            logger.error("mysql connet failure:{}".format(e.args[0]))
            raise e

    async def get_mysql_cursor(self):
        conn = await self.pool.acquire()
        cur  = await conn.cursor()
        return conn, cur

    async def mysql_execute(self, sql):
        conn, cur = await self.get_mysql_cursor()
        logger.info('SQL:%s' % sql)
        try:
            await cur.execute(sql)
            return conn, cur
        except Exception as e:
            logger.error("mysql SQL:{} failure:{}".format(sql, e.args[0]))
            await self.pool.release(conn)
            raise e

    async def mysql_insert_one(self, sql):
        conn, cur = None, None
        try:
            conn, cur = await self.mysql_execute(sql)
            num = cur.rowcount
            return num
        except Exception as e:
            logger.error("mysql INSERT failure:{}".format(e.args))
            raise e
        finally:
            if conn:
                await self.pool.release(conn)

    async def mysql_query_one(self, sql):
        conn, cur = None, None
        try:
            conn, cur = await self.mysql_execute(sql)
            return await cur.fetchone()
        except Exception as e:
            logger.error("mysql QUERY failure:{}".format(e.args[0]))
            sys.exit(1)
        finally:
            if conn:
                await self.pool.release(conn)

    async def mysql_query_many(self, sql):
        conn, cur = None, None
        try:
            conn, cur = await self.mysql_execute(sql)
            return await cur.fetchall()
        except Exception as e:
            logger.error("mysql QUERY failure:{}".format(e.args[0]))
            raise e
        finally:
            if conn:
                await self.pool.release(conn)

    async def mysql_insert_many(self, sql, data):
        conn, cur = await self.get_mysql_cursor()
        logger.info('SQL MANY:%s' % sql)
        try:
            await cur.executemany(sql, data)
            num = cur.rowcount
            #logger.info('%s row affected' % num)
            return num
        except Exception as e:
            logger.error("mysql INSERT failure:{}".format(e.args[0]))
            sys.exit(1)
        finally:
            await self.pool.release(conn)

    async def get_applog(self, txid):
        try:
            result = await self.mysql_query_one("SELECT applog FROM applog WHERE txid='%s';" % txid)
            if result:
                return json.loads(result[0])
            return None
        except Exception as e:
            logger.error("mysql SELECT failure:{}".format(e))
            raise e

    async def update_applog(self, txid, applog):
        sql = "INSERT IGNORE INTO applog(txid,applog) VALUES ('%s','%s') ON DUPLICATE KEY UPDATE update_height=%s;" % (txid,json.dumps(applog))
        await self.mysql_insert_one(sql)
