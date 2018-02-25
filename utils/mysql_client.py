"""This is a MySQL client which allows connection to database."""

from absl import logging

import MySQLdb as mdb


class MySQLClient(object):
    """This class allows you to connect to MySQL database."""

    def __init__(self, username='root', password='', host='127.0.0.1', port=3306, database='default'):
        """

        :param username:
        :param password:
        :param host:
        :param port:
        :param database:
        :return:
        """
        self._username = username
        self._password = password
        self._host = host
        self._port = port
        self._database = database
        self.cnx = self.connect()

    def disconnect(self, cnx):
        """
        :return:
        """
        cnx.close()

    def connect(self):
        """

        :return:
        """
        cnx = mdb.connect(self._host, self._username, self._password, self._database, self._port)
        return cnx

    def query(self, query):
        """

        :param cnx:
        :param query:
        :return:
        """

        cursor = self.cnx.cursor()
        cursor.execute(query)
        if cursor.rowcount < 1:
            logging.error('No information')
        return cursor.fetchone()

