#!/usr/bin/python2

import RPi.GPIO as GPIO
GPIO.setmode(GPIO.BCM)
from lib_nrf24 import NRF24
import time
import spidev
import signal
import time
import sys


def fillWithPadding(byteBlock, blockSize):
    while (len(byteBlock) < blockSize):
        byteBlock = byteBlock + chr(0x00)
        
    return byteBlock

def readFile(fileName, blockSize):
    blocks = []

    with open(fileName, "rb") as f:
        byteBlock = f.read(blockSize)

        while byteBlock != b'':
            if (len(byteBlock) < blockSize):
                byteBlock = fillWithPadding(byteBlock, blockSize)
            
            blocks.append(byteBlock)
            byteBlock = f.read(blockSize)
        f.close()

    return blocks

def bytesToString(bytesObj):
    formattedString = ""
    for b in bytesObj:
        s = format(b, '02x')
        #s = format(b, '02d')
        formattedString += s.rjust(3)
    return formattedString

def handler (signum, frame):
    global counter
    global rxbuf
    global seqCounter

    # If an output file was specifiied, save the result
    if (outputFileName != ""):
        f = open("test_rx_data.csv","w")
        for s in seqCounter:
            f.write(str(s) + "\n")
        f.close()


    print("\n total received packets: " + str(counter))
    exit()


# MAIN
arglist = parseCommandLineArguments(sys.argv,["--out"])

outputFileName = ""
for a in arglist:
    if (a[0] == "--out" and len(a)>=2):
        outputFileName = a[1]


GPIO.setup(25, GPIO.IN)

blockSize = 32
############ setup the transceiver ##################################
radio = NRF24(GPIO, spidev.SpiDev())
radio.begin(0, 0)
#radio.begin(0, 0) # Set spi-cs pin0, and rf24-CE pin 17
time.sleep(0.5)
radio.setRetries(15,0)
radio.setPayloadSize(blockSize)
radio.setChannel(0x60)

radio.setDataRate(NRF24.BR_2MBPS)
radio.setPALevel(NRF24.PA_MIN)

radio.setAutoAck(False)
#radio.enableDynamicPayloads() # radio.setPayloadSize(32) for setting a fixed payload
#radio.enableAckPayload()

#radio.openWritingPipe([0xe7, 0xe7, 0xe7, 0xe7, 0xe7])
radio.openReadingPipe(1, [0xC2, 0xC2, 0xC2, 0xC2, 0xC2])
#radio.startListening()
#radio.stopListening()
radio.printDetails()
radio.startListening()


buf = "1"*32
counter=0
signal.signal(signal.SIGINT, handler)
radio.write_register(NRF24.STATUS, 0x70)
radio.flush_rx()

rxbuf = []
seqCounter = []
while True:
#    if radio.available([0]):
    available = GPIO.input(25)
    if (available ==0):
        radio.write_register(NRF24.STATUS, 0x70)
        buf = []
        counter+=1
        #radio.read(buf,32)
        txbuffer = [NRF24.R_RX_PAYLOAD] + ([0xFF]*32)
        payload = radio.spidev.xfer2(txbuffer)

        low = payload[-1]
        high = payload[-2]
        seqNumber=(high<<8 | low)
        seqCounter.append(seqNumber)

        #print(bytesToString(payload[1:]))
        #radio.print_status(radio.get_status())
        rxbuf.append(payload)
        if (counter % 500 ==0):
            print(counter)