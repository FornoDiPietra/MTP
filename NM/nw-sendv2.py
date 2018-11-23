#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# Network mode implementation of Team C based on Arnau E. QM for Team C
# Author: Albert Sanchez
# Date: 09/11/2018
# Version: 2.0

from lib_nrf24 import NRF24
import time
import spidev
import sys
import os
#import crc16
import RPi.GPIO as GPIO
import framesv2 as frames
import crc_utils

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

#Define Led 1
deviceLed1 = 26
GPIO.setup(deviceLed1, GPIO.OUT)

#Define LED
deviceLed2 = 21
GPIO.setup(deviceLed2, GPIO.OUT)

#Define Button
deviceButton = 6
GPIO.setup(deviceButton, GPIO.IN)

#Define device address
deviceAddresPin = 2
GPIO.setup(deviceAddresPin, GPIO.IN)

#GLOBAL VARIABLES
MAX_DATA_ATTEMPTS = 30
MAX_GOODBYE_ATTEMPTS = 10
GOODBYE_TIMER = 1
GOODBYE_TIMER_RECEIVER = 20

filePath = '/home/pi/MTP/NM/nw-file.txt'

SENDER_REPEATER_CHANNEL = 0x60
REPEATER_SENDER_CHANNEL = 0x70


# Define the pipes that will be used to send the data from one transceiver to the other
pipes = [[0xe7, 0xe7, 0xe7, 0xe7, 0xe7], [0xc2, 0xc2, 0xc2, 0xc2, 0xc2]]

def transmitData(sender, receiver, deviceID, nextHopID, hopCount):

    transmissionFinished = False

    while not transmissionFinished:
        print('starting transmission from ' + str(deviceID) + 'to ' + str(nextHopID))
        dataTransmitted = transmissionData(sender, receiver, deviceID, nextHopID, hopCount)

        while not dataTransmitted:
            currentNextHopID = nextHopID
            nextHopID = getNextHopID(currentNextHopID)
            hopCount += 1
            dataTransmitted = transmissionData(sender, receiver, deviceID, nextHopID, hopCount)

def receiveData(sender, receiver, deviceID):
    payload_list = list()
    
    receiver.startListening()

    out = False
    actual_ack = None
    timeout_bye = 0
    while (out == False) and (timeout_bye < GOODBYE_TIMER_RECEIVER):
        print ('antes de wait for data')
        wait_for_data(receiver)

        print ('RX: Something received')
        # recv_buffer is the array where received data will be placed
        recv_buffer = []
        receiver.read(recv_buffer, receiver.getDynamicPayloadSize())
        srcAddr, dstAddr, pckSeqNum, eot, hopCount = frames.splitPayload(recv_buffer)
        print (str(srcAddr) + str(dstAddr) + str(pckSeqNum) + str(eot) + str(hopCount))
        data = recv_buffer[1:]
        if (dstAddr == deviceID):
            if (actual_ack != pckSeqNum) and (eot != 1):
                send_packet(sender, frames.getAck(deviceID, srcAddr, pckSeqNum, True))
                payload_list.append(bytes(data))
                actual_ack = pckSeqNum

            elif (actual_ack == pckSeqNum) and (eot != 1):
                send_packet(sender, frames.getAck(deviceID, srcAddr, pckSeqNum, True))

            elif (actual_ack != pckSeqNum) and (eot == 1):
                send_packet(sender, frames.getAck(deviceID, srcAddr, pckSeqNum, True))
                payload_list.append(bytes(data))
                actual_ack = pckSeqNum

                wait_for_data(receiver)
                lastPacket = []
                receiver.read(lastPacket, receiver.getDynamicPayloadSize())
                tx, rx, payload = frames.splitFinalPayload(lastPacket)
                if (rx == deviceID) and (payload == 2047):
                    out = True
                else:
                    time.sleep(1)
                    timeout_bye += 1
                
    write_file(filePath, payload_list)

