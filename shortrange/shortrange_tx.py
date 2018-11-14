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
        txbuffer = [NRF24.R_RX_PAYLOAD] + ([0xff]*32)
        payload = radio.spidev.xfer2(txbuffer)
        #print(payload)
        return payload[1:]
    else:
        #timeout
        print("timeout")
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
    print("specify tx file name")
    sys.exit()
TX_FILE_NAME = argv[1]

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


print("init packet stack")
stack = PacketStack()
stack.readFromFile(TX_FILE_NAME)

print("packets in stack: " + str(stack._packetCount))


info_burstNum = 0
info_ackLost = 0
timer1=time.time()
timer3=time.time()

totalTimeBurst = 0
totalTimeAckWaiting = 0
totalTimeWaitingForNextBurst = 0

print("start transmission")

try:
    while (not stack.isAllConfirmed() ):

        if (info_burstNum % 20 == 0):
            print(str(stack._packetCount) + "/" + )

        burst = stack.createBurst()
        radioRx.flush_rx()

        totalTimeWaitingForNextBurst+=time.time()-timer3
        timer2=time.time()

        for frame in burst:
            transmitPacket(radioTx,IRQ_TX,frame.getRawData())

        timeBurst=time.time()-timer2
        totalTimeBurst+=timeBurst

        info_burstNum += 1

        radioTx.flush_tx()
        radioRx.flush_rx()

        timer3 = time.time()
        
        rxData = waitForPacket(radioRx,IRQ_RX,0.5)

        totalTimeAckWaiting+=time.time()-timer3
        timer4=0

        if (rxData != None):
            burst.ACK(rxData)
        else:
            info_ackLost += 1
except KeyboardInterrupt:
    print("")
finally:
    print("transmission done")
    print("number of bursts: " + str(info_burstNum))
    print("number of lost ACKS: " + str(info_ackLost))
    print("time elapsed: " + str(time.time()-timer1))
    print("average time per burst: " + str(totalTimeBurst/info_burstNum))
    print("average time to wait for ACK: " + str(totalTimeAckWaiting/info_burstNum))
    print("average time to create next burst: " + str(totalTimeWaitingForNextBurst/info_burstNum))