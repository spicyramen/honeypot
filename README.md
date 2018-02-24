# Honeypot

## Intro

This software provides a solution to detect Toll Fraud attacks.
By setting up Honeypots in the cloud we are able to detect IP addresses
and attack patterns for attackers which are scanning 
Network infrastructure. 
This software provides an interface to notify network equipment about 
attackers.

## Topology

 - Honeypot server
    - Freeswitch
    - Kamailio
    - Homer
    - Database (PostgresSQL, MySQL)
 
 - Honeypot analyzer
    - Pub/Sub notification infrastructure via PubNub.
    - Tensorflow classification model.
 
 - Honeypot services
    - Database (PostgresSQL)
    - REST API via Python Flask
    - Shared log (Blockchain)
    
 - Orchestration module
    - Chef recipes
    - Dockerfile configuration