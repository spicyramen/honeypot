import hashlib as hasher


class Block(object):
    """Block definition."""

    def __init__(self, index, timestamp, data, previous_hash):
        self.index = index
        self.timestamp = timestamp
        self.data = data
        self.previous_hash = previous_hash
        self.hash = self.hash_block()

    def hash_block(self):
        """

        :return:
        """
        sha = hasher.sha256()
        sha.update('%s%s%s%s' % (self.index, self.timestamp, self.data, self.previous_hash))
        return sha.hexdigest()
