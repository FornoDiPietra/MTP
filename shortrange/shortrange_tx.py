#!/usr/bin/python2

import RPi.GPIO as GPIO
GPIO.setmode(GPIO.BCM)
from lib_nrf24 import NRF24
import time, sys, argparse
import spidev
from lib_protocol_shortrange import *
import os

def _BV(x):
    return 1

def setupRadio(CE):
    CHANNEL = 0x70
    POWER = NRF24.PA_MAX
    #POWER = NRF24.PA_HIGH
    #POWER = NRF24.PA_LOW
    #POWER = NRF24.PA_MIN
    DATARATE = NRF24.BR_2MBPS

    radio = NRF24(GPIO, spidev.SpiDev())
    radio.begin(CE, 0)
    radio.setRetries(15,0)
    radio.setPayloadSize(32)
    radio.setChannel(CHANNEL)
    radio.setDataRate(DATARATE)
    radio.setPALevel(POWER)
    radio.setAutoAck(False)
    radio.write_register(NRF24.STATUS, 0x70)

    return radio

def transmit(radio, IRQ, data):
    txbuffer = [NRF24.W_TX_PAYLOAD] + data
    result =  radio.spidev.xfer2(txbuffer)

    #wait for successful sended
    while (GPIO.input(IRQ) == 1):
        time.sleep(0.0000001)
    radio.write_register(NRF24.STATUS, 0x70)

def receive(radio, IRQ, timeout):
    startTime = time.time()

    while (GPIO.input(IRQ) == 1 and (time.time()-startTime<timeout)):
        time.sleep(0.000001)

    if (GPIO.input(IRQ) == 0):
        radio.write_register(NRF24.STATUS, 0x70)

        txbuffer = [NRF24.R_RX_PAYLOAD] + ([0xFF]*32)
        payload = radio.spidev.xfer2(txbuffer)

        return payload[1:]
    else:
        return None


if (len(sys.argv) < 2):
    print("shortrange_tx.py <file> <config: cfg1|cfg2> <compress|nocompress>")
    sys.exit()

FILE_NAME = sys.argv[1]
config = "cfg1"
if (len(sys.argv)> 2):
    config = sys.argv[2]

compression = False
if (len(sys.argv) > 3):
	if (sys.argv[3] == "compress"):
		compression = True

# Normal configuration Raspi 2
ADDR_TX = [0xe7, 0xe7, 0xe7, 0xe7, 0xe7]
ADDR_RX = [0xc2, 0xc2, 0xc2, 0xc2, 0xc2]
ACK_TIMEOUT = 0.2


print("TX addr: " + str(ADDR_TX))
print("RX addr: " + str(ADDR_RX))	

if (config == "cfg1"):
    # CE=0/IRQ=25 belongs together
    # CE=1/IRQ=15
    CE_TX = 0
    CE_RX = 1
    IRQ_TX = 16
    IRQ_RX = 20

else:
    # Switch Rx/Tx
    CE_TX = 1
    CE_RX = 0
    IRQ_TX = 20
    IRQ_RX = 16


radioRx = setupRadio(CE_RX)
radioRx.openReadingPipe(1, ADDR_RX)
radioRx.openReadingPipe(0, ADDR_RX)
radioRx.startListening()


radioTx = setupRadio(CE_TX)
radioTx.startListening()
radioTx.stopListening()
time.sleep(130 / 1000000.0)

radioTx.openWritingPipe(ADDR_TX)

# setup the interrupts
GPIO.setup(IRQ_TX, GPIO.IN)
GPIO.setup(IRQ_RX, GPIO.IN)

print("CE_TX=" + str(CE_TX))
print("CE_RX=" + str(CE_RX))
print("IRQ_TX=" + str(IRQ_TX))
print("IRQ_RX=" + str(IRQ_RX))

print(sys.version)
print("----Tx---------")
radioTx.printDetails()
print("----Rx---------")
radioRx.printDetails()


print("init the packet stack")
stack = PacketStack()

if (compression):
	print("compressing file")
	os.system("gzip < " + FILE_NAME + " > tmp.gz")
	print("reading file compressed file tmp.gz")
	stack.readFromFile("tmp.gz",True)
else:
	print("reading file " + FILE_NAME)
	stack.readFromFile(FILE_NAME, False)

raw_input("press button to start")


# run this to swtich the radio on and into tx mode
radioTx.write_register(NRF24.CONFIG, (radioTx.read_register(NRF24.CONFIG) | _BV(NRF24.PWR_UP) ) & ~_BV(NRF24.PRIM_RX))
radioTx.flush_rx()
radioRx.flush_rx()

count = 0
ackLost = 0

timer1 = time.time()

stats = []

try:
    while (not stack.isAllConfirmed()):
    	timingStat = []
        count += 1

        timer2 = time.time()
        timer3 = time.time()

        burst = stack.createBurst()

        # How long did it take to create the burst?
        timingStat.append(time.time()-timer3) 	
        timer3 = time.time()

        for frame in burst:
            transmit(radioTx, IRQ_TX, frame.getRawData())

       	# How long did it take to transmit the burst
       	timingStat.append(time.time()-timer3)
        timer3 = time.time()

        radioRx.flush_rx()
        radioRx.write_register(NRF24.STATUS, 0x70)    #clear the interrupt

        #now wait for the ACK
        data = receive(radioRx, IRQ_RX, ACK_TIMEOUT)

        # How long did we wait for the ACK
        timingStat.append(time.time() - timer3)
        timer3 = time.time()

        ack_message = ""
        if (data != None):
            burst.ACK(data,stack)
        else:
            ack_message = " (ACK timeout)"
            fails+=1

       	print(str(stack._packetCount) + " packets left")

        # How long did it take to process the ACK
        timingStat.append(time.time()-timer3)
        # How long did the whole burst transmission take?
        timingStat.append(time.time()-timer2)
        timingStat.append(count)
        timingStat.append(fails)

        stats.append(timingStat)

except KeyboardInterrupt:
    print("")
finally:
    GPIO.cleanup()
    totalTime = time.time()-timer1
    print("time elapsed: " + str(totalTime))
    print("transmitted: " + str(count))
    print("timeouts: " + str(fails))
    print("saving logfile, don't cancel!")

    logFile = open(FILE_NAME + ".timelog")

    logFile.write(time.asctime( time.localtime(time.time())) + "\n")
    logFile.write("total time elapsed: " + str(totalTime) + "\n")
    logFile.write("---------------------------------------\n")

    # Write the timing statistics
    logFile.write("Burst_create;Burst_transmit;ACK_wait;Process_ACK;total;burst_count;ack_timeout_count\n")
    for timingStat in stats:
    	for datum in timingStat:
    		logFile.write(str(datum) + ";")
    	logFile.write("\n")
    logFile.close()