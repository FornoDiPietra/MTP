from shortrange_functions import *
import os
import sys
import time

def waitForFile():
	path="/home/pi/txfile"
	while len(os.listdir(path))<=0:
		time.sleep(1)

	filesList = os.listdir(path)
	return filesList[0]

switch = "TX"

if (switch == "RX"):
	RX("cfg1")

else:
	fileName = waitForFile()
	print("found file: " + fileName)
	TX("/home/pi/MTP/testfiles/" + fileName,"cfg1",False)
