#!/usr/bin/python2

import RPi.GPIO as GPIO
GPIO.setmode(GPIO.BCM)
from lib_nrf24 import NRF24
import time, sys, argparse
import spidev

def _BV(x):
    return 1 << x

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
            
            blocks.append(  byteBlock ) 
            byteBlock = f.read(blockSize)
        f.close()

    return blocks

def bytesToString(bytesObj):
    formattedString = ""
    for b in bytesObj:
        s = format(b, '02b')
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

def handler(signum, frame):
    global counter
    print(coutner)
    exit()


args = parseCommandLineArguments(sys.argv,["--power","--channel","--packettype","--packetnum","--datarate","--sleeptime"])

CHANNEL = 0x60
POWER = NRF24.PA_MAX
#POWER = NRF24.PA_HIGH
#POWER = NRF24.PA_LOW
#POWER = NRF24.PA_MIN

testPacket = [0x00]*32
#testPacket = [0xFF]*32
#testPacket = [0xAA]*32

numOfPackets = 50000

DATARATE = NRF24.BR_2MBPS
SLEEPTIME = 0

for a in args:

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


print("packetdata:\n" + (bytesToString(testPacket)))
print("sleeptime:" + str(SLEEPTIME))

blockSize = 32

pipes = [[0xe7, 0xe7, 0xe7, 0xe7, 0xe7], [0xc2, 0xc2, 0xc2, 0xc2, 0xc2]]

radio = NRF24(GPIO, spidev.SpiDev())
radio.begin(0, 17)
time.sleep(1)
radio.setRetries(15,0)
radio.setPayloadSize(blockSize)
radio.setChannel(CHANNEL)

radio.setDataRate(DATARATE)
radio.setPALevel(POWER)
radio.setAutoAck(False)
#radio.enableDynamicPayloads()
#radio.enableAckPayload()


radio.openWritingPipe(pipes[1])

# ######################################################################

# radio.write_register(0x00,0b00001110)   #transmitter
# radio.write_register(0x01,0b00000000)   # disable auto ACK for any pipe
# radio.write_register(0x02,0b00000001)   # disable all pipes except for pipe 0
# radio.write_register(0x03,0b00000001)   # 3 bytes addresses
# radio.write_register(0x04,0b00000000)   # disable retransmissions
# radio.write_register(0x05,0x60)
# radio.write_register(0x06,0b00000110)   # maximum output power
# #radio.write_register(0x07,)
# radio.write_register(0x0A,[0xE7, 0xE7, 0xE7],3)
# #print(radio.read_register(0x0A,5))
# radio.write_register(0x10,[0xE7, 0xE7, 0xE7],3)
# radio.write_register(0x11,32)

#radio.print_status(radio.get_status())



GPIO.setup(25, GPIO.IN)
radio.write_register(NRF24.STATUS, 0x70)
print(GPIO.input(25))

#oldVal=0
#while True:
#    val = GPIO.input(25)
#    if (val != oldVal):
#        print("change  detected")
#        oldVal = val


## Read the file
print(sys.version)
radio.printDetails()

raw_input("press button to start test")

#testPacket = [0x00]*32
startTime = time.time()
counter = 0

# run this to swtich the radio on and into tx mode
radio.write_register(NRF24.CONFIG, (radio.read_register(NRF24.CONFIG) | _BV(NRF24.PWR_UP) ) & ~_BV(NRF24.PRIM_RX))
radio.flush_rx()

while True:

    low = counter & 0xFF
    high = counter>>8 & 0xFF

    testPacket[31] = low
    testPacket[30] = high


    #radio.write( testPacket )
    txbuffer = [NRF24.W_TX_PAYLOAD] + testPacket
    result =  radio.spidev.xfer2(txbuffer)

    # 0.0014 apeared to be close to the limit
    #time.sleep(0.0014)

    # with this we will loose about 50 out of 10k packets
    #time.sleep(0.00005)

    time.sleep(SLEEPTIME)

    #wait for successful sended
    while (GPIO.input(25) == 1):
        time.sleep(0.0000001)
    radio.write_register(NRF24.STATUS, 0x70)

    #print("tx: " + bytesToString(testPacket))

    #time.sleep(0.0001)
    #sent = GPIO.input(25)
    #print(sent)
    #radio.print_status(radio.get_status())
    #radio.write_register(NRF24.STATUS, 0x70)
    #sent = GPIO.input(25)
    #print(sent)

    counter+=1

    if (counter >= numOfPackets):
        break

    if (counter % 500 == 0):
        print(counter)

elapsedTime = time.time()-startTime;
print("transmitted " + str(numOfPackets) + " packets")
print("Time elapsed " + str(elapsedTime))
print("Time per packet in ms: " + str(elapsedTime*1000/float(numOfPackets)))