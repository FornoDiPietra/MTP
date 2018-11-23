#!/usr/bin/python2

from shortrange_functions import *
import os
import sys
import time
from threading import Thread, Event, Lock
import Queue

RX_FOLDER = "/home/pi/MTP/rxfile/"
TX_FOLDER = "/home/pi/MTP/txfile/"

class LED(Thread):
	def __init__(self, channel):
		super(LED, self).__init__()
		self.frequency = 0.9
		self.GPIO_CHANNEL = channel
		self.events = Queue.Queue()
		self.daemon = True
		self.state = 'OFF'
		GPIO.setup(channel,  GPIO.OUT)
		self.off()
		self.start()

	def run(self):
		# we are off, wait until turned on/blink
		event = self.events.get(True)

		#print("got and event: " + str(event))

		while True:
			
			if (event == 'OFF'):
				GPIO.output(self.GPIO_CHANNEL, 0)
				self.state = 'OFF'
				event = self.events.get(True)

			elif (event == 'ON'):
				GPIO.output(self.GPIO_CHANNEL, 1)
				self.state = 'ON'
				event = self.events.get(True)

			elif (event == 'BLINK'):
				self.state = 'BLINK'
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
	def toggle(self):
		if self.state == 'ON' or self.state == 'BLINK':
			self.off()
		if self.state == 'OFF':
			self.on()


class Switch():

	def __init__(self, channel):
		self.GPIO_CHANNEL = channel
		GPIO.setup(channel, GPIO.IN)
		self.lastState = GPIO.input(self.GPIO_CHANNEL)

	def isOn(self):
		if GPIO.input(self.GPIO_CHANNEL) == 0:
			return True
		else:
			return False

	def changed(self):
		val = GPIO.input(self.GPIO_CHANNEL)

		if (val == self.lastState):
			return False

		self.lastState = val
		return True

class Button():
	def __init__(self, channel):
		self.GPIO_CHANNEL = channel
		GPIO.setup(channel, GPIO.IN)
		self.lastState = GPIO.input(self.GPIO_CHANNEL)

	def isOn(self):
		if GPIO.input(self.GPIO_CHANNEL) == 0:
			return True
		else:
			return False

	def waitForRelease(self):
		while (GPIO.input(self.GPIO_CHANNEL) == 0):
			time.sleep(0.001)

	def waitForPress(self):
		while (GPIO.input(self.GPIO_CHANNEL) == 1):
			time.sleep(0.001)


def waitForFile():
	while True:
		# find the first one smaller than 24 characters
		for file in os.listdir(TX_FOLDER):
			if (len(file) < 24):
				return file
			
		time.sleep(1)


SW2 = Switch( 6)
SW3 = Switch(13)
BTN = Button(12)


led_err = LED(22)
led_rx  = LED(17)
led_tx  = LED(21)
led_a1  = LED(14)
led_a2  = LED(18)
led_net = LED(27)
led_dir = LED( 4)

leds = [led_err, led_rx, led_tx, led_a1, led_a2, led_net, led_dir]



while True:

	while (not BTN.isOn()):
		for led in leds:
			led.on()

		time.sleep(0.5)

		for led in leds:
			led.off()

		time.sleep(0.5)
	BTN.waitForRelease()

	if (SW2.isOn()):
		#network mode
		led_net.on()

	else:
		#Shortrange / midrange
		led_net.off()
		led_a1.off()
		led_a2.off()
		led_dir.off()

		if (SW3.isOn()):
			#Rx
			led_tx.off()
			led_rx.blink() #--> turned on by RX function as soon as ready
			RX("cfg1", RX_FOLDER, led_err, led_rx, led_tx, led_a1, led_a2, led_net, led_dir,BTN,SW2,SW3)

		else:
			#Tx
			led_tx.on()
			led_rx.off()

			fileName = waitForFile()
			led_dir.blink()
			print("found file: " + fileName)
			time.sleep(1)
			TX(TX_FOLDER + fileName,"cfg1",led_err, led_rx, led_tx, led_a1, led_a2, led_net, led_dir,BTN,SW2,SW3,compression=False)


for led in leds:
	led.kill()

GPIO.cleanup()