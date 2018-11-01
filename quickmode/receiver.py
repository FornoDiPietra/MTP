#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Example program to receive packets from the radio link
#

import RPi.GPIO as GPIO
GPIO.setmode(GPIO.BCM)
from lib_nrf24 import NRF24
import time
import spidev
import sys


pipes = [[0xe7, 0xe7, 0xe7, 0xe7, 0xe7], [0xc2, 0xc2, 0xc2, 0xc2, 0xc2]]

radio2 = NRF24(GPIO, spidev.SpiDev())
radio2.begin(0, 17)

radio2.setRetries(15,0)

radio2.setPayloadSize(32)
radio2.setChannel(0x60)
radio2.setDataRate(NRF24.BR_2MBPS)
radio2.setPALevel(NRF24.PA_MIN)

radio2.setAutoAck(False)
radio2.enableDynamicPayloads()
radio2.enableAckPayload()

radio2.openWritingPipe(pipes[0])
radio2.openReadingPipe(1, pipes[1])

radio2.startListening()
radio2.stopListening()

radio2.printDetails()

radio2.startListening()


packet_id = []
packets_received = 0
packet_completed = True
packet_data = []
next_packet = 0
counter = 0

f = open("hola.txt", "w")

while packet_completed:
    pipe = [0]
    while not radio2.available(pipe):
        time.sleep(10000/1000000.0)

    recv_buffer = []
    packet_size = radio2.getDynamicPayloadSize()
    radio2.read(recv_buffer, packet_size)
    if packets_received == 0:
        packet_id = [0] * recv_buffer[1]
    if recv_buffer[0] == next_packet:
        print("Received packet: "),
        print(recv_buffer[0])
        f.write(bytearray(recv_buffer[2:packet_size]))
        packets_received = packets_received + 1
        next_packet = next_packet + 1
    if packets_received == recv_buffer[1]:
        print("File completed!")
        packet_completed = False
    counter = counter + 1
    if counter == 10000000000000000000000:
        f.close()
        sys.exit()

#for readed_packet in packet_data:
    #f.write(bytearray(readed_packet))

f.close()
