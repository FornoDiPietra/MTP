import RPi.GPIO as GPIO
import time
from threading import Thread, Event, Lock
import Queue
import sys
import os
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

DEBUG_LEVEL = 0

class MidrangeRxModule(Thread):

	def __init__(self, led0):
		super(MidrangeRxModule, self).__init__()
		self.events = Queue.Queue()	
		self.sleep()
		self.daemon = True
		self.start()
		self.led0 = led0

	def sleep(self):
		self.events.put('SLEEP')

	def wakeup(self):
		self.events.put('WAKEUP')

	def kill(self):
		self.events.put('DIE')

	def isDone(self):
		return False

	def run(self):

		while True:
			try:
				event = self.events.get(True)

				if (event == 'SLEEP'):
					# sleep until we are woken up again
					log("Midrange RX sleeps", "MRX", 2)
					#self.led0.off()
					while True:
						event = self.events.get(True)
						if (event != 'SLEEP'):
							break
				if (event == 'DIE'):
					break

				log("Midrange RX running", "MRX", 2)
				#self.led0.on()

			except Queue.Empty:
				#print("receiving midrange rx")		
				pass

class MidrangeTxModule(Thread):

	def __init__(self, led0):
		super(MidrangeTxModule, self).__init__()
		self.events = Queue.Queue()	
		self.sleep()
		self.daemon = True
		self.start()
		self.led0 = led0
		self.done = False

	def sleep(self):
		self.events.put('SLEEP')

	def wakeup(self):
		self.events.put('WAKEUP')

	def kill(self):
		self.events.put('DIE')

	def isDone(self):
		return self.done

	def run(self):
		rcvCounter = 0

		while True:
			try:
				event = self.events.get(False)

				if (event == 'SLEEP'):
					# sleep until we are woken up again
					log("Midrange TX sleeps", "MTX", 2)
					#self.led0.off()
					while True:
						event = self.events.get(True)
						if (event != 'SLEEP'):
							break
				if (event == 'DIE'):
					break

				log("Midrange TX running", "MTX", 2)
				rcvCounter = 0
				#self.led0.blink()

			except Queue.Empty:
				#print("receiving midrange rx")	
				time.sleep(1)
				rcvCounter += 1
				if rcvCounter > 10:
					log("File transmitted", "MTX", 5)
					self.done = True
				pass

class LED(Thread):
	def __init__(self, channel):
		super(LED, self).__init__()
		self.frequency = 0.9
		self.GPIO_CHANNEL = channel
		self.events = Queue.Queue()
		self.daemon = True
		self.state = 0

	def run(self):
		# we are off, wait until turned on/blink
		event = self.events.get(True)

		print("got and event: " + str(event))

		while True:
			
			if (event == 'OFF'):
				GPIO.output(self.GPIO_CHANNEL, 0)
				event = self.events.get(True)

			elif (event == 'ON'):
				GPIO.output(self.GPIO_CHANNEL, 1)
				event = self.events.get(True)

			elif (event == 'BLINK'):
				toggler = False
				
				while True:
					toggler = not toggler
					if (toggler):
						GPIO.output(self.GPIO_CHANNEL, 1)
					else:
						GPIO.output(self.GPIO_CHANNEL, 0)

					try:
						event = self.events.get(True, self.frequency/2.0)
						break
					except Queue.Empty:
						pass

			elif (event == 'DIE'):
				GPIO.output(self.GPIO_CHANNEL, 0)
				break

	def blink(self):
		self.events.put('BLINK')
	def on(self):
		self.events.put('ON')
	def off(self):
		self.events.put('OFF')
	def kill(self):
		self.events.put('DIE')

def log(msg, module, severity):
	global DEBUG_LEVEL
	timeStamp = time.asctime( time.localtime(time.time()))
	logMsg = timeStamp + " | " + module + " | " + msg

	if DEBUG_LEVEL <= severity:
		print(logMsg)


def getButton():
	return GPIO.input(GPIO_BTN )

