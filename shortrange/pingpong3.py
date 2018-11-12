#!/usr/bin/python2

import RPi.GPIO as GPIO
GPIO.setmode(GPIO.BCM)
from lib_nrf24 import NRF24
import time
import spidev
import signal
import time
import sys

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
    radio.openReadingPipe(0, addr)
    radio.startListening()

def transmitOnAddress(radio, addr):
    radio.openWritingPipe(addr)
    radio.write_register(NRF24.CONFIG, (radio.read_register(NRF24.CONFIG) | _BV(NRF24.PWR_UP) ) & ~_BV(NRF24.PRIM_RX))

def waitForPacket(radio,irqPin):
    startTime = time.time()
    timeOut = 5
    #wait for the Rx to get the interrupt
    while (GPIO.input(irqPin) == 1 and (time.time()-startTime)<timeOut):
        time.sleep(0.0000001)

    if (GPIO.input(irqPin) == 0):
        #clear the interrupt
        radio.write_register(NRF24.STATUS, 0x70)

        # read the data
        txbuffer = [NRF24.R_RX_PAYLOAD] + ([0xFF]*32)
        payload = radio.spidev.xfer2(txbuffer)

        print("received:")
        print(payload[1:])
    else:
        print("timeOut")

def transmitPacket(radio,irqPin):
    #create and send a test packet
    testPacket = []
    for i in range(0,32):
        testPacket.append(i)
        
    txbuffer = [NRF24.W_TX_PAYLOAD] + testPacket
    result =  radio.spidev.xfer2(txbuffer)

    #wait for successful sended
    while (GPIO.input(irqPin) == 1):
        time.sleep(0.0000001)
    #clear the IRQ
    radio.write_register(NRF24.STATUS, 0x70)

    print("transmitting done")

# MAIN

IRQ_TX = 15
IRQ_RX = 25
CE_TX = 1
CE_RX = 0

GPIO.setup(IRQ_TX, GPIO.IN) #Tx IRQ
GPIO.setup(IRQ_RX, GPIO.IN) #Rx IRQ

#config self test
#ADDR_TX = [0xc2, 0xc2, 0xc2, 0xc2, 0xc2]
#ADDR_RX = [0xc2, 0xc2, 0xc2, 0xc2, 0xc2]

#config raspi 3
ADDR_TX = [0xE7, 0xE7, 0xE7, 0xE7, 0xE7]
ADDR_RX = [0xc2, 0xc2, 0xc2, 0xc2, 0xc2]

#config raspi 2
#ADDR_TX = [0xc2, 0xc2, 0xc2, 0xc2, 0xc2]
#ADDR_RX = [0xE7, 0xE7, 0xE7, 0xE7, 0xE7]

radioTx = configureRadio(CE_TX)
radioRx = configureRadio(CE_RX)

listenOnAddress(radioRx, ADDR_RX)
transmitOnAddress(radioTx, ADDR_TX)




while True:

    #clear the Rx FIFO so we are ready to receive new packets
    radioRx.flush_rx()

    transmitPacket(radioTx,IRQ_TX)

    waitForPacket(radioRx,IRQ_RX)

    time.sleep(0.5)
