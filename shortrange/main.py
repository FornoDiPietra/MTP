from shortrange_functions import *
import os
import sys
import time

RX_FOLDER = "/home/pi/MTP/rxfile"
TX_FOLDER = "/home/pi/MTP/txfile"

def waitForFile():
	while len(os.listdir(TX_FOLDER))<=0:
		time.sleep(1)

	filesList = os.listdir(TX_FOLDER)
	return filesList[0]

switch = "RX"

if (switch == "RX"):
	RX("cfg1",RX_FOLDER)

else:
	fileName = waitForFile()
	print("found file: " + fileName)
	TX("/home/pi/MTP/testfiles/" + fileName,"cfg1",False)
