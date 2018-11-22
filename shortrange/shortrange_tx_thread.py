#!/usr/bin/python2

import RPi.GPIO as GPIO
GPIO.setmode(GPIO.BCM)
from lib_nrf24 import NRF24
import time, sys
import spidev
from lib_protocol_shortrange import *
import os
from threading import Thread, Event, Lock
import Queue

class ShortrangeTx(Thread):

    def __init__(self, controllerQueue):
        self.CHANNEL = 0x70
        self.POWER = NRF24.PA_MAX
        #POWER = NRF24.PA_HIGH
        #POWER = NRF24.PA_LOW
        #POWER = NRF24.PA_MIN
        self.DATARATE = NRF24.BR_2MBPS
        self.CE_TX = 0
        self.CE_RX = 1
        self.IRQ_TX = 16
        self.IRQ_RX = 20
        self.ADDR_TX = [0xe7, 0xe7, 0xe7, 0xe7, 0xe7]
        self.ADDR_RX = [0xc2, 0xc2, 0xc2, 0xc2, 0xc2]
        self.COMPRESSION = False
        self.ACK_TIMEOUT = 0.2

        self.events = Queue.Queue()
        self.emissionEvents = controllerQueue
        self.daemon = True

    def loadFile(self,fileName):
        self.events.put(['FILE', fileName])

    def startTx(self):
        self.events.put(['START', None])

    def pauseTx(self):
        self.events.put(['PAUSE',None])

    def reset(self):
        self.events.put(['RESET',None])


    def _BV(x):
        return 1

    def setupRadio(CE):
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

    def setup(self):
		self.radioRx = setupRadio(CE_RX)
        self.radioRx.openReadingPipe(1, ADDR_RX)
        self.radioRx.openReadingPipe(0, ADDR_RX)
        self.radioRx.startListening()

        self.radioTx = setupRadio(CE_TX)
        self.radioTx.startListening()
        self.radioTx.stopListening()
        self.time.sleep(130 / 1000000.0)
        self.radioTx.openWritingPipe(ADDR_TX)

        # setup the interrupts
        GPIO.setup(self.IRQ_TX, GPIO.IN)
        GPIO.setup(self.IRQ_RX, GPIO.IN)

    def run(self):
        FILE_NAME = ""

        self.setup()

        print("init the packet stack")
        self.stack = PacketStack()

        event = ['','']
        # Wait for the file event
        while (event[0] != 'FILE'):
            event = self.events.get(True)
        FILE_NAME = event[1]

        if (COMPRESSION):
            print("compressing file")
            os.system("gzip < " + FILE_NAME + " > tmp.gz")
            print("reading file compressed file tmp.gz")
            self.stack.readFromFile("tmp.gz",True)
        else:
            print("reading file " + FILE_NAME)
            self.stack.readFromFile(FILE_NAME, False)

        # Wait for the start Event
        while (event[0] != 'START'):
            event = self.events.get(True)
        
        # run this to swtich the radio on and into tx mode
        self.radioTx.write_register(NRF24.CONFIG, (self.radioTx.read_register(NRF24.CONFIG) | _BV(NRF24.PWR_UP) ) & ~_BV(NRF24.PRIM_RX))
        self.radioTx.flush_rx()
        self.radioRx.flush_rx()

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

                burst = self.stack.createBurst()

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
                    burst.ACK(data,self.stack)
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

                # wait for a stop event
                while (not self.events.empty()):
                    event = self.events.get(False)
                    if event[0] == 'PAUSE':
                        # Wait for the start Event
                        while (event[0] != 'START'):
                            event = self.events.get(True)


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