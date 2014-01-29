from gevent import socket, sleep


class SafeSocket(object):
    def __init__(self, peer, reconnect_interval=5, attempt_limit=None):
        self.sock = None
        self.peer = peer
        self.reconnect_interval = reconnect_interval
        self.attempt_limit = attempt_limit
        self.reconnect()

    @staticmethod
    def attempt_counter(limit):
        counter = 1
        while True:
            if limit is None or limit >= counter:
                yield counter
            else:
                break
            counter += 1

    @property
    def connected(self):
        return self.sock is not None

    def reconnect(self):
        if self.sock is not None:
            self.sock.shutdown(socket.SHUT_RDWR)
            self.sock.close()
        counter = self.attempt_counter(self.attempt_limit)
        for c in counter:
            self.sock = socket.socket(socket.AF_UNIX if hasattr(socket, 'AF_UNIX') else socket.AF_INET,
                                      socket.SOCK_STREAM)
            print c, 'attempt to connect to', self.peer
            try:
                self.sock.connect(self.peer)
                print 'connection to', self.peer, 'established'
                break
            except socket.error:
                sleep(self.reconnect_interval)
                self.sock = None
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