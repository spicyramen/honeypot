import Connection
import time


class Client(object):
    """Connects to Freeswitch."""

    def __init__(self, host='127.0.0.1', port=8021, auth='ClueCon', ):
        self.host = host
        self.port = str(port)
        self.auth = auth
        self._con = Connection.Connection(self.host, self.port, self.auth)

    @property
    def con(self):
        return self._con

    def disconnect(self):
        """Disconnect the client's underlying connection."""
        self._con.disconnect()
        time.sleep(0.05)
        print 'Client.disconnected() '

    def connect(self):
        """Connect this client."""
        self._con.connect()
        assert self.connected(), "connect() Failed to connect to '{}'".format(
            self.host)

    def connected(self):
        """Check if connection is active."""
        return self._con.connected()
