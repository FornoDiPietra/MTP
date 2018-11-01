
class Packet:

	def __init__(self):
		self._seqNum = 0
		self._data = [0x00] * 29
		self._confirmed = False
		self._valid = False
		self._burstId = 0

	def getTransmitData(self):
		high = self._seqNum>>8 & 0xFF
		low  = self._seqNum & 0xFF

		return [self._burstId ,high, low] + self._data

	def setDataAndSeqNum(self, data, seqNum):
		self._seqNum = seqNum
		self._data = data

	def setBurstId(self, bid):
		self._burstId = bid

	def createFromRadio(self, recvData):
		self._burstId = recvData[0]
		high = recvData[1]
		low  = recvData[2]
		self._seqNum = high<<8 | low
		self._data = recvData[3:]






p1 = Packet()
#p1.setDataAndSeqNum([0xFF]*29, 51231)

b= [0, 200, 31, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255];
p1.createFromRadio(b)
print( p1.getTransmitData() )
print(p1._seqNum)
print(p1._burstId)


# ack = [0xAA]*32

# for b in ack:
# 	print("---")

# 	for i in range(0,8):
# 		if ( (b & 0x01<<i) == 0 ):
# 			print("0")
# 		else:
# 			print("1")
