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

def parseCommandLineArguments(argv, validArgs):
    newArg = []
    arglist = []
    for a in argv[1:]:
        if (a in validArgs):
            arglist.append(newArg)
            newArg = []
            newArg.append(a)
        else:
            newArg.append(a)

    arglist.append(newArg)
    del arglist[0]
    return arglist

def handler (signum, frame):
    global counter
    global rxbuf
    global seqCounter
    global status

    # If an output file was specifiied, save the result
    if (outputFileName != ""):
        f = open(outputFileName,"w")
        for s in seqCounter:
            f.write(str(s) + "\n")
        f.close()


    print("\n total received packets: " + str(counter))
    exit()


# MAIN


args = parseCommandLineArguments(sys.argv,["--power","--channel","--datarate","--out"])

CHANNEL = 0x60
POWER = NRF24.PA_MAX
#POWER = NRF24.PA_HIGH
#POWER = NRF24.PA_LOW
#POWER = NRF24.PA_MIN

testPacket = [0x00]*32
#testPacket = [0xFF]*32
#testPacket = [0xAA]*32

DATARATE = NRF24.BR_2MBPS

outputFileName = ""

for a in args:

    if (a[0] == "--out" and len(a)>=2):
        outputFileName = a[1]

    if (a[0] == "--power" and len(a) >= 2):
        if a[1] == "max":
            POWER = NRF24.PA_MAX
        elif a[1] == "high":
            POWER = NRF24.PA_HIGH
        elif a[1] == "low":
            POWER = NRF24.PA_LOW
        elif a[1] == "min":
            POWER = NRF24.PA_MIN

    if (a[0] == "--channel" and len(a) >= 2):
        CHANNEL = int(a[1])

    if (a[0] == "--packettype" and len(a) >= 2):
        if (a[1] == "00"):
            testPacket = [0x00]*32
        elif (a[1] == "11"):
            testPacket = [0xFF]*32
        elif (a[1] == "01"):
            testPacket = [0xAA]*32

    if (a[0] == "--packetnum" and len(a) >= 2):
        numOfPackets = int(a[1])

    if (a[0] == "--datarate" and len(a) >= 2):
        if (a[1] == "2Mbps"):
            DATARATE = NRF24.BR_2MBPS
        if (a[1] == "1Mbps"):
            DATARATE = NRF24.BR_1MBPS
        if (a[1] == "250Kbps"):
            DATARATE = NRF24.BR_250KBPS

    if (a[0] == "--sleeptime" and len(a) >= 2):
        SLEEPTIME = float(a[1])





GPIO.setup(25, GPIO.IN)

blockSize = 32
############ setup the transceiver ##################################
radio = NRF24(GPIO, spidev.SpiDev())
radio.begin(0, 0)
#radio.begin(0, 0) # Set spi-cs pin0, and rf24-CE pin 17
time.sleep(0.5)
radio.setRetries(15,0)
radio.setPayloadSize(blockSize)
radio.setChannel(CHANNEL)

radio.setDataRate(DATARATE)
radio.setPALevel(POWER)

radio.setAutoAck(False)
#radio.enableDynamicPayloads() # radio.setPayloadSize(32) for setting a fixed payload
#radio.enableAckPayload()

#radio.openWritingPipe([0xe7, 0xe7, 0xe7, 0xe7, 0xe7])
radio.openReadingPipe(1, [0xC2, 0xC2, 0xC2, 0xC2, 0xC2])
radio.printDetails()
radio.startListening()


buf = "1"*32
counter=0
signal.signal(signal.SIGINT, handler)
radio.write_register(NRF24.STATUS, 0x70)
radio.flush_rx()

rxbuf = []
seqCounter = []
status = radio.get_status()
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