import ESL
import time


def check_con(con):
    '''Raise a connection error if this connection is down
    '''
    # XXX sometimes after the 1st cmd sent to the server
    # the connection will be lost? (lib esl bug?)
    if not con:
        return False
    event = con.api('status')
    return bool(con.connected()) and bool(event)


class ESLError(Exception):
    """An error pertaining to the connection"""

    def __init__(self, value):
        self.value = value
        self.code = 4

    def __str__(self):
        return repr(self.value)


class Connection(object):
    '''
    Connection wrapper which can provide mutex attr access making the
    underlying ESL.ESLconnection thread safe

    Note
    ----
    This class must be explicitly connected before use.
    '''

    def __init__(self, host, port=8021, auth='ClueCon', ):
        """
        Parameters
        -----------
        host : string
            host name or ip address for server hosting an esl connection.
        port : string
            port where esl connection socket is being offered.
        auth : string
            authentication password for esl connection.
        """
        self.host = host
        self.port = str(port)
        self.auth = auth
        self._con = None

    def recvEventTimed(self, time):
        try:
            return self._con.recvEventTimed(time)
        except AttributeError:
            raise ESLError("call `connect` first")

    def events(self, event_type, events):
        try:
            return self._con.events(event_type, events)
        except AttributeError:
            raise ESLError("call `connect` first")

    def api(self, cmd):
        """

        :param cmd:
        :return:
        """
        try:
            return self._con.api(cmd)
        except AttributeError:
            raise ESLError("call `connect` first")

    def bgapi(self, cmd):
        """

        :param cmd:
        :return:
        """
        try:
            return self._con.bgapi(cmd)
        except AttributeError:
            raise ESLError("call `connect` first")

    def __enter__(self, **kwargs):
        self.connect(**kwargs)
        return self

    def __exit__(self, exception_type, exception_val, trace):
        self.disconnect()

    def disconnect(self):
        """Rewrap disconnect to avoid deadlocks
        """
        if self.connected():
            ret = self._con.disconnect()
            self._sub = ()  # reset subscription
            return not bool(ret)
        return False

    def connect(self, host=None, port=None, auth=None):
        """Reconnect if disconnected
        """
        host = host or self.host
        port = port or self.port
        auth = auth or self.auth
        if not self.connected():
            # XXX: try a few times since connections seem to be flaky
            # We should probably try to fix this in the _ESL.so
            for _ in range(5):
                self._con = ESL.ESLconnection(*map(str, (host, port, auth)))
                time.sleep(0.05)
                if check_con(self._con):
                    break
                else:
                    self._con = False
        if not check_con(self._con):
            raise ESLError(
                "Failed to connect to server at '{}:{}'\n"
                "Please check that FreeSWITCH is running and "
                "accepting ESL connections.".format(host, port))
        # on success change our contact info
        self.host = host
        self.port = port
        self.auth = auth

    def connected(self):
        """
            Return bool indicating if this connection is active
        """
        if not self._con:
            return False
        return bool(self._con.connected())
