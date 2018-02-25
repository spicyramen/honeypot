"""Gets call information from Database."""

import datetime
import pytz


class Call(object):
    def __init__(self, call_id, source_ip, source_port):
        self.call_id = call_id
        self.source_ip = source_ip
        self.source_port = source_port

    def GetCallInfo(self, db_client):
        """

        :param db_client:
        :return:
        """
        # Make it UTC aware
        today = datetime.datetime.now(pytz.UTC).strftime('%Y%m%d')
        query = """
        SELECT
            ruri,
            ruri_user,
            ruri_domain,
            from_user,
            from_domain,
            from_tag,
            to_user,
            contact_user,
            callid,
            content_type,
            user_agent,
            source_ip,
            source_port,
            destination_port,
            contact_ip,
            contact_port
        FROM
            homer_data.sip_capture_call_%s
        WHERE
            method = 'INVITE'
            AND callid = '%s'
            AND source_ip = '%s'
            AND source_port = %d
        """ % (today, self.call_id, self.source_ip, self.source_port)

        return db_client.query(query)
