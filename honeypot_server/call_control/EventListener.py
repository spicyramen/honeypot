from collections import deque, OrderedDict, defaultdict, Counter, namedtuple
from threading import Thread, current_thread
import functools
import time


class EventListener(object):
    '''ESL Listener which tracks FreeSWITCH state using an observer pattern.
    This implementation utilizes a background event loop (single thread)
    and one `Connection`.
    The main purpose is to enable event oriented state tracking of various
    slave process objects and call entities.
    '''
    HOST = '127.0.0.1'
    PORT = '8021'
    AUTH = 'ClueCon'

    def __init__(self, rx_con=None,
                 events=None,
                 ):
        '''
        Parameters
        ----------
        host : string
            Hostname or ip of the FS engine server to listen to
        port : string
            Port on which the FS server is offering an esl connection
        auth : string
            Authentication password for connecting via esl
        '''
        self._events = None

    @property
    def events(self):
        return self._events

    @events.setter
    def events(self, events):
        self._events = events