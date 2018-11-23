import RPi.GPIO as GPIO
GPIO.setmode(GPIO.BCM)
from lib_nrf24 import NRF24
import time, sys, os
import spidev
from lib_protocol_shortrange import *
from threading import Thread, Event, Lock
import Queue

class Shortrange(Thread):

    def __init__(self, eventPipe, msgPipe):
        super(Shortrange, self).__init__()

        self.CHANNEL = 0x70
        self.POWER = NRF24.PA_MAX
        #POWER = NRF24.PA_HIGH
        #POWER = NRF24.PA_LOW
        #POWER = NRF24.PA_MIN
        self.DATARATE = NRF24.BR_2MBPS

        self.ADDR_TX = [0xe7, 0xe7, 0xe7, 0xe7, 0xe7]
        self.ADDR_RX = [0xc2, 0xc2, 0xc2, 0xc2, 0xc2]
        self.ACK_TIMEOUT = 0.2

        self.CE_TX = 0
        self.CE_RX = 1
        self.IRQ_TX = 16
        self.IRQ_RX = 20

        self.COMPRESSION = False
        self.FILE_NAME = ""
        self.stack = None

        self.daemon = True
        self.events = Queue.Queue()
        self.emitEvents = eventPipe
        self.msgPipe = msgPipe

    def kill(self):
        self.events.put(['KILL',None])

    def loadFile(self, fileName):
        self.events.put(['FILE',fileName])

    def startOperation(self):
        self.events.put(['START',None])

    def _BV(sefl,x):
        return 1

    def setupRadio(self,CE):
        radio = NRF24(GPIO, spidev.SpiDev())
        radio.begin(CE, 0)
        radio.setRetries(15,0)
        radio.setPayloadSize(32)
        radio.setChannel(self.CHANNEL)
        radio.setDataRate(self.DATARATE)
        radio.setPALevel(self.POWER)
        radio.setAutoAck(False)
        radio.write_register(NRF24.STATUS, 0x70)

        return radio

    def transmit(sefl,radio, IRQ, data):
        txbuffer = [NRF24.W_TX_PAYLOAD] + data
        result =  radio.spidev.xfer2(txbuffer)

        #wait for successful sended
        while (GPIO.input(IRQ) == 1):
            time.sleep(0.0000001)
        radio.write_register(NRF24.STATUS, 0x70)

    def receive(self,radio, IRQ, timeout):
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

    def setup(self):
        self.radioRx = self.setupRadio(self.CE_RX)
        self.radioRx.openReadingPipe(1, self.ADDR_RX)
        self.radioRx.openReadingPipe(0, self.ADDR_RX)
        self.radioRx.startListening()


        self.radioTx = self.setupRadio(self.CE_TX)
        self.radioTx.startListening()
        self.radioTx.stopListening()
        time.sleep(130 / 1000000.0)

        self.radioTx.openWritingPipe(self.ADDR_TX)

        # setup the interrupts
        GPIO.setup(self.IRQ_TX, GPIO.IN)
        GPIO.setup(self.IRQ_RX, GPIO.IN)

    def emitMsg(self, msg):
        self.msgPipe.put(['STX',msg])

    def emitEvent(self, event, arg=None):
        self.emitEvents.put(['STX',event,arg])

    def run(self):
        pass
        #to be overwritten by children