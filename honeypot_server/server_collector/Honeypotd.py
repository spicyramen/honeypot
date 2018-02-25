"""Honeypot main application."""

import time

from absl import app
from absl import flags
from absl import logging

from honeypot_analyzer.publisher_notifier import Call
from honeypot_analyzer.threat_analyzer.prediction import threat_prediction
from honeypot_server.conf import settings
from honeypot_server.conf import whitelist

from honeypot_server.call_control import Client
from honeypot_server.call_control.Connection import ESLError
from honeypot_analyzer.publisher_notifier import Publisher

from utils import mysql_client

FLAGS = flags.FLAGS

flags.DEFINE_string('host', '127.0.0.1', 'Freeswitch ESL server')
flags.DEFINE_integer('port', 8021, 'Freeswitch ESL port')

# Freeswitch ESL events to Monitor.
EVENTS = ['BACKGROUND_JOB',
          'DETECTED_TONE',
          'CHANNEL_OUTGOING',
          'CHANNEL_CREATE',
          'CHANNEL_ANSWER',
          'CHANNEL_PROGRESS_MEDIA',
          'RECORD_START',
          'CHANNEL_HANGUP',
          'CHAN_NOT_IMPLEMENTED']

# Freeswitch variables.
_CHANNEL_UUID = 'Channel-Call-UUID'
_SIP_CALL_ID = 'variable_sip_call_id'
_SIP_TERM_STATUS = 'variable_sip_term_status'
_SIP_INVITE_FAILURE_MSG = 'variable_sip_invite_failure_phrase'
_SIP_NETWORK_IP = 'variable_sip_network_ip'
_SIP_TO_USER = 'variable_sip_to_user'
_SIP_REQUEST_URI = 'variable_sip_req_uri'
_SIP_PROTOCOL = 'variable_sip_via_protocol'
_SIP_REMOTE_PORT = 'variable_sip_network_port'
_SIP_FROM_STRIPPED = 'variable_sip_from_user_stripped'
_SIP_FROM = 'variable_sip_full_from'

DB_CLIENT = mysql_client.MySQLClient(username=settings.HOMER_DB_USER,
                                     password=settings.HOMER_DB_PASSWORD,
                                     host=settings.HOMER_DB_HOST,
                                     port=settings.HOMER_DB_PORT,
                                     database=settings.HOMER_DATABASE)


