# vim:ts=4:sts=4:sw=4:expandtab

import argparse
import cgi
import http.client
import json
import logging
import os
from urllib.parse import urlparse, urlencode, parse_qsl

import kolejka.settings
from kolejka.common import HTTPUnixConnection

class KolejkaObserverClient:
    def __init__(self, socket_path=None, session=None, secret=None):
        if socket_path is None:
            socket_path = kolejka.settings.OBSERVER_SOCKET
        self.connection = HTTPUnixConnection(socket_path)
        self.content_type = 'application/json; charset=utf-8'
        self.session = session
        self.secret = secret
    def request(self, cmd, path, headers, body):
        self.connection.request(cmd, path, body, headers)
        with self.connection.getresponse() as response:
            response_type, response_type_dict  = cgi.parse_header(response.getheader('Content-Type', self.content_type))
            response_charset = response_type_dict.get('charset', 'utf-8')
            response_body = response.read().decode(response_charset)
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
    def get(self, path='/', params={}):
        pars = dict()
        pars.update(params)
        pars['content_type'] = 'application/json'
        if self.session is not None:
            pars['session_id'] = self.session
        if self.secret is not None:
            pars['secret'] = self.secret
        path = path+'?'+urlencode(pars)
        return self.request('GET', path, dict(), None)
