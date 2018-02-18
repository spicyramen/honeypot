"""Blockchain implementation. Using Flask Web App."""

import hashlib
import json
import requests
import urlparse
import uuid

from absl import app
from absl import flags
from absl import logging

from time import time

from flask import Flask, jsonify, request

FLAGS = flags.FLAGS

flags.DEFINE_string('host', '0.0.0.0', 'API host')
flags.DEFINE_integer('port', 5000, 'API port')

# Generate a globally unique address for this node
MINER_ADDRESS = "honeypot-miner-%s" % str(uuid.uuid1()).upper().replace("-", "")[:10]


class Blockchain(object):
    def __init__(self):
        self.current_transactions = []
        self.chain = []
        self.nodes = set()

        # Create the genesis block.
        self.new_block(previous_hash='1', proof=100)

    @property
    def last_block(self):
        return self.chain[-1]

    def register_node(self, address):
        """
        Add a new node to the list of nodes
        :param address: Address of node. Eg. 'http://192.168.0.5:5000'
        """

        parsed_url = urlparse.urlparse(address)
        if parsed_url.netloc:
            logging.info('Adding node: %s' % parsed_url.netloc)
            self.nodes.add(parsed_url.netloc)
        elif parsed_url.path:
            # Accepts an URL without scheme like '192.168.0.5:5000'.
            logging.info('Adding node: %s' % parsed_url.path)
            self.nodes.add(parsed_url.path)
        else:
            raise ValueError('Invalid URL')

    def valid_chain(self, chain):
        """
        Determine if a given blockchain is valid.

        :param chain: A blockchain.
        :return: True if valid, False if not
        """

        last_block = chain[0]
        current_index = 1

        logging.info('Chain: %r' % chain)
        while current_index < len(chain):
            block = chain[current_index]
            logging.info('Last block: %s \n Current block: %s' % (last_block, block))
            # Check that the hash of the block is correct.
            if block['previous_hash'] != self.hash(last_block):
                logging.error('Proof of Work is not valid. Hash is different')
                return False

            # Check that the Proof of Work is correct.
            logging.info('Validating Last block: %s Current block: %s Current block previous hash %s' % (
                last_block['proof'], block['proof'], block['previous_hash']))
            if not self.valid_proof(last_block['proof'], block['proof'], block['previous_hash']):
                logging.error('Proof of work is not valid.')
                return False
            last_block = block
            current_index += 1

        logging.info('Chain is valid.')
        return True

    def resolve_conflicts(self):
        """
        This is the consensus algorithm, it resolves conflicts
        by replacing local chain with the longest one in the network.

        :return: True if our chain was replaced, False if not
        """

        neighbours = self.nodes
        new_chain = None

        # We're only looking for chains longer than ours
        max_length = len(self.chain)
        logging.info('Current blockchain length: %s' % max_length)

        # Grab and verify the chains from all the nodes in our network
        for node in neighbours:
            logging.info('Contacting %s' % node)
            response = requests.get('http://%s/chain' % node)

            if response.status_code == 200:
                length = response.json()['length']
                chain = response.json()['chain']

                # Check if the length is longer and the chain is valid.
                logging.info('New blockchain length: %s for node: %s' % (length, node))
                if length > max_length and self.valid_chain(chain):
                    max_length = length
                    new_chain = chain

        # Replace our chain if we discovered a new, valid chain longer than ours.
        if new_chain:
            self.chain = new_chain
            return True

        return False

    def new_block(self, proof, previous_hash):
        """
        Create a new Block in the Blockchain

        :param proof: (int) The proof given by the Proof of Work algorithm
        :param previous_hash: (str) Hash of previous Block
        :return: New Block
        """

        block = {
            'index': len(self.chain) + 1,
            'timestamp': time(),
            'transactions': self.current_transactions,
            'proof': proof,
            'previous_hash': previous_hash or self.hash(self.chain[-1]),
        }

        # Reset the current list of transactions
        self.current_transactions = []

        self.chain.append(block)
        return block

    def new_transaction(self, sender, recipient, amount, hosts):
        """
        Creates a new transaction to go into the next mined Block

        :param sender: Address of the Sender
        :param recipient: Address of the Recipient
        :param amount: Amount
        :param hosts: Attackers.
        :return: The index of the Block that will hold this transaction
        """
        logging.info(
            'New transaction sender: %s recipient: %s amount: %s hosts: %r' % (sender, recipient, amount, hosts))
        self.current_transactions.append({
            'sender': sender,
            'recipient': recipient,
            'amount': amount,
            'hosts': hosts,
        })

        return self.last_block['index'] + 1

    @staticmethod
    def hash(block):
        """
        Creates a SHA-256 hash of a Block

        :param block: Block
        """

        # We must make sure that the Dictionary is Ordered, or we'll have inconsistent hashes
        block_string = json.dumps(block, sort_keys=True).encode()
        return hashlib.sha256(block_string).hexdigest()

    def proof_of_work(self, last_block):
        """
        Simple Proof of Work Algorithm:

         - Find a number p' such that hash(pp') contains leading 4 zeroes
         - Where p is the previous proof, and p' is the new proof

        :param last_block: (dict) last Block
        :return: <int>
        """

        last_proof = last_block['proof']
        last_hash = self.hash(last_block)

        proof = 0
        while self.valid_proof(last_proof, proof, last_hash) is False:
            proof += 1

        return proof

    @staticmethod
    def valid_proof(last_proof, proof, last_hash):
        """
        Validates the Proof

        :param last_proof: (int) Previous Proof.
        :param proof: (int) Current Proof.
        :param last_hash: (str) The hash of the Current Block.
        :return: (bool) True if correct, False if not.

        """

        guess = '%s%s%s'.encode() % (last_proof, proof, last_hash)
        guess_hash = hashlib.sha256(guess).hexdigest()
        return guess_hash[:4] == "0000"


