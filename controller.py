import RPi.GPIO as GPIO
import time
from threading import Thread, Event, Lock
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)



def getButton():
	return GPIO.input(GPIO_BTN )

def waitForButtonRelease():
	while (getButton() == 1):
		time.sleep(0.001)

def getMode():
	return GPIO.input(GPIO_MODE)

def getDevOrRange():
	return GPIO.input(GPIO_DEV )


def STATE_POWER_UP():
	currentState = 'POWER_UP'
	print("entering " + currentState)

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
	print("entering " + currentState)

	dev = getDevOrRange()
	if (dev == 0):
		print("--setting up as A1")
	else:
		print("--setting up as A2")

	print("--run networkmode rx module")
	midrangeRxModule.run()

	while True:
		mode = getMode()
		rangeMode = getDevOrRange()
		button = getButton()
		fileReceived = False

		if (mode == 1 and rangeMode == 0):
			print("--pausing network rx module")
			midrangeRxModule.stop()
			return 'MIDRANGE_RX'

		if (mode == 1 and rangeMode == 1):
			print("--pausing network rx module")
			midrangeRxModule.stop()
			return 'SHORTRANGE_RX'

		if (button == 1):
			waitForButtonRelease()
			print("--pausing network rx module")
			midrangeRxModule.stop()
			return 'NETWORK_TX'

		if (midrangeRxModule.isDone()):
			print("--file received in network rx")
			return 'NETWORK_TX'

		time.sleep(0.001)	

def STATE_MIDRANGE_RX():
	global midrangeRxModule
	currentState = 'MIDRANGE_RX'
	print("entering " + currentState)

	midrangeRxModule.start()
	print("--running midrange rx module")

	while True:
		mode = getMode()
		rangeMode = getDevOrRange()
		button = getButton()
		fileReceived = False

		if (mode == 0):
			print("--pausing midrange rx module")
			midrangeRxModule.stop()
			return 'NETWORK_RX'

		if (mode == 1 and rangeMode == 1):
			print("--pausing midrange rx module")
			midrangeRxModule.stop()
			return 'SHORTRANGE_RX'

		if (button == 1):
			waitForButtonRelease()
			print("--pausing shortrange rx module")
			midrangeRxModule.stop()
			return 'MIDRANGE_TX'

		if (midrangeRxModule.isDone()):
			print("--file received in midrange rx")
			return 'FILE_RECEIVED'

		time.sleep(0.001)

def STATE_SHORTRANGE_RX():
	currentState = 'SHORTRANGE_RX'
	print("entering " + currentState)

	while True:
		mode = getMode()
		rangeMode = getDevOrRange()
		button = getButton()
		fileReceived = False

		if (mode == 0):
			print("--pausing shortrange rx module")
			return 'NETWORK_RX'

		if (mode == 1 and rangeMode == 0):
			print("--pausing shortrange rx module")
			return 'MIDRANGE_RX'

		if (button == 1):
			waitForButtonRelease()
			print("--pausing shortrange rx module")
			return 'SHORTRANGE_TX'

		if (fileReceived):
			print("--file received in shortrange rx")
			return 'FILE_RECEIVED'

		time.sleep(0.001)

def STATE_FILE_RECEIVED():
	currentState = 'FILE_RECEIVED'
	print("entering " + currentState)
	return 'POWER_UP'

def STATE_SHORTRANGE_TX():
	currentState = 'SHORTRANGE_TX'
	print("entering " + currentState)

	print("--starting shortrange tx module")
	
	# do we really not want to escape from that state anymore?!
	time.sleep(10)

	print("--shutting shortrange tx module down")

	return 'TX_DONE'

def STATE_MIDRANGE_TX():
	currentState = 'MIDRANGE_TX'
	print("entering " + currentState)

	print("--starting midrange tx module")
	
	# do we really not want to escape from that state anymore?!
	time.sleep(10)

	print("--shutting midrange tx module down")

	return 'TX_DONE'

def STATE_NETWORK_TX():
	currentState = 'NETWORK_TX'
	print("entering " + currentState)

	print("--starting network tx module")
	
	# do we really not want to escape from that state anymore?!
	time.sleep(10)

	print("--shutting network tx module down")

	return 'TX_DONE'

def STATE_TX_DONE():
	currentState = 'TX_DONE'
	print("entering " + currentState)

	print("Transmission is done. Press button to confirm")

	while True:
		time.sleep(0.001)
		button = getButton()

		if (button == 1):
			waitForButtonRelease()
			return 'POWER_UP'

def STATE_FILE_NOT_FOUND():
	current = 'FILE_NOT_FOUND'
	print("entering " + currentState)

	while True:
		time.sleep(0.001)
		button = getButton()

		if (button == 1):
			waitForButtonRelease()
			return 'POWER_UP'

GPIO_BTN  = 26
GPIO_MODE = 19
GPIO_DEV  = 13


GPIO.setup(GPIO_BTN,  GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
GPIO.setup(GPIO_MODE, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
GPIO.setup(GPIO_DEV,  GPIO.IN, pull_up_down=GPIO.PUD_DOWN)


print("BTN:\t\t"     + str(GPIO.input(GPIO_BTN )))
print("GPIO_MODE:\t" + str(GPIO.input(GPIO_MODE)))
print("GPIO_DEV:\t"  + str(GPIO.input(GPIO_DEV )))

midrangeRxModule = Midrange_rx_module()

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
finally:
	GPIO.cleanup()