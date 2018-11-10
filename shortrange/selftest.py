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

# MAIN

IRQ_TX = 25
IRQ_RX = 15
GPIO.setup(IRQ_TX, GPIO.IN) #Tx IRQ
GPIO.setup(IRQ_RX, GPIO.IN) #Rx IRQ

ADDR_TX = [0xc2, 0xc2, 0xc2, 0xc2, 0xc2]
ADDR_RX = [0xC2, 0xC2, 0xC2, 0xC2, 0xC2]
#ADDR_RX = [0xE7, 0xE7, 0xE7, 0xE7, 0xE7]

radioRx = NRF24(GPIO, spidev.SpiDev())
radioRx.begin(1, 0) # Chip select 0
radioRx.setRetries(15,0)
radioRx.setPayloadSize(32)
radioRx.setChannel(0x60)
radioRx.setDataRate(NRF24.BR_2MBPS)
radioRx.setPALevel(NRF24.PA_LOW)
radioRx.setAutoAck(False)
radioRx.openReadingPipe(1, ADDR_RX)
#radioRx.printDetails()
radioRx.startListening()


radioTx = NRF24(GPIO, spidev.SpiDev())
radioTx.begin(0, 17)
radioTx.setRetries(15,0)
radioTx.setPayloadSize(32)
radioTx.setChannel(0x60)
radioTx.setDataRate(NRF24.BR_2MBPS)
radioTx.setPALevel(NRF24.PA_LOW)
radioTx.setAutoAck(False)
radioTx.openWritingPipe(ADDR_TX)



# Transmit something using the Tx

#Startup the transmitter
radioTx.write_register(NRF24.CONFIG, (radioTx.read_register(NRF24.CONFIG) | _BV(NRF24.PWR_UP) ) & ~_BV(NRF24.PRIM_RX))


while True:
    #clear the Rx FIFO so we are ready to receive new packets
    radioRx.flush_rx()

    #create and send a test packet
    testPacket = [0xFF]*32
    txbuffer = [NRF24.W_TX_PAYLOAD] + testPacket
    result =  radioTx.spidev.xfer2(txbuffer)

    #wait for successful sended
    while (GPIO.input(IRQ_TX) == 1):
        time.sleep(0.0000001)
    #clear the IRQ
    radioTx.write_register(NRF24.STATUS, 0x70)

    print("transmitting done")

    #wait for the Rx to get the interrupt
    while (GPIO.input(IRQ_RX) == 1):
        time.sleep(0.0000001)
    #clear the interrupt
    radioRx.write_register(NRF24.STATUS, 0x70)

    # read the data
    txbuffer = [NRF24.R_RX_PAYLOAD] + ([0xFF]*32)
    payload = radioRx.spidev.xfer2(txbuffer)

    print("received:")
    print(payload[1:])

    time.sleep(0.5)