class ESLHandler(object):
    """Listens for Event Socket Layer ESL signals from Freeswitch."""

    def __init__(self, host, port, events):
        self._host = host
        self._port = port
        self._events = events
        self.pending_calls = []

    @property
    def host(self, host):
        self._host = host

    @host.getter
    def host(self):
        return self._host

    @property
    def port(self, port):
        self._port = port

    @port.getter
    def port(self):
        return self._port

    @property
    def events(self, events):
        self._events = events

    @events.getter
    def events(self):
        return self._events

    def predict(self, sip_call_id, sip_remote_ip_addr, sip_remote_port, pending):
        """

        :param sip_call_id:
        :param sip_remote_ip_addr:
        :param sip_remote_port:
        :param pending:
        :return:
        """

        caller = Call.Call(sip_call_id, sip_remote_ip_addr, int(sip_remote_port))
        potential_threat = caller.GetCallInfo(DB_CLIENT)
        if not potential_threat:
            logging.error('Call with callid: %s was not found in Database' % sip_call_id)
            return -1

        # Ask Threat analyzer to predict if caller is an Attacker.
        potential_threat = [str(call) if call else '' for call in potential_threat]
        label, stats = threat_prediction.predict(potential_threat)
        if label == 1:
            logging.warning('Threat detected %s . Remote SIP host: %s ' % (stats, sip_remote_ip_addr))
            return 1
        else:
            logging.info('No threat %s' % stats)
            return 0

    def listen(self):
        """

        :return:
        """
        try:
            logging.info('Initializing Publisher...')
            # Generate notifications to clients that subscribe service via PubNub (pubnub.com).

            pnconfig = Publisher.GetConfig()
            if not isinstance(pnconfig, Publisher.PNConfiguration):
                raise ValueError('Invalid PubNub configuration')

            pubnub = Publisher.Publisher(pnconfig)

            logging.info('Listener starting...')
            if not self.host:
                raise ValueError('Invalid host')
            try:
                client = Client.Client(host=self.host)
                logging.info('Connecting to Freeswitch: %s ...' % self.host)
                client.connect()
                if not client.connected():
                    raise ValueError('Unable to connect to %s' % self.host)
            except ESLError as e:
                logging.exception(e)

            logging.info('Connected to %s' % self.host)

            connection = client.con
            connection.events('plain', self.events)
            time.sleep(0.05)
            stay_connected = True

            while stay_connected:
                reply = connection.recvEventTimed(1000)
                if reply:
                    event_name = reply.getHeader('Event-Name')
                    logging.info('Event name: %s' % event_name)

                   # Call is received.
                    if event_name == 'CHANNEL_CREATE':
                        uuid = reply.getHeader(_CHANNEL_UUID)
                        logging.info('Call UUID: %s' % uuid)
                    # Call is completed.
                    elif event_name == 'CHANNEL_HANGUP':
                        uuid = reply.getHeader(_CHANNEL_UUID)
                        hangup_cause = reply.getHeader('Hangup-Cause')
                        # Collect SIP information.
                        sip_call_id = reply.getHeader(_SIP_CALL_ID)
                        sip_term_status = reply.getHeader(_SIP_TERM_STATUS)
                        sip_invite_failure_phrase = reply.getHeader(_SIP_INVITE_FAILURE_MSG)
                        # Collect SIP call details.
                        sip_remote_ip_addr = reply.getHeader(_SIP_NETWORK_IP)
                        sip_remote_port = reply.getHeader(_SIP_REMOTE_PORT)
                        sip_protocol = reply.getHeader(_SIP_PROTOCOL)
                        sip_from_stripped = reply.getHeader(_SIP_FROM_STRIPPED)
                        sip_from = reply.getHeader(_SIP_FROM)
                        sip_to_user = reply.getHeader(_SIP_TO_USER)
                        sip_req_uri = reply.getHeader(_SIP_REQUEST_URI)

                        logging.warning('Call ended UUID: %s Reason: %s' % (uuid, hangup_cause))
                        if sip_term_status:
                            if int(sip_term_status) >= 400:
                                logging.error('SIP Error. Call ended %s %s %s %s' % (uuid,
                                                                                     sip_call_id, sip_term_status,
                                                                                     sip_invite_failure_phrase))
                        logging.info('Send event to Threat Analyzer...')

                        # Use PubSub notification systems.
                        if sip_remote_ip_addr not in whitelist.WHITE_LIST:
                            # Connect to Homer and get Caller information.
                            threat = self.predict(sip_call_id, sip_remote_ip_addr, int(sip_remote_port), False)
                            if threat == 1:
                                call_info = {"Honeypot": pnconfig.uuid,
                                             "RemoteIpv4": sip_remote_ip_addr,
                                             "SipProtocol": sip_protocol,
                                             "SipRemotePort": sip_remote_port,
                                             "SipFrom": sip_from,
                                             "SipFromStripped": sip_from_stripped,
                                             "SipTo": sip_to_user,
                                             "RequestUri": sip_req_uri,
                                             "SipCallid": sip_call_id
                                             }
                                logging.info('Notifying Subscribers: Call info: %s' % call_info)
                                # Notify Network via PubNub.
                                try:
                                    pubnub.publish(Publisher.CHANNEL, call_info)
                                except ValueError as e:
                                    logging.exception(e)
                            elif threat == -1:
                                logging.info('Adding call to Queue')
                                self.pending_calls.append((sip_call_id, sip_remote_ip_addr, int(sip_remote_port)))
                                continue
                        else:
                            logging.warning(
                                'Detected IP Address in Whitelist: %s. No notification was sent.' % sip_remote_ip_addr)

                else:
                    logging.info('Listening...')
                    if len(self.pending_calls) > 1:
                        logging.warning('%d Calls in Queue' % len(self.pending_calls))
                    #TODO Process asyncronously (Celery/RabbitMQ)

        except KeyboardInterrupt:
            logging.warning('Exiting manually...')
            logging.info('Pending calls to process: %d' % self.pending_calls)


def main(_):
    # Connect to Freeswitch.
    listener_instance = ESLHandler(settings.FREESWITCH_HOST, FLAGS.port, ' '.join(EVENTS))
    listener_instance.listen()


if __name__ == '__main__':
    app.run(main)
