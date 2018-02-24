from absl import app
from absl import logging

from pubnub.callbacks import SubscribeCallback
from pubnub.enums import PNStatusCategory
from pubnub.pnconfiguration import PNConfiguration
from pubnub.pubnub import PubNub

CHANNEL = 'honeypot'


def PublisherCallBack(envelope, status):
    # Check whether request successfully completed or not
    if not status.is_error():
        logging.info(status)
        pass  # Message successfully published to specified channel.
    else:
        pass  # Handle message publish error. Check 'category' property to find out possible issue
        # because of which request did fail.
        # Request can be resent using: [status retry];


class MySubscribeCallback(SubscribeCallback):
    def presence(self, pubnub, presence):
        pass  # handle incoming presence data

    def status(self, pubnub, status):
        if status.category == PNStatusCategory.PNUnexpectedDisconnectCategory:
            pass  # This event happens when radio / connectivity is lost

        elif status.category == PNStatusCategory.PNConnectedCategory:
            # Connect event. You can do stuff like publish, and know you'll get it.
            # Or just use the connected event to confirm you are subscribed for
            # UI / internal notifications, etc
            pubnub.publish().channel(CHANNEL).message('Client is connected.').async(PublisherCallBack)
        elif status.category == PNStatusCategory.PNReconnectedCategory:
            # Happens as part of our regular operation. This event happens when
            # radio / connectivity is lost, then regained.
            pubnub.publish().channel(CHANNEL).message('Client reconnected, we are online again.').async(
                PublisherCallBack)
            logging.warning('Client reconnected, we are online again.')
        elif status.category == PNStatusCategory.PNDecryptionErrorCategory:
            pass
            # Handle message decryption error. Probably client configured to
            # encrypt messages and on live data feed it received plain text.

    def message(self, pubnub, message):
        """Handle new message stored in message.message"""
        msg = message.message
        logging.info('Received message: %s' % msg)


def main(_):
    pnconfig = PNConfiguration()
    pnconfig.publish_key = 'pub-c-ef4b6aa1-d5ca-43f8-92c8-f9840fb5bb9f'
    pnconfig.subscribe_key = 'sub-c-151a8936-0fc7-11e8-941f-7e2964818bdb'
    pubnub = PubNub(pnconfig)
    pubnub.add_listener(MySubscribeCallback())
    pubnub.subscribe().channels(CHANNEL).execute()


if __name__ == '__main__':
    app.run(main)
