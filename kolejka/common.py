# vim:ts=4:sts=4:sw=4:expandtab

import http.client
import os
import socket
import socketserver
import struct

class HTTPUnixServer(socketserver.UnixStreamServer):
    
    allow_reuse_address = 1
    
    def server_bind(self):
        try:
            os.unlink(self.server_address)
        except:
            pass
        socketserver.UnixStreamServer.server_bind(self)
        os.chmod(self.server_address, 0o777)
        self.server_name = str(self.server_address)
        self.server_port = ""

    def get_request(self):
        request, client_address = self.socket.accept()
        client_credentials = request.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, struct.calcsize('3i'))
        client_pid, client_uid, client_gid = struct.unpack('3i', client_credentials)
        return (request, (str(client_pid), ""))

    def server_close(self):
        super().server_close()
        try:
            os.unlink(self.server_address)
        except:
            pass

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.server_close()

class HTTPUnixConnection(http.client.HTTPConnection):
    def _get_hostport(self, host, port):
        return (self.socket_path, None)

    def __init__(self, socket_path):
        self.socket_path = socket_path
        super().__init__(self, socket_path)

    def connect(self):
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.connect(self.socket_path)

        if self._tunnel_host:
            self._tunnel()


def parse_float_with_modifiers(x, modifiers):
    modifier = 1
    x = x.strip().lower()
    while len(x) > 0 and x[-1] in modifiers :
        modifier *= modifiers[x[-1]]
        x = x[:-1]
    return float(x) * modifier

def parse_time(x) :
    return parse_float_with_modifiers(x, {
        's' : 1,
        'm' : 10**-3,
        'µ' : 10**-6,
        'n' : 10**-9,
    })

def parse_memory(x):
    return int(round(parse_float_with_modifiers(x, {
        'b' : 1,
        'k' : 1024,
        'm' : 1024**2,
        'g' : 1024**3,
        't' : 1024**4,
        'p' : 1024**5,
    })))