def transmissionData(sender, receiver, deviceID, nextHopID, hopCount):
        
    count = 0
    attempts = 0
    dataTransmitted = False
    seconds = 0
    fail = 0

    payload_list = frames.getDataPayloadList(filePath, deviceID, nextHopID, hopCount)

    while count < len(payload_list):
        # send a packet to receiver
        acknowledged = False
        while ((not acknowledged) and attempts < MAX_DATA_ATTEMPTS):
            send_packet(sender, payload_list[count])
            print("Sent payload number: " + str(count))

            # If it is the last packet, we set the Goodbye timer
            if count != len(payload_list)-1:
                
                # Did we get an ACK back?
                ack_or_timeout(receiver)
                
                if receiver.available(pipes[0]):
                    print ('TX: something received')
                    recv_buffer = []
                    receiver.read(recv_buffer, receiver.getDynamicPayloadSize())
                    ackPayload = bytes(recv_buffer)

                    srcAddr, dstAddr, ackNack, pckSeqNum =  frames.splitAck(ackPayload)

                    if (srcAddr == nextHopID) and (dstAddr == deviceID) and (ackNack == 3) and (pckSeqNum == count):
                        print ('ACK ' + str(pckSeqNum) + 'received')
                        acknowledged = True
                        count += 1
                        attempts = 0
                    else:
                        attempts += 1
                else:
                        attempts += 1

            else:
                while (fail < MAX_GOODBYE_ATTEMPTS):   
                    while (seconds < GOODBYE_TIMER):
                        time.sleep(0.1)
                        if receiver.available(pipes[0]):
                            recv_buffer = []
                            receiver.read(recv_buffer, receiver.getDynamicPayloadSize())
                            ackPayload = bytes(recv_buffer)

                            srcAddr, dstAddr, ackNack, pckSeqNum =  frames.splitAck(ackPayload)
                            if (srcAddr == nextHopID) and (dstAddr == deviceID) and (ackNack == 3) and (pckSeqNum == count):
                                goodbyePck = frames.getFinalPayload(deviceID, nextHopID)
                                send_packet(sender, goodbyePck)
                                dataTransmitted = True
                                break
                        seconds = seconds + 0.1

                    if (dataTransmitted == True):
                        break    

                    fail += 1

        if (attempts == MAX_DATA_ATTEMPTS - 1) or (fail == MAX_GOODBYE_ATTEMPTS -1):
            dataTransmitted = False
            break

    return dataTransmitted

def getDeviceID():
    #It returns the device ID 
    '''
    if GPIO.input(deviceAddresPin) == 0:
        deviceID = 2
    else:
        deviceID = 6
    '''
    deviceID = sys.argv[1]
    return int(deviceID)

def getNextHopID(inputAddr):
    #It returns the device ID for the next hop 
    inputAddr = (int(inputAddr) + 1) % 8

    return inputAddr

def initialize_radios(csn, ce, channel):
    #This function initializes the radios, each
    #radio being the NRF24 transceivers.
    
    #It gets 3 arguments, csn = Chip Select, ce = Chip Enable
    #and the channel that will be used to transmit or receive the data.

    radio = NRF24(GPIO, spidev.SpiDev())
    radio.begin(csn, ce)
    time.sleep(2)
    radio.setRetries(15,15)
    radio.setPayloadSize(32)
    radio.setChannel(channel)

    radio.setDataRate(NRF24.BR_250KBPS)
    radio.setPALevel(NRF24.PA_HIGH) # TODO check if this is max allowed power
    radio.setAutoAck(False)
    radio.enableDynamicPayloads()
    radio.enableAckPayload()

    return radio

def send_packet(sender, payload):
    # Send the packet thorugh the sender radio. 
    sender.write(payload)

def ack_or_timeout(receiver):
    # This is a blocking function that waits until
    # data has been received or until the defined timeout has passed.

    timeout_starts = time.time() 
    while (not receiver.available(pipes[0]) and (time.time() - timeout_starts) < 0.01):
        time.sleep(0.01)

def wait_for_data(receiver):
    # This is a blocking function that waits
    # until data is available in the receiver pipe. '''

    while not receiver.available(pipes[1]):
            time.sleep(0.01)

def write_file(file_path, payload_list):
    # This function gets the data from the variable payload_list, 
    #iterates through it and saves it to the file you have provided 
    # in the arguments. 
    
    # Warning: If the size of the payload_list is greater than the size
    #of the RAM memory this script will fail.'''

    with open(file_path, "wb") as f:
        count = 0
        while count < len(payload_list):
            f.write(payload_list[count])
            count = count + 1

def main_Source():

    print('Start main_source')

    # Each group should set the correct pin numbers (25, 16)
    sender = initialize_radios (0, 25, SENDER_REPEATER_CHANNEL)
    receiver = initialize_radios (1, 16, REPEATER_SENDER_CHANNEL)

    sender.openWritingPipe(pipes[1])
    receiver.openReadingPipe(0, pipes[0])

    receiver.startListening()

    deviceID = getDeviceID()
    nextHopID = getNextHopID(deviceID)

    hopCount = 1
    
    transmitData(sender, receiver, deviceID, nextHopID, hopCount)
        
def main_Repeater():
    print('Start main_repeater')

    sender = initialize_radios(1, 16, REPEATER_SENDER_CHANNEL)
    receiver = initialize_radios(0, 25, SENDER_REPEATER_CHANNEL)

    sender.openWritingPipe(pipes[0])
    receiver.openReadingPipe(0, pipes[1])

    receiver.startListening()

    deviceID = getDeviceID()

    receiveData(sender, receiver, deviceID)

    receiver.stopListening()
    receiver.closeReadingPipe(pipes[1])

    sender = initialize_radios (0, 25, SENDER_REPEATER_CHANNEL)
    receiver = initialize_radios (1, 16, REPEATER_SENDER_CHANNEL)

    sender.openWritingPipe(pipes[1])
    receiver.openReadingPipe(0, pipes[0])

    receiver.startListening()

    nextHopID = getNextHopID(deviceID)

    transmitData(sender, receiver, deviceID, nextHopID)

if __name__ == '__main__':
    if os.path.isfile(filePath) == True:
        main_Source()
    else:
        main_Repeater()
