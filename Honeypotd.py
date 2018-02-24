"""Honeypot main application."""

import time

from absl import app
from absl import flags
from absl import logging

from conf import whitelist
from freeswitch import Client
from freeswitch.Connection import ESLError
from notifications import Publisher

FLAGS = flags.FLAGS

flags.DEFINE_string('host', '127.0.0.1', 'Freeswitch ESL server')
flags.DEFINE_integer('port', 8021, 'Freeswitch ESL port')

# Freeswitch ESL IP Address.
FREESWITCH_HOST = '13.57.9.131'

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


class ESLHandler(object):
    """Gets ESL signals from Freeswitch."""

    def __init__(self, host, port, events):
        self._host = host
        self._port = port
        self._events = events

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

    def listen(self):
        """

        :return:
        """
        try:
            # Generate notifications to clients that subscribe service.
            logging.info('Initializing Publisher...')
            pnconfig = Publisher.GetConfig()
            if not isinstance(pnconfig, Publisher.PNConfiguration):
                raise ValueError('Invalid PubNub configuration')
            pubnub = Publisher.Publisher(pnconfig)

            logging.info('Listener starting...')
            if not self.host:
                raise ValueError('Invalid host')

            client = Client.Client(host=self.host)
            logging.info('Connecting to Freeswitch: %s ...' % self.host)
            client.connect()
            if not client.connected():
                raise ValueError('Unable to connect to %s' % self.host)

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
                        # Notify Network.
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
                        # Use PubSub notification systems.
                        if sip_remote_ip_addr not in whitelist.WHITE_LIST:
                            logging.warning('Threat detected. Remote SIP host: %s ' % sip_remote_ip_addr)
                            logging.info('Call info: %r' % call_info)
                            pubnub.publish(Publisher.CHANNEL, call_info)
                        else:
                            logging.warning(
                                'Detected IP Address in white list: %s. No notification was sent. Call info: %r' % (
                                sip_remote_ip_addr, call_info))
                else:
                    logging.info('Listening...')

        except ESLError as e:
            logging.exception(e)
        except KeyboardInterrupt:
            logging.warning('Exiting manually...')


def main(_):
    listener_instance = ESLHandler(FREESWITCH_HOST, FLAGS.port, ' '.join(EVENTS))
    listener_instance.listen()


if __name__ == '__main__':
    app.run(main)
