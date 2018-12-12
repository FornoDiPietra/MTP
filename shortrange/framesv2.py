#!/usr/bin/python3
# -*- coding: utf-8 -*-

import os
import math

'''
-------------------------------------------------------
|       |         |          |                        |
|@Sender|@Receiver| ACK/NACK | Packet Sequence Number |   
|       |         |          |                        |
-------------------------------------------------------
   3b       3b         2b               1B
'''
def getAck(deviceID, nextHopID, pckID, ackNack):
    
    payload1 = deviceID << 5 | nextHopID << 2

    if ackNack == True:
        payload1 = payload1 | 3
    else:
        payload1 = payload1 | 0

    payload2 = pckID
    payload = bytes([payload1]) + bytes([payload2])

    return payload

def splitAck(ack):

    ack = ack[0] << 8 | ack[1]

    maskSender = 0b1110000000000000
    maskReceiver = 0b0001110000000000
    maskAckNack = 0b0000001100000000
    maskPckSeqNum = 0b0000000011111111

    sender = (ack & maskSender) >> 13
    receiver = (ack & maskReceiver) >> 10
    ackNack = (ack & maskAckNack) >> 8
    pckSeqNum = ack & maskPckSeqNum

    return sender, receiver, ackNack, pckSeqNum

'''			
-----------------------------------------------------------------
|		|		  |			|		|		 |					|
|@Sender|Packet_ID|@Receiver|EoTFlag|HopCount|		 DATA		|	
|		|		  |			|		|		 |					|
-----------------------------------------------------------------
   3b		5b		  3b		1b		4b			 30B
'''
def getDataPayloadList(filePath, deviceID, nextHopID, hopCount):
    if(os.path.isfile(filePath)):
        payload_list = list()
        with open(filePath, 'rb') as f:
            size = len(f.read())
            f.seek(0)
            num_packets = math.ceil(size/30)
            count = 0
            while True:
                chunk = f.read(30)
                if chunk:
                    payload1 = deviceID << 5 | count
                    payload2 = nextHopID << 5
                    if count == num_packets-1:
                        payload2 = payload2 | 1 << 4
                    else:
                        payload2 = payload2 | 0 << 4

                    payload2 = payload2 | hopCount
                    data = chunk
                    payload = bytes([payload1]) + bytes([payload2]) + data
                    payload_list.append(payload)
                    count = count + 1

                else:
                    break
    else:
        print("ERROR: file does not exist in PATH: " + filePath)
    
    return payload_list

def splitPayload(payload):

    payloadHeader = payload[0] << 8 | payload[1]

    maskSender = 0b1110000000000000
    maskPckSeqNum = 0b0001111100000000
    maskReceiver = 0b0000000011100000
    maskEoT = 0b0000000000010000
    maskHopCount = 0b0000000000001111

    sender = (payloadHeader & maskSender) >> 13
    pckSeqNum = (payloadHeader & maskPckSeqNum) >> 8
    receiver = (payloadHeader & maskReceiver) >> 5
    eot = (payloadHeader & maskEoT) >> 4
    hopCount = payloadHeader & maskHopCount

    return sender, receiver, pckSeqNum, eot, hopCount

'''
--------------------------------
|       |         |            | 
|@Sender|@Receiver| 1111111111 |   
|       |         |            | 
--------------------------------
   3b       3b         10b       
'''
def getFinalPayload(deviceID, nextHopID):

    payload1 = deviceID << 5 | nextHopID << 2 | 3
    payload2 = 0xFF
    payload = bytes([payload1]) + bytes([payload2])
    return payload

def splitFinalPayload(payload):

    finalPayload = payload[0] << 8 | payload[1]
    

    maskSender = 0b1110000000000000
    maskReceiver = 0b0001110000000000
    maskPayload = 0b0000001111111111

    sender = (finalPayload & maskSender) >> 13
    receiver = (finalPayload & maskReceiver) >> 10
    payload = finalPayload & maskPayload

    return sender, receiver, payload



