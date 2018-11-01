import RPi.GPIO as GPIO
GPIO.setmode(GPIO.BCM)
from lib_nrf24 import NRF24
import time
import spidev


def fillWithPadding(byteBlock, blockSize):
    while (len(byteBlock) < blockSize):
        byteBlock = byteBlock + chr(0x00)
        
    return byteBlock

def readFile(fileName, blockSize):
    blocks = []

    with open(fileName, "rb") as f:
        byteBlock = f.read(blockSize)

        while byteBlock != b'':
            if (len(byteBlock) < blockSize):
                byteBlock = fillWithPadding(byteBlock, blockSize)
            
            blocks.append(byteBlock)
            byteBlock = f.read(blockSize)
        f.close()

    return blocks

def bytesToString(bytesObj):
    formattedString = ""
    for b in bytesObj:
        s = format(ord(b), '02x')
        formattedString += '0x' + s + ' '
    return formattedString



blockSize = 32
############ setup the transceiver ##################################
radio = NRF24(GPIO, spidev.SpiDev())
radio.begin(0, 0)
# radio.write_register(0x00, 0b00001111)
# radio.write_register(0x01, 0b00000000)
# radio.write_register(0x02, 0b00000001)
# radio.write_register(0x03, 0b00000001)
# radio.write_register(0x04, 0b00000000)
# radio.write_register(0x05, 0x60)
# radio.write_register(0x06, 0b00000110)
# radio.write_register(0x0A, [0xC2, 0xC2, 0xC2], 3)
# radio.write_register(0x11, 32)

#radio.begin(0, 0) # Set spi-cs pin0, and rf24-CE pin 17
time.sleep(0.5)
radio.setRetries(15,0)
radio.setPayloadSize(blockSize)
radio.setChannel(0x60)

radio.setDataRate(NRF24.BR_2MBPS)
radio.setPALevel(NRF24.PA_MIN)

radio.setAutoAck(False)
#radio.enableDynamicPayloads() # radio.setPayloadSize(32) for setting a fixed payload
#radio.enableAckPayload()

#radio.openWritingPipe([0xe7, 0xe7, 0xe7, 0xe7, 0xe7])
radio.openReadingPipe(1, [0xC2, 0xC2, 0xC2, 0xC2, 0xC2])
radio.startListening()
radio.stopListening()
radio.printDetails()
radio.startListening()

Final_Buf = []
buf = "1"*32
c=0
failed=True
while True:
    if radio.available([0]):
        buf = []
        radio.read(buf,32)
        print(buf)

        index = buf[0]

        if index == 0:
            c=0
            Final_Buf=[]
            Final_Buf.append(buf)
            failed=False
        else:
            c+=1
            if index == c and not failed:
                Final_Buf.append(buf)
                if buf[31] == 0:
                    break
            else:
                failed=True
    #raw_input("press button")
    #radio.print_status(radio.get_status())
        
newFile = open("rec.txt","wb")

for a in Final_Buf:
    newFileByteArray = bytearray(a)
    newFile.write(newFileByteArray[1:])

newFile.close()