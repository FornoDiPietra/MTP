#!/usr/bin/python2

from shortrange_functions import *
import os
import sys
import time

RX_FOLDER = "/home/pi/MTP/rxfile/"
TX_FOLDER = "/home/pi/MTP/txfile/"

def waitForFile():
	while True:
		# find the first one smaller than 24 characters
		for file in os.listdir(TX_FOLDER):
			if (len(file) < 24):
				return file
			
		time.sleep(1)

while True:

	#check here the switch for Shortrange or network mode

	#check here the button for Rx or Tx
	switch = "TX"

	if (switch == "RX"):
		RX("cfg1",RX_FOLDER)

	else:
		fileName = waitForFile()
		print("found file: " + fileName)
		TX(TX_FOLDER + fileName,"cfg1",compression=True)

