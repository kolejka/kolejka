# vim:ts=4:sts=4:sw=4:expandtab

import cgi
import json
import logging
import multiprocessing
from multiprocessing import Process
import pickle
import subprocess

from kolejka.common import settings
from kolejka.common import HTTPUnixConnection
from kolejka.common import KolejkaLimits, KolejkaStats

class KolejkaObserverClient:
    def __init__(self, socket_path=None, session=None, secret=None):
        if socket_path is None:
            socket_path = settings.OBSERVER_SOCKET
        self.connection = HTTPUnixConnection(socket_path)
        self.content_type = 'application/json; charset=utf-8'
        self.session = session
        self.secret = secret
    def request(self, cmd, path, headers, body):
        logging.debug('Observer client sent : '+str(body, 'utf-8'))
        self.connection.request(cmd, path, body, headers)
        with self.connection.getresponse() as response:
            response_type, response_type_dict  = cgi.parse_header(response.getheader('Content-Type', self.content_type))
            response_charset = response_type_dict.get('charset', 'utf-8')
            response_body = response.read().decode(response_charset)
            logging.debug('Observer client received : '+response_body)
            result = json.loads(response_body)
            self.session = result.get('session_id', self.session)
            self.secret = result.get('secret', self.secret)
            return result
    def post(self, path='/', params={}):
        headers = dict()
        pars = dict()
        pars.update(params)
        if self.session is not None:
            pars['session_id'] = self.session
        if self.secret is not None:
            pars['secret'] = self.secret
        body = bytes(json.dumps(pars), 'utf-8')
        headers['Content-Type'] = self.content_type
        headers['Content-Length'] = len(body)
        return self.request('POST', path, headers, body)

    def open(self):
        return self.post('/open')
    def attach(self, session=None):
        if session is not None:
            self.session = session
        return self.post('/attach')
    def detach(self, session=None):
        if session is not None:
            self.session = session
        return self.post('/detach')
    def limits(self, limits):
        return self.post('/limits', { 'limits' : limits.dump() })
    def stats(self):
        ret = KolejkaStats()
        ret.load(self.post('/stats'))
        return ret
    def close(self):
        ret = self.post('/close')
        self.session = None
        self.secret = None
        return ret
