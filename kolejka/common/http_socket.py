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