# Instantiate the Node.
blockchain_app = Flask(__name__)

# Instantiate the Blockchain.
blockchain = Blockchain()


@blockchain_app.route('/mine', methods=['GET'])
def mine():
    # We run the proof of work algorithm to get the next proof...
    last_block = blockchain.last_block
    proof = blockchain.proof_of_work(last_block)

    # We must receive a reward for finding the proof.
    # The sender is "0" to signify that this node has mined a new coin.
    blockchain.new_transaction(
        sender='0',
        recipient=MINER_ADDRESS,
        amount=1,
        hosts=[],
    )

    # Forge the new Block by adding it to the chain
    previous_hash = blockchain.hash(last_block)
    block = blockchain.new_block(proof, previous_hash)

    response = {
        'message': "New Block Forged",
        'index': block['index'],
        'transactions': block['transactions'],
        'proof': block['proof'],
        'previous_hash': block['previous_hash'],
    }
    return jsonify(response), 200


@blockchain_app.route('/transactions/new', methods=['POST'])
def new_transaction():
    values = request.get_json()

    # Check that the required fields are in the POST'ed data.
    required = ['sender', 'recipient', 'amount']
    if not all(k in values for k in required):
        return 'Missing values', 400

    # Create a new Transaction.
    index = blockchain.new_transaction(values['sender'], values['recipient'], values['amount'], values['hosts'])

    response = {'message': 'Transaction will be added to Block %s ' % index}
    return jsonify(response), 201


@blockchain_app.route('/chain', methods=['GET'])
def full_chain():
    response = {
        'chain': blockchain.chain,
        'length': len(blockchain.chain),
    }
    return jsonify(response), 200


@blockchain_app.route('/nodes/register', methods=['POST'])
def register_nodes():
    values = request.get_json()

    nodes = values.get('nodes')

    if nodes is None or not isinstance(nodes, list):
        return "Error: Please supply a valid list of nodes", 400

    for node in nodes:
        blockchain.register_node(node)

    response = {
        'message': 'New nodes have been added',
        'total_nodes': list(blockchain.nodes),
    }
    return jsonify(response), 201


@blockchain_app.route('/nodes', methods=['GET'])
def list_nodes():
    response = {
        'message': 'List of nodes',
        'total_nodes': list(blockchain.nodes),
    }
    return jsonify(response), 200


@blockchain_app.route('/nodes/resolve', methods=['GET'])
def consensus():
    replaced = blockchain.resolve_conflicts()

    if replaced:
        response = {
            'message': 'Our chain was replaced',
            'new_chain': blockchain.chain
        }
    else:
        response = {
            'message': 'Our chain is authoritative',
            'chain': blockchain.chain
        }

    return jsonify(response), 200


def main(_):
    logging.info('Starting Blockchain...')
    blockchain_app.run(host=FLAGS.host, port=FLAGS.port)


if __name__ == '__main__':
    app.run(main)
