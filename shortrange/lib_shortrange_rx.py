import RPi.GPIO as GPIO
GPIO.setmode(GPIO.BCM)
from lib_nrf24 import NRF24
import time, sys, os
import spidev
from lib_protocol_shortrange import *
from threading import Thread, Event, Lock
import Queue
from lib_shortrange_thread import *

class ShortrangeRx(Shortrange):

    def emitMsg(self, msg):
        self.msgPipe.put(['SRX',msg])

    def emitEvent(self, event, arg=None):
        self.emitEvents.put(['SRX',event,arg])

    def checkKill(self):
        if (not self.events.empty()):
            event = self.events.get(False)
            if (event[0] == 'KILL'):
                return True
        return False

    def run(self):

        self.stack = PacketStack()
        self.emitMsg("packet stack initialized")
        self.emitEvent('INIT')

        event = self.events.get(True)
        while (event[0] != 'START' and event[0] != 'KILL'):
            event = self.events.get(True)
        if event[0] == 'KILL':
            self.emitMsg("shortrange Rx killed")
            return

        self.setup()


        # run this to swtich the radio on and into tx mode
        self.radioTx.write_register(NRF24.CONFIG, (self.radioTx.read_register(NRF24.CONFIG) | self._BV(NRF24.PWR_UP) ) & ~self._BV(NRF24.PRIM_RX))
        self.radioTx.flush_rx()
        self.radioRx.flush_rx()

        count = 0
        fails = 0
        stats = []
        totalTime = 0
        timer1 = time.time()

        self.emitMsg("waiting for bursts")


        while True:
            count += 1

            burst = RxBurst()
            self.radioRx.flush_rx()

            data = None
            while (data == None):
                data = self.receive(self.radioRx, self.IRQ_RX, 0.5)
                if self.checkKill():
                    self.emitMsg('short Rx is killed')
                    return

            frame = RxFrame(data)
            burst.addFrame(frame)

            while True:
                data = self.receive(self.radioRx, self.IRQ_RX, burst.getTimeOut())

                if (data != None):
                    frame = RxFrame(data)
                    burst.addFrame(frame)
                else:
                    break

            self.transmit(self.radioTx,self.IRQ_TX,burst.getACK())
            self.transmit(self.radioTx,self.IRQ_TX,burst.getACK())
            self.radioRx.write_register(NRF24.STATUS, 0x70)    #reset interrupt
            self.emitMsg("received burst: " + str(count) + " - " + str(burst.statsNumRcv) + "/256")
            self.stack.addBurst(burst)

            stats.append([count, burst.statsNumRcv])

            if (self.stack.isCompletlyReceived()):
                self.emitMsg("\033[92m file received!\033[0m")
                self.emitEvent('RXDONE')
                totalTime = time.time() - timer1

            # Process event
            while (not self.events.empty()):
                event = self.events.get(False)
                if (event[0] == 'KILL'):
                    self.emitMsg("shortrange Rx killed")
                    break
            else:
                continue
            break


        fileName = self.stack._packets[0].getFileName()
        compression = self.stack._packets[0].isCompressed()
        self.emitMsg("recovered file name:" + fileName)

        if (self.FILE_NAME != ""):
            self.emitMsg("saving file as " + self.FILE_NAME + " (specified as an argument)")
            fileName = FILE_NAME

        tmpFileName = fileName
        if (compression):
            tmpFileName = "tmp.gz"

        print("writing received data to file: " + tmpFileName)
        self.stack.writeToFile(tmpFileName)

        if (compression):
            self.emitMsg("decompressing file")
            os.system("gunzip < tmp.gz > " + fileName)

        GPIO.cleanup()
        #print("time elapsed: " + str(totalTime))
        #print("transmitted: " + str(count))
        #print("timeouts: " + str(fails))

        self.emitMsg("saving packet loss statistics")
        logFile = open(fileName + ".loss","w+")
        logFile.write(time.asctime( time.localtime(time.time())) + "\n")
        logFile.write("total time: " + str(totalTime) + "\n")

        logFile.write("burst_count;losses\n")
        for s in stats:
            logFile.write(str(s[0]) + ";" + str(s[1]) + "\n")
        logFile.close()

        self.emitEvent('FILE_SAVED')