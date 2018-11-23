#!/usr/bin/python2

import RPi.GPIO as GPIO
GPIO.setmode(GPIO.BCM)
from lib_nrf24 import NRF24
import time, sys, os
import spidev
from lib_protocol_shortrange import *
from threading import Thread, Event, Lock
import Queue
from lib_shortrange_tx import *
from lib_shortrange_rx import *


class MsgPipeProcessor(Thread):

    def __init__(self, pipe):
        super(MsgPipeProcessor, self).__init__()
        self.pipe = pipe
        self.daemon = True

    def run(self):
        while True:
            event = self.pipe.get(True)
            print(event[0].rjust(5) + " | " + event[1])


#main
try:
	switch = "TX"
	#switch = "RX"
	eventPipe = Queue.Queue()
	msgPipe = Queue.Queue()
	msgPipeProcessor = MsgPipeProcessor(msgPipe)
	msgPipeProcessor.start()

	shortrangeTx = ShortrangeTx(eventPipe, msgPipe)
	shortrangeRx = ShortrangeRx(eventPipe, msgPipe)

	msgPipe.put(['MAIN','init shortrange rx'])
	shortrangeRx.start()

	msgPipe.put(['MAIN', 'init shortrange tx'])
	shortrangeTx.start()

	if (switch == "RX"):

		shortrangeRx.startOperation()

		event = eventPipe.get(True)

		while True:
			time.sleep(10)

	elif (switch == "TX"):
		event = eventPipe.get(True)
		
		msgPipe.put(['MAIN', 'loading file'])
		shortrangeTx.loadFile("../testfiles/test_pat_001.txt")
		
		event = eventPipe.get(True)
		print(event)
		
		msgPipe.put(['MAIN','Starting transmission'])
		shortrangeTx.startOperation()
		
		event = eventPipe.get(True)

except KeyboardInterrupt:
	print("")
finally:
	shortrangeTx.kill()
	shortrangeRx.kill()

	time.sleep(2)