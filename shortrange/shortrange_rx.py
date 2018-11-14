#!/usr/bin/python2

import RPi.GPIO as GPIO
GPIO.setmode(GPIO.BCM)
from lib_nrf24 import NRF24
import time
import spidev
import signal
import time
import sys

from lib_protocol_shortrange import *

def _BV(x):
    return 1 << x

def configureRadio(ce):
    radio = NRF24(GPIO, spidev.SpiDev())
    radio.begin(ce, 0) # Chip select 0
    radio.setRetries(15,0)
    radio.setPayloadSize(32)
    radio.setChannel(0x60)
    radio.setDataRate(NRF24.BR_2MBPS)
    radio.setPALevel(NRF24.PA_LOW)
    radio.setAutoAck(False)

    return radio

def listenOnAddress(radio, addr):
    radio.openReadingPipe(1, addr)
    radio.startListening()

def transmitOnAddress(radio, addr):
    radio.startListening()
    radio.stopListening()
    radio.openWritingPipe(addr)
    radio.write_register(NRF24.CONFIG, (radio.read_register(NRF24.CONFIG) | _BV(NRF24.PWR_UP) ) & ~_BV(NRF24.PRIM_RX))

def waitForPacket(radio,irqPin,timeOut):
    #wait for the Rx to get the interrupt
    startTime = time.time()
    while (GPIO.input(irqPin) == 1 and (time.time()-startTime < timeOut)):
        time.sleep(0.0000001)

    if (GPIO.input(irqPin) == 0):
        #clear the interrupt
        radio.write_register(NRF24.STATUS, 0x70)

        # read the data
        txbuffer = [NRF24.R_RX_PAYLOAD] + ([0xFF]*32)
        payload = radio.spidev.xfer2(txbuffer)

        return payload[1:]
    else:
        #timeout
        return None

def transmitPacket(radio,irqPin, data):
    #create and send a test packet
    txbuffer = [NRF24.W_TX_PAYLOAD] + data
    result =  radio.spidev.xfer2(txbuffer)

    #wait for successful sended
    while (GPIO.input(irqPin) == 1):
        time.sleep(0.0000001)
    #clear the IRQ
    radio.write_register(NRF24.STATUS, 0x70)

# MAIN

if (len(sys.argv) < 2):
    print("specify output file name")
    sys.exit()
RCV_FILE_NAME = sys.argv[1]

IRQ_TX = 25
IRQ_RX = 15
CE_TX = 0
CE_RX = 1

GPIO.setup(IRQ_TX, GPIO.IN) #Tx IRQ
GPIO.setup(IRQ_RX, GPIO.IN) #Rx IRQ

#config selftest
#ADDR_TX = [0xc2, 0xc2, 0xc2, 0xc2, 0xc2]
#ADDR_RX = [0xc2, 0xc2, 0xc2, 0xc2, 0xc2]

#config raspi 3
#ADDR_TX = [0xE7, 0xE7, 0xE7, 0xE7, 0xE7]
#ADDR_RX = [0xc2, 0xc2, 0xc2, 0xc2, 0xc2]

#config raspi 2
ADDR_TX = [0xc2, 0xc2, 0xc2, 0xc2, 0xc2]
ADDR_RX = [0xE7, 0xE7, 0xE7, 0xE7, 0xE7]

radioTx = configureRadio(CE_TX)
radioRx = configureRadio(CE_RX)

listenOnAddress(radioRx, ADDR_RX)
transmitOnAddress(radioTx, ADDR_TX)

print("init packet stack")
stack = PacketStack()

veryFirstPacket = True

info_receivedBurstNum = 0
timer1=0
print("ready")

while True:

    burst = RxBurst()

    timeOut = 100000
    if (stack.isCompletlyReceived()):
        timeOut = 2

    rxData = waitForPacket(radioRx,IRQ_RX,timeOut)
    if (rxData != None):
        rxFrame = RxFrame(rxData)
        burst.addFrame(rxFrame)
    else:
        exit()


    while True:
        rxData = waitForPacket(radioRx,IRQ_RX,burst.getTimeOut())
        if (rxData != None):
            rxFrame = RxFrame(rxData)
            burst.addFrame(rxFrame)

        else:
            break

    radioRx.flush_rx()
    radioTx.flush_tx()

    info_receivedBurstNum += 1
    
    stack.addBurst(burst)
    transmitPacket(radioTx,IRQ_TX, burst.getACK() )

    if (stack.isCompletlyReceived()):
        print("file completly received")
        stack.writeToFile(RCV_FILE_NAME)