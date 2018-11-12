import time
from lib_protocol_shortrange import *
import random
import os


# to do:
#       check what happens if only one packet is not confirmed!!!!

stack = PacketStack()
rxStack = PacketStack()

os.system("gzip < data.txt > data.txt.gz")
stack.readFromFile("data.txt.gz")

#stack._packets[1].confirm()

burstCounter = 0
lostCounter = 0
ackLostCounter = 0


while True:
	print("---------------------------------")
	#print("The Tx Stack")
	#print(str(stack))
	burst = stack.createBurst()
	rxBurst = RxBurst()

	#raw_input("see tx burst...")

	#print(str(burst))

	print("transmitting frames... (Channel magic is happening)")
	c=0
	burstCounter+=1
	for frame in burst:
		god = random.random()
		if (god > 0.75):
			print( "Successful Tx of: " + str(frame.getPacket().getSeqNum()) )
			rxFrame = RxFrame(frame.getRawData()[:])
			rxBurst.addFrame(rxFrame)
			c+=1
		else:
			lostCounter+=1
			print( "lost Tx of:       " + str(frame.getPacket().getSeqNum()) )
	#print("transmitted " + str(c) + " packets "

	#raw_input("see rx burst...")
	#print(str(rxBurst))

	print("transmitting ACK")
	god = random.random()
	if (god > 0.05):
		ack = rxBurst.getACK()
		burst.ACK(ack)
		print("ACK received")
	else:
		print("ACK timeout in Tx")
		ackLostCounter+=1

	#raw_input("seding ACK, see Tx Stack")
	#print(str(stack))

	#print("see the Rx stack")
	rxStack.addBurst(rxBurst)
	#print(str(rxStack))

	print("is complete? " + str(rxStack.isCompletlyReceived()))
	if (rxStack.isCompletlyReceived()):
		break

	#raw_input("press for next round...")

print("sent: " + str(burstCounter) + " bursts")
print("lost: " + str(lostCounter) + " data packets")
print("lost: " + str(ackLostCounter) + " ACKs") 
rxStack.writeToFile("received.txt.gz")
os.system("gunzip < received.txt.gz > received.txt")

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