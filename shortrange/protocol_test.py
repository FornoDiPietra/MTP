import time
from lib_protocol_shortrange import *
#from simulator import *
import random

stack = PacketStack()
rxStack = PacketStack()

stack.readFromFile("data.txt")

#stack._packets[1].confirm()



while True:
	print("---------------------------------")
	print("The Tx Stack")
	print(str(stack))
	burst = stack.createBurst()
	rxBurst = RxBurst()

	#raw_input("see tx burst...")

	#print(str(burst))

	print("transmitting frames...")
	c=0
	for frame in burst:
		god = random.random()
		if (god > 0.5):
			rxFrame = RxFrame(frame.getRawData()[:])
			rxBurst.addFrame(rxFrame)
			c+=1
	print("transmitted " + str(c) + " packets")

	#raw_input("see rx burst...")
	#print(str(rxBurst))

	print("transmitting ACK")
	god = random.random()
	if (god > 0.2):
		ack = rxBurst.getACK()
		burst.ACK(ack)
		print("ACK received")
	else:
		print("ACK timeout in Tx")

	#raw_input("seding ACK, see Tx Stack")
	#print(str(stack))

	print("see the Rx stack")
	rxStack.addBurst(rxBurst)
	print(str(rxStack))

	print("is complete? " + str(rxStack.isCompletlyReceived()))
	if (rxStack.isCompletlyReceived()):
		break

	raw_input("press for next round...")

## wait for the burst
#startTime = time.time()
#txAckWaitTimeOut = 1
#
##while (not dataAvailable() and (time.time()-startTime)<txAckWaitTimeOut):
##    time.sleep(0.000000001)
#
##if (dataAvailable()):
##    burst.ACK(ack)
#
#
#while (not stack.isAllConfirmed()):
#    burst = stack.createNextBurst()
#
#    #transmit the burst
#
#    #wait for the acknowledgement
#
#    ack = [0x00] * 32
#    ack[0] = 0b00000001
#
#    #mark the acknowledged packets
#    burst.ACK(ack)
#
#    for i in burst:
#        print(i)
#
#
##     print("-"*131)
#