def waitForButtonRelease():
	while (getButton() == 1):
		time.sleep(0.001)

def getMode():
	return GPIO.input(GPIO_MODE)

def getDevOrRange():
	return GPIO.input(GPIO_DEV )

def findMidrangeFile():
	return os.path.isfile("midrange.tx") 

def STATE_POWER_UP():
	currentState = 'POWER_UP'
	log("entering " + currentState, "STM", 2)

	mode = getMode()
	rangeMode = getDevOrRange()

	if (mode == 0):
		return 'NETWORK_RX'

	if (mode == 1 and rangeMode == 0):
		return 'MIDRANGE_RX'

	if (mode == 1 and rangeMode == 1):
		return 'SHORTRANGE_RX'

def STATE_NETWORK_RX():
	currentState = 'NETWORK_RX'
	log("entering " + currentState, "STM", 2)

	dev = getDevOrRange()
	if (dev == 0):
		log("--setting up as A1", "STM", 2)
	else:
		log("--setting up as A2", "STM", 2)

	log("run networkmode rx module", "STM", 1)

	while True:
		mode = getMode()
		rangeMode = getDevOrRange()
		button = getButton()
		fileReceived = False

		if (mode == 1 and rangeMode == 0):
			log("--pausing network rx module", "STM", 1)
			return 'MIDRANGE_RX'

		if (mode == 1 and rangeMode == 1):
			log("--pausing network rx module", "STM", 1)
			return 'SHORTRANGE_RX'

		if (button == 1):
			waitForButtonRelease()
			log("--pausing network rx module", "STM", 1)
			return 'NETWORK_TX'

		if (midrangeRxModule.isDone()):
			log("--file received in network rx", "STM", 1)
			return 'NETWORK_TX'

		time.sleep(0.001)	

def STATE_MIDRANGE_RX():
	global midrangeRxModule, txFileFound
	currentState = 'MIDRANGE_RX'
	log("entering " + currentState, "STM", 2)

	log("--wakeup midrange rx module", "STM", 1)
	midrangeRxModule.wakeup()

	led0.on()

	while True:
		mode = getMode()
		rangeMode = getDevOrRange()
		button = getButton()

		if (mode == 0):
			log("--pausing midrange rx module", "STM", 1)
			midrangeRxModule.sleep()
			led0.off()
			return 'NETWORK_RX'

		if (mode == 1 and rangeMode == 1):
			log("--pausing midrange rx module", "STM", 1)
			midrangeRxModule.sleep()
			led0.off()
			return 'SHORTRANGE_RX'

		if (button == 1):
			waitForButtonRelease()
			log("--pausing shortrange rx module", "STM", 1)
			midrangeRxModule.sleep()
			led0.off()
			return 'MIDRANGE_TX'

		if (midrangeRxModule.isDone()):
			log("--file received in midrange rx", "STM", 1)
			led0.off()
			return 'FILE_RECEIVED'

		if (findMidrangeFile() and not txFileFound):
			log("found mid range file", "STM", 5)
			txFileFound = True

		time.sleep(0.001)

def STATE_SHORTRANGE_RX():
	currentState = 'SHORTRANGE_RX'
	log("entering " + currentState, "STM", 2)

	while True:
		mode = getMode()
		rangeMode = getDevOrRange()
		button = getButton()
		fileReceived = False

		if (mode == 0):
			log("--pausing shortrange rx module", "STM", 1)
			return 'NETWORK_RX'

		if (mode == 1 and rangeMode == 0):
			log("--pausing shortrange rx module", "STM", 1)
			return 'MIDRANGE_RX'

		if (button == 1):
			waitForButtonRelease()
			log("--pausing shortrange rx module", "STM", 1)
			return 'SHORTRANGE_TX'

		if (fileReceived):
			log("--file received in shortrange rx", "STM", 1)
			return 'FILE_RECEIVED'

		time.sleep(0.001)

def STATE_FILE_RECEIVED():
	currentState = 'FILE_RECEIVED'
	log("entering " + currentState, "STM", 2)
	return 'POWER_UP'

