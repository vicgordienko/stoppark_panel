from gevent import socket, sleep


class SafeSocket(object):
    def __init__(self, peer, reconnect_interval=2):
        self.sock = None
        self.peer = peer
        self.reconnect_interval = reconnect_interval
        self.reconnect()

    def reconnect(self):
        if self.sock is not None:
            self.sock.close()
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        while True:
            print 'trying to connect to', self.peer
            try:
                self.sock.connect(self.peer)
                break
            except socket.error:
                sleep(self.reconnect_interval)
                continue

    def recv(self, *args):
        while True:
            try:
                data = self.sock.recv(*args)
                if data == '':
                    self.reconnect()
                else:
                    return data
            except socket.error:
                self.reconnect()

    def send(self, *args):
        while True:
            try:
                return self.sock.send(*args)
            except socket.error:
                self.reconnect()