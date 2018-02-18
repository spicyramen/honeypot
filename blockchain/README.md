# Blockchain implementation



## New transaction

```
curl "localhost:5001/transactions/new" -H "Content-Type: application/json" -d '{"sender": "honeypot-1", "recipient":"twilio", "amount": 10}'
```

## Start mining.

```
curl "localhost:5001/mine"
```

## Chain

```
curl "localhost:5001/chain"
```

## Adding a new node.

```
curl "localhost:5001/nodes/register" -H "Content-Type: application/json" -d '{"nodes": "http://127.0.0.1:5002"}'
```

## List nodes and resolve nodes.

```
curl "localhost:5001/nodes/resolve"
```


### Create sequence

This sequence will allow us to add some transactions to different
nodes. By creating a longer blockchain in a node.
We will create 2 transactions and mine them. 
Then resolve conflicts by selecting the longer blockchain in the available nodes
in network.

```
curl "localhost:5001/nodes/register" -H "Content-Type: application/json" -d '{"nodes": ["http://127.0.0.1:5002"]}'

curl "localhost:5001/nodes"

curl "localhost:5002/transactions/new" -H "Content-Type: application/json" -d '{"sender": "honeypot-2", "recipient":"twilio", "amount": 111, "hosts": ["+192.99.38.121"]}'

curl "localhost:5002/mine"

curl "localhost:5002/chain"

curl "localhost:5002/transactions/new" -H "Content-Type: application/json" -d '{"sender": "honeypot-2", "recipient":"twilio", "amount": 222, "hosts": ["+51.15.144.191"]}'

curl "localhost:5002/mine"

curl "localhost:5002/chain"

curl "localhost:5001/transactions/new" -H "Content-Type: application/json" -d '{"sender": "honeypot-1", "recipient":"twilio", "amount": 100, "hosts": ["+185.107.83.35"]}'

curl "localhost:5001/mine"

curl "localhost:5001/chain"

curl "localhost:5001/transactions/new" -H "Content-Type: application/json" -d '{"sender": "honeypot-1", "recipient":"twilio", "amount": 100, "hosts": ["-185.107.83.35"]}'

curl "localhost:5001/nodes/resolve"
```


### Closed consensus

In a Closed consensus mechanism certain nodes are required to put up a security deposit in order to participate in updating the Blockchain.

This consensus mechanism doesn’t require mining, and is growing in popularity in some banking and insurance segments.

The management of the consensus is done using security deposits which incentivize the validators. 

The “arbitrators” — conflict management nodes are the enforcers on the blockchain and the adjudicate when something is not write or if a miner is not acting fairly.

The main objective of using an arbitrator’s protocol is to enforce consensus among the autonomous nodes in the Blockchain.

If a validator authenticates a transaction which the arbitrators have considered illegitimate, then the validator losses their security deposit and they also forfeit their privileges of providing consensus in the Blockchain network in the future.