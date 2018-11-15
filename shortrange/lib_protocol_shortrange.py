burstSize = 256

class Packet:

    def __init__(self):
        self._rawData = [0x00]*31
        self._confirmed = False
        self._valid = False

    def isValid(self):
        return self._valid

    def validate(self):
        self._valid = True

    def confirm(self):
        self._confirmed = True

    def isConfirmed(self):
        return self._confirmed

    def setPayloadData(self, payloadData):
        self._rawData[2:] = payloadData

    def getPayloadData(self):
        return self._rawData[2:]

    def getRawData(self):
        return self._rawData

    def setRawData(self, rawData):
        self._rawData = rawData

    def getSeqNum(self):
        high = self._rawData[0]
        low  = self._rawData[1]
        return (high<<8 | low)

    def setSeqNum(self, seqNum):
        high = seqNum>>8 & 0xFF
        low  = seqNum & 0xFF
        self._rawData[0] = high
        self._rawData[1] = low

    def getPayloadData(self):
        return self._rawData[2:]

    def __str__(self):
        conf = " "
        val = " "
        if (self.isValid()):
            val = "v"
        if (self.isConfirmed()):
            conf = "c"
        ret = str(self.getSeqNum()).rjust(5) + " - " + val + conf + " - "
        for b in self.getPayloadData():
            ret += str(b).rjust(4)
        return ret

class MagicPacket(Packet):

    def setFileSize(self, fileSize):
        high = fileSize>>8 & 0xFF
        low  = fileSize & 0xFF
        self._rawData[2] = high
        self._rawData[3] = low

    def getFileSize(self):
        high = self._rawData[2]
        low  = self._rawData[3]
        return high<<8 | low

    def setPadding(self, padding):
        high = padding>>8 & 0xFF
        low  = padding & 0xFF
        self._rawData[4] = high
        self._rawData[5] = low

    def getPadding(self):
        high = self._rawData[4]
        low  = self._rawData[5]
        return high<<8 | low

class TxFrame:

    def __init__(self):
        pass

    def getBurstId(self):
        return self._burstId

    def setBurstId(self, bid):
        self._burstId = bid

    def getPacket(self):
        return self._packet

    def setPacket(self, packet):
        self._packet = packet

    def getRawData(self):
        return [self._burstId & 0xFF] + self._packet.getRawData()

    def __str__(self):
        return str(self._burstId).rjust(3) + "| " + str(self._packet)

class RxFrame(TxFrame):

    def __init__(self, rawData):
        self.setRawData(rawData)

    def setRawData(self, rawData):
        self._rawData = rawData

    def getBurstId(self):
        return self._rawData[0]

    def getPacketSeqNum(self):
        high = self._rawData[1]
        low  = self._rawData[2]
        return (high<<8 | low)

    def getRawPacketData(self):
        return self._rawData[1:]

    def __str__(self):
        return str(self.getBurstId()) + "| "  + str(self._rawData[1:])