def STATE_SHORTRANGE_TX():
	currentState = 'SHORTRANGE_TX'
	log("entering " + currentState, "STM", 2)

	log("--starting shortrange tx module", "STM", 1)
	
	# do we really not want to escape from that state anymore?!
	time.sleep(10)

	log("--shutting shortrange tx module down", "STM", 1)

	return 'TX_DONE'

def STATE_MIDRANGE_TX():
	currentState = 'MIDRANGE_TX'
	log("entering " + currentState, "STM", 2)

	log("--starting midrange tx module", "STM", 1)
	midrangeTxModule.wakeup()
	led0.blink()

	while (not midrangeTxModule.isDone()):
		time.sleep(0.001)

	log("--shutting midrange tx module down", "STM", 1)
	midrangeTxModule.sleep()
	led0.off()

	return 'TX_DONE'

def STATE_NETWORK_TX():
	currentState = 'NETWORK_TX'
	log("entering " + currentState, "STM", 2)

	log("--starting network tx module", "STM", 1)
	
	# do we really not want to escape from that state anymore?!
	time.sleep(10)

	log("--shutting network tx module down", "STM", 1)

	return 'TX_DONE'

def STATE_TX_DONE():
	currentState = 'TX_DONE'
	log("entering " + currentState, "STM", 2)

	while True:
		time.sleep(0.001)
		button = getButton()

		if (button == 1):
			waitForButtonRelease()
			return 'POWER_UP'

def STATE_FILE_NOT_FOUND():
	current = 'FILE_NOT_FOUND'
	log("entering " + currentState, "STM", 2)

	while True:
		time.sleep(0.001)
		button = getButton()

		if (button == 1):
			waitForButtonRelease()
			return 'POWER_UP'

GPIO_BTN  = 26
GPIO_MODE = 19
GPIO_DEV  = 13

GPIO_LED0 = 6

txFileFound = False


GPIO.setup(GPIO_BTN,  GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
GPIO.setup(GPIO_MODE, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
GPIO.setup(GPIO_DEV,  GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

GPIO.setup(GPIO_LED0, GPIO.OUT)

print("BTN:\t\t"     + str(GPIO.input(GPIO_BTN )))
print("GPIO_MODE:\t" + str(GPIO.input(GPIO_MODE)))
print("GPIO_DEV:\t"  + str(GPIO.input(GPIO_DEV )))
	

led0 = LED(GPIO_LED0)
led0.start()
led0.off()

midrangeRxModule = MidrangeRxModule(led0)
midrangeTxModule = MidrangeTxModule(led0)

time.sleep(0.1)


nextState = STATE_POWER_UP()

try:
	while True:
		if (nextState == 'POWER_UP'):
			nextState = STATE_POWER_UP()

		elif (nextState == 'NETWORK_RX'):
			nextState = STATE_NETWORK_RX()

		elif (nextState == 'MIDRANGE_RX'):
			nextState = STATE_MIDRANGE_RX()

		elif (nextState == 'SHORTRANGE_RX'):
			nextState = STATE_SHORTRANGE_RX()

		elif (nextState == 'FILE_RECEIVED'):
			nextState = STATE_FILE_RECEIVED()

		elif (nextState == 'NETWORK_TX'):
			nextState = STATE_NETWORK_TX()

		elif (nextState == 'SHORTRANGE_TX'):
			nextState = STATE_SHORTRANGE_TX()

		elif (nextState == 'MIDRANGE_TX'):
			nextState = STATE_MIDRANGE_TX()

		elif (nextState == 'TX_DONE'):
			nextState = STATE_TX_DONE()

		elif (nextState == 'FILE_NOT_FOUND'):
			nextState = STATE_FILE_NOT_FOUND()

		else:
			print("fatal error: undefinded state " + str(nextState))
			break

except KeyboardInterrupt:
	print("exiting...")
	led0.kill()
finally:
	GPIO.cleanup()