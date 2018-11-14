#!/usr/bin/python2

import RPi.GPIO as GPIO
GPIO.setmode(GPIO.BCM)
from lib_nrf24 import NRF24
import time, sys, argparse
import spidev

def _BV(x):
    return 1

def setupRadio(CE):
    CHANNEL = 0x60
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
    print("pingping.py <filename> <config:cfg1|cfg2> <textout|notextout>")
    sys.exit()

FILE_NAME = sys.argv[1]
if (len(sys.argv) > 2):
    config = sys.argv[2]
else:
    config = "cfg1"

textout = True


# Normal configuration Raspi 2
ADDR_TX = [0xe7, 0xe7, 0xe7, 0xe7, 0xe7]
ADDR_RX = [0xc2, 0xc2, 0xc2, 0xc2, 0xc2]
testPacket = []
for i in range(0,32):
    testPacket.append(i)



print("TX addr: " + str(ADDR_TX))
print("RX addr: " + str(ADDR_RX))

if (config == "cfg1"):
    # CE=0/IRQ=25 belongs together
    # CE=1/IRQ=15
    CE_TX = 0
    CE_RX = 1
    IRQ_TX = 25
    IRQ_RX = 15

else:
    # Switch Rx/Tx
    CE_TX = 1
    CE_RX = 0
    IRQ_TX = 15
    IRQ_RX = 25


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

raw_input("press button to start test")


# run this to swtich the radio on and into tx mode
radioTx.write_register(NRF24.CONFIG, (radioTx.read_register(NRF24.CONFIG) | _BV(NRF24.PWR_UP) ) & ~_BV(NRF24.PRIM_RX))
radioTx.flush_rx()
radioRx.flush_rx()

maxTries = 50000
count = 0
fails = 0

file = open(FILE_NAME, 'rb')
end=False

timer1 = time.time()
try:
    while (not end):
        count += 1

        #print("new packet")

        if (count % 20 == 0):
            print(str(count) + "/" + str(time.time()-timer1))

        header = [0]
        data = file.read(31)
        dataTx = []

        for d in data:
            dataTx.append(ord(d))

        if (len(dataTx) != 31):
            #last transmission
            #add padding and fix header
            end=True
            headerData = 31-len(data)
            header = [headerData]
            while (len(dataTx) < 31):
                dataTx.append(0x00)

        #retransmit until we have an ACK
        while True:

            #print(dataTx)
            transmit(radioTx, IRQ_TX, header + dataTx)

            data = receive(radioRx, IRQ_RX, 0.1)

            if (data != None):
                #print("got ACK")
                break
            else:
                if (textout):
                    print("timeout")
                fails+=1

        #raw_input("press a button")

except KeyboardInterrupt:
    print("")
finally:
    GPIO.cleanup()
    print("time elapsed: " + str(time.time()-timer1))
    print("transmitted: " + str(count))
    print("timeouts: " + str(fails))
