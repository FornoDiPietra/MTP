import RPi.GPIO as GPIO
GPIO.setmode(GPIO.BCM)
from lib_nrf24 import NRF24
import time, sys, os
import spidev
from lib_protocol_shortrange import *
from threading import Thread, Event, Lock
import Queue
from lib_shortrange_thread import *

class ShortrangeTx(Shortrange):

    def run(self):
        self.stack = PacketStack()
        self.emitMsg('packet stack initialized')
        self.emitEvent('INIT')

        event = self.events.get(True)
        if (event[0] == 'KILL'):
            self.emitMsg("shortrange Tx killed")
            return
        if (event[0] == 'FILE'):
            self.FILE_NAME = event[1]
            self.emitMsg("set filename to " + self.FILE_NAME)

        if (self.COMPRESSION):
            self.emitMsg("compressing file")
            os.system("gzip < " + self.FILE_NAME + " > tmp.gz")
            self.emitMsg("reading file compressed file tmp.gz")
            self.stack.readFromFile("tmp.gz",True,self.FILE_NAME)
        else:
            self.emitMsg("reading file " + self.FILE_NAME)
            self.stack.readFromFile(self.FILE_NAME, False)

        self.emitEvent('FILE_READING_DONE')

        while (event[0] != 'START' and event[0] != 'KILL'):
            event = self.events.get(True)
        if event[0] == 'KILL':
            self.emitMsg("shortrange Tx killed")
            return

        self.setup()

        # run this to swtich the radio on and into tx mode
        self.radioTx.write_register(NRF24.CONFIG, (self.radioTx.read_register(NRF24.CONFIG) | self._BV(NRF24.PWR_UP) ) & ~self._BV(NRF24.PRIM_RX))
        self.radioTx.flush_rx()
        self.radioRx.flush_rx()

        count = 0
        ackLost = 0
        timer1 = time.time()
        stats = []


        while (not self.stack.isAllConfirmed()):
            timingStat = []
            count += 1

            timer2 = time.time()
            timer3 = time.time()

            burst = self.stack.createBurst()

            # How long did it take to create the burst?
            timingStat.append(time.time()-timer3)   
            timer3 = time.time()

            for frame in burst:
                self.transmit(self.radioTx, self.IRQ_TX, frame.getRawData())

            # How long did it take to transmit the burst
            timingStat.append(time.time()-timer3)
            timer3 = time.time()

            self.radioRx.flush_rx()
            self.radioRx.write_register(NRF24.STATUS, 0x70)    #clear the interrupt

            #now wait for the ACK
            data = self.receive(self.radioRx, self.IRQ_RX, self.ACK_TIMEOUT)

            # How long did we wait for the ACK
            timingStat.append(time.time() - timer3)
            timer3 = time.time()

            ack_message = ""
            if (data != None):
                burst.ACK(data,self.stack)
            else:
                ack_message = " (ACK timeout)"
                ackLost+=1

            self.emitMsg(str(self.stack._packetCount) + " packets left" + ack_message)

            # How long did it take to process the ACK
            timingStat.append(time.time()-timer3)
            # How long did the whole burst transmission take?
            timingStat.append(time.time()-timer2)
            timingStat.append(count)
            timingStat.append(ackLost)

            stats.append(timingStat)

            #Process events
            #while (not self.events.empty()):
            #    event = self.events.get(False)
            #    if (event[0] == 'KILL'):
            #        self.emitMsg("shortrange Tx killed")
            #        break
            #else:
            #    continue
            #break

        #Cleanup after transmission
        GPIO.cleanup()
        totalTime = time.time()-timer1
        self.emitEvent('TXDONE',totalTime)
        #self.emitMsg("time elapsed: " + str(totalTime))
        #self.emitMsg("transmitted: " + str(count))
        #self.emitMsg("timeouts: " + str(ackLost))
        #self.emitMsg("saving logfile, don't cancel!")

        # Safe a logfile
        logFile = open(os.path.basename(self.FILE_NAME) + ".timelog","w+")
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
        self.emitMsg("logfile saved")