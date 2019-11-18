#! /usr/bin/env python3
# coding: utf-8
# flow@SEA
# Licensed under the MIT License.

import os
from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv(), override=True)


class Config:

    @staticmethod
    def get_mysql_args():
        return {
            'host':    os.environ.get('MYSQLHOST'),
            'port':     int(os.environ.get('MYSQLPORT')),
            'user':     os.environ.get('MYSQLUSER'),
            'password': os.environ.get('MYSQLPASS'),
            'db':       os.environ.get('MYSQLDB'),
            'autocommit':True,
            'maxsize':256
        }

    @staticmethod
    def get_listen_ip():
        return os.environ.get('LISTENIP')

    @staticmethod
    def get_listen_port():
        return os.environ.get('LISTENPORT')

    @staticmethod
    def get_net():
        return os.environ.get('NET')

    @staticmethod
    def get_seeds():
        seeds = []
        seed_num = int(os.environ.get('SEEDNUM'))
        for i in range(1, seed_num+1):
            seeds.append(os.environ.get('SEED{}'.format(i)))
        return seeds