class PacketStack:

    def __init__(self):
        self._packets = [MagicPacket()]
        for i in range(0,0xFFFF+1):
            self._packets.append(Packet())
        self._packetCount = 0
        self._unconfirmedIndexes = range(0,0xFFFF)

    def readFromFile(self, fileName, blockSize=29):
        firstPacket = self._packets[0]
        self._packetCount=1
        with open(fileName, "rb") as f:
            byteBlock = f.read(blockSize)

            loopIndex = 1
            while byteBlock != b'':
                dataBlock = self._convertToArray(byteBlock)
                if (len(dataBlock) < blockSize):
                    padding = self._fillWithPadding(dataBlock, blockSize)
                    firstPacket.setPadding(padding)

                self._packets[loopIndex].setSeqNum(loopIndex)
                self._packets[loopIndex].setPayloadData(dataBlock[:])
                self._packets[loopIndex].validate()
                self._packetCount+=1
                loopIndex+=1

                byteBlock = f.read(blockSize)
            f.close()

        firstPacket.setFileSize(loopIndex-1)
        firstPacket.validate()
        
    def writeToFile(self, fileName):
        f = open(fileName, "wb")
        # only write something if we have received at least 2 packets
        if (self._packetCount > 1):
            padding = self._packets[0].getPadding() 
            
            for i in range(1,self._packetCount):
                p = self._packets[i]
                if (p.isValid()):
                    if (i == self._packetCount-1):
                        # this is the last packet and we need to care for the padding
                        f.write(bytearray(p.getPayloadData()[:-padding]))
                    else:
                        f.write(bytearray(p.getPayloadData()))
        f.close()

    def createBurst(self):
        burst = TxBurst()
        counter = 0
        i = 0
        j = 0
        while (not burst.isFull()):
            for packet in self._packets:
                j+=1
                if not packet.isConfirmed():
                    burst.addPacket(packet)
                    if (burst.isFull()):
                        break
        return burst

    def addBurst(self, burst):
        c=0
        for frame in burst:
            seqNum = frame.getPacketSeqNum()
            if (not self._packets[seqNum].isValid()):
                self._packets[seqNum].setRawData( frame.getRawPacketData()[:] )
                self._packets[seqNum].validate()
                self._packetCount+=1
                c+=1

        #print("added " + str(c) + " frames from burst")

    def _convertToArray(self, byteBlock):
        arr = []
        for b in byteBlock:
            arr.append(ord(b))
        return arr

    def _fillWithPadding(self, dataBlock, blockSize):
        paddingLen = blockSize - len(dataBlock)
        while (len(dataBlock) < blockSize):
            dataBlock.append(0x00)
        return paddingLen

    def isAllConfirmed(self):
        for i in range(0,self._packetCount):
            if (not self._packets[i].isConfirmed()):
                return False
        return True

    def isCompletlyReceived(self):
        if (self._packets[0].isValid()):
            maxSeq = self._packets[0].getFileSize()
            #print("self.packetcount=" + str(self._packetCount) + " maxSeq=" + str(maxSeq))
            if (self._packetCount > maxSeq):
                return True    
        return False

    def __str__(self):
        s = ""
        for p in self._packets:
            if (p.isValid()):
                s += str(p) + "\n"
        
        return s

class TxBurst:

    def __init__(self):
        self._burstSize = burstSize
        self._frameCount = 0
        self._frames = []

    def addPacket(self, packet):
        frame = TxFrame()
        frame.setPacket(packet)
        frame.setBurstId(self._frameCount)
        self._frames.append(frame)
        self._frameCount+=1

    def isFull(self):
        if (self._frameCount >= self._burstSize):
            return True
        else:
            return False

    def ACK(self, ackData, stack):
        j=0
        for b in ackData:
            for i in range(0,8):
                if ( (b & 0x01<<i) != 0 and j<self._burstSize):
                    self._frames[j].getPacket().confirm()
                    stack._packets.remove(self._frames[j].getPacket())
                    stack._packetCount -= 1
                j+=1 

    def __str__(self):
        s = ""
        for i in range(0, self._frameCount):
            s += str(self._frames[i]) + "\n"
        return s

    def __iter__(self):
        self._itterIndex = 0
        return self

    def next(self):
        return self.__next__()

    def __next__(self):
        if self._itterIndex >= self._burstSize:
            raise StopIteration
        else:
            self._itterIndex+=1
            return self._frames[self._itterIndex-1]

class RxBurst(TxBurst):

    def __init__(self):
        self._burstSize = burstSize
        self._frameCount = self._burstSize
        self._frames = []
        self._frameTime = 0.1
        self._timeOut = self._burstSize * self._frameTime
        self._ack = [0x00] * 32
        for i in range(0,self._burstSize):
            self._frames.append(None)

        self._statsNumRcv = 0

    def addFrame(self, frame):
        if (frame.getBurstId() < self._burstSize):
            self._statsNumRcv +=1
            self._frames[frame.getBurstId()] = frame
            self.markACKbit(frame.getBurstId())
            self._timeOut = (self._burstSize - frame.getBurstId()-1)*self._frameTime

    def getTimeOut(self):
        return self._timeOut

    def markACKbit(self, index):
        bitIndex = index % 8
        byteIndex = int(index/8)
        self._ack[byteIndex] = self._ack[byteIndex] | 0x01<<bitIndex

    def getACK(self):
        return self._ack

    def __iter__(self):
        self._itterIndex = 0
        return self

    def next(self):
        return self.__next__()

    def __next__(self):
        if self._itterIndex >= self._burstSize:
            raise StopIteration
        else:
            self._itterIndex+=1
            if (self._frames[self._itterIndex-1] == None):
                return self.__next__()
            else:
                return self._frames[self._itterIndex-1] 
