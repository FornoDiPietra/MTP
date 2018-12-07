import RPi.GPIO as GPIO
GPIO.setmode(GPIO.BCM)
from lib_nrf24 import NRF24
import time, sys, argparse
import spidev
from lib_protocol_shortrange import *
import os

def _BV(x):
    return 1

def setupRadio(CE):
    CHANNEL = 0x62
    POWER = NRF24.PA_MAX
    #POWER = NRF24.PA_HIGH
    #POWER = NRF24.PA_LOW
    #POWER = NRF24.PA_MIN
    DATARATE = NRF24.BR_2MBPS

    print("setup radio: CHANNEL (dec)=" + str(CHANNEL))
    print("setup radio: POWER = " + str(POWER))
    print("setup radio: DATARATE = " + str(DATARATE))


    radio = NRF24(GPIO, spidev.SpiDev())
    radio.begin(CE, 0)
    radio.setRetries(15,0)
    radio.setPayloadSize(32)
    radio.setChannel(CHANNEL)
    radio.setDataRate(DATARATE)
    radio.setPALevel(POWER)
    radio.setAutoAck(False)
    radio.write_register(NRF24.STATUS, 0x70)

    return radio

def transmit(radio, IRQ, data):
    txbuffer = [NRF24.W_TX_PAYLOAD] + data
    result =  radio.spidev.xfer2(txbuffer)

    #wait for successful sended
    while (GPIO.input(IRQ) == 1):
        time.sleep(0.0000001)
    radio.write_register(NRF24.STATUS, 0x70)

def receive(radio, IRQ, timeout):
    startTime = time.time()

    while (GPIO.input(IRQ) == 1 and (time.time()-startTime<timeout)):
        time.sleep(0.000001)

    if (GPIO.input(IRQ) == 0):
        radio.write_register(NRF24.STATUS, 0x70)

        txbuffer = [NRF24.R_RX_PAYLOAD] + ([0xFF]*32)
        payload = radio.spidev.xfer2(txbuffer)

        return payload[1:]
    else:
        return None

def CE():
    CE_TX = 19
    CE_RX = 26

    GPIO.setup(CE_TX, GPIO.OUT)
    GPIO.setup(CE_RX, GPIO.OUT)
    GPIO.output(CE_TX, GPIO.HIGH)
    GPIO.output(CE_RX, GPIO.HIGH)


def RX(config,RX_FOLDER,led_err, led_rx, led_tx, led_a1, led_a2, led_net, led_dir, btn, sw2, sw3, FILE_NAME=""):
    # Normal configuration Raspi 2
    #ADDR_TX = [0xc2, 0xc2, 0xc2, 0xc2, 0xc2]
    #ADDR_RX = [0xe7, 0xe7, 0xe7, 0xe7, 0xe7]
    ADDR_TX = [0xd3, 0xd3, 0xd3, 0xd3, 0xd3]
    ADDR_RX = [0xb9, 0xb9, 0xb9, 0xb9, 0xb9]


    print("TX addr: " + str(ADDR_TX))
    print("RX addr: " + str(ADDR_RX))

    if (config == "cfg1"):
        # CE=0/IRQ=25 belongs together
        # CE=1/IRQ=15
        CE_TX = 0
        CE_RX = 1
        IRQ_TX = 16
        IRQ_RX = 20

    else:
        # Switch Rx/Tx
        CE_TX = 1
        CE_RX = 0
        IRQ_TX = 20
        IRQ_RX = 16

    CE()


    radioRx = setupRadio(CE_RX)
    time.sleep(0.5)
    radioRx.openReadingPipe(1, ADDR_RX)
    radioRx.openReadingPipe(0, ADDR_RX)
    radioRx.startListening()


    radioTx = setupRadio(CE_TX)
    time.sleep(0.5)
    radioTx.startListening()
    radioTx.stopListening()
    time.sleep(130 / 1000000.0)

    radioTx.openWritingPipe(ADDR_TX)

    # setup the interrupts
    GPIO.setup(IRQ_TX, GPIO.IN)
    GPIO.setup(IRQ_RX, GPIO.IN)

    print("CE_TX=" + str(CE_TX))
    print("CE_RX=" + str(CE_RX))
    print("IRQ_TX=" + str(IRQ_TX))
    print("IRQ_RX=" + str(IRQ_RX))

    print(sys.version)
    #print("----Tx---------")
    #radioTx.printDetails()
    #print("----Rx---------")
    #radioRx.printDetails()


    print("init the packet stack")
    stack = PacketStack()

    led_rx.on()


    # run this to swtich the radio on and into tx mode
    radioTx.write_register(NRF24.CONFIG, (radioTx.read_register(NRF24.CONFIG) | _BV(NRF24.PWR_UP) ) & ~_BV(NRF24.PRIM_RX))
    radioTx.flush_rx()
    radioRx.flush_rx()

    maxTries = 50000
    count = 0
    fails = 0
    stats = []
    totalTime = 0
    timer1 = time.time()
    data = None
    stop = False

    print("waiting for bursts")

    try:
        while (not stop):
            count += 1

            burst = RxBurst()
            radioRx.flush_rx()
            radioRx.write_register(NRF24.STATUS, 0x70)

            while (data == None and not stop):
                data = receive(radioRx, IRQ_RX, 0.5)

                pressTime = time.time()
                if (btn.isOn()):
                    print("trying to escape Rx mode")
                    led_err.blink()
                    btn.waitForRelease()
                    led_err.off()
                    if (time.time()-pressTime > 5):
                        print("manual cancel of RX mode")
                        stop = True
                    else:
                        print("not escaped from Rx after " + str(time.time()-pressTime)+ "s")



            if (not stop):
                frame = RxFrame(data)
                burst.addFrame(frame)

                while not stop:
                    data = receive(radioRx, IRQ_RX, burst.getTimeOut())

                    if (data != None):
                        frame = RxFrame(data)
                        burst.addFrame(frame)
                    else:
                        break

                transmit(radioTx,IRQ_TX,burst.getACK())
                transmit(radioTx,IRQ_TX,burst.getACK())
                transmit(radioTx,IRQ_TX,burst.getACK())
                transmit(radioTx,IRQ_TX,burst.getACK())
                transmit(radioTx,IRQ_TX,burst.getACK())

                print("received burst: " + str(count) + " - " + str(burst.statsNumRcv) + "/256")
                if (burst.statsNumRcv < 30):
                    led_err.flash()

                stack.addBurst(burst)

                stats.append([count, burst.statsNumRcv])

                led_rx.flash()

            if (stack.isCompletlyReceived() or stop):
                if (stack.isCompletlyReceived()):
                    print("\033[92m file received!\033[0m")
                else:
                    print("canceling")

                totalTime = time.time() - timer1

                fileName = stack._packets[0].getFileName()

                if fileName == None or fileName == "":
                    fileName = "no_filename_recovered.txt"

                compression = stack._packets[0].isCompressed()
                print("recovered file name:" + fileName)

                if (FILE_NAME != ""):
                    print("saving file as " + FILE_NAME + " (specified as an argument)")
                    fileName = FILE_NAME

                tmpFileName = fileName
                if (compression):
                    tmpFileName = "tmp.7z"

                print("writing received data to file: " + tmpFileName)
                stack.writeToFile(RX_FOLDER + tmpFileName)

                if (compression):
                    print("decompressing file")
                    os.system("7z x -y -so " + RX_FOLDER + "tmp.7z > " + RX_FOLDER + fileName)
                print("file stored")
                break
    except KeyboardInterrupt:
        print("")
    finally:

        i=0
        maxPack = stack._packets[0].getFileSize()

        while (i <= maxPack):
            packet = stack._packets[i]
            if (not packet.isValid()):
                print(i)
            i+=1

        print("time elapsed: " + str(totalTime))
        print("transmitted: " + str(count))
        print("timeouts: " + str(fails))

        print("saving packet loss statistics")
        logFile = open(fileName + ".loss","w+")
        logFile.write(time.asctime( time.localtime(time.time())) + "\n")
        logFile.write("total time: " + str(totalTime) + "\n")

        logFile.write("burst_count;losses\n")
        for s in stats:
            logFile.write(str(s[0]) + ";" + str(s[1]) + "\n")
        logFile.close()

        #btn.waitForPress()
        #btn.waitForRelease()


def TX(TX_FOLDER, FILE_NAME, config, led_err, led_rx, led_tx, led_a1, led_a2, led_net, led_dir, btn, sw2, sw3, compression=False):
    # Normal configuration Raspi 2
    #ADDR_TX = [0xe7, 0xe7, 0xe7, 0xe7, 0xe7]
    #ADDR_RX = [0xc2, 0xc2, 0xc2, 0xc2, 0xc2]
    ADDR_TX = [0xb9, 0xb9, 0xb9, 0xb9, 0xb9]
    ADDR_RX = [0xd3, 0xd3, 0xd3, 0xd3, 0xd3]
    ACK_TIMEOUT = 0.2


    print("TX addr: " + str(ADDR_TX))
    print("RX addr: " + str(ADDR_RX)) 
    print("ACK_TIMEOUT: " + str(ACK_TIMEOUT))

    CE()  

    if (config == "cfg1"):
        # CE=0/IRQ=25 belongs together
        # CE=1/IRQ=15
        CE_TX = 0
        CE_RX = 1
        IRQ_TX = 16
        IRQ_RX = 20

    else:
        # Switch Rx/Tx
        CE_TX = 1
        CE_RX = 0
        IRQ_TX = 20
        IRQ_RX = 16


    radioRx = setupRadio(CE_RX)
    radioRx.openReadingPipe(1, ADDR_RX)
    radioRx.openReadingPipe(0, ADDR_RX)
    radioRx.startListening()


    radioTx = setupRadio(CE_TX)
    radioTx.startListening()
    radioTx.stopListening()
    time.sleep(130 / 1000000.0)

    radioTx.openWritingPipe(ADDR_TX)

    # setup the interrupts
    GPIO.setup(IRQ_TX, GPIO.IN)
    GPIO.setup(IRQ_RX, GPIO.IN)

    print("CE_TX=" + str(CE_TX))
    print("CE_RX=" + str(CE_RX))
    print("IRQ_TX=" + str(IRQ_TX))
    print("IRQ_RX=" + str(IRQ_RX))

    print(sys.version)
    #print("----Tx---------")
    #radioTx.printDetails()
    #print("----Rx---------")
    #radioRx.printDetails()


    print("init the packet stack")
    stack = PacketStack()

    if (compression):
        print("removing old "+ TX_FOLDER + "tmp.7z (just in case)")
        os.system("rm "+ TX_FOLDER +"tmp.7z")
        print("compressing file")
        os.system("7z a " + TX_FOLDER + "tmp.7z" + " " + FILE_NAME)
        print("reading file compressed file tmp.7z")
        stack.readFromFile(TX_FOLDER + "tmp.7z",True,FILE_NAME)
    else:
        print("reading file " + FILE_NAME)
        stack.readFromFile(FILE_NAME, False)

    led_a1.on()
    print("waiting for button press to start transmission")

    #wait for button press
    btn.waitForPress()
    btn.waitForRelease()

    led_a1.off()
    print("starting transmission")


    # run this to swtich the radio on and into tx mode
    radioTx.write_register(NRF24.CONFIG, (radioTx.read_register(NRF24.CONFIG) | _BV(NRF24.PWR_UP) ) & ~_BV(NRF24.PRIM_RX))
    radioTx.flush_rx()
    radioRx.flush_rx()

    count = 0
    ackLost = 0
    timer1 = time.time()
    stats = []
    acks = []
    stop = False

    try:
        while (not stack.isAllConfirmed() and not stop):
            timingStat = []
            count += 1

            timer2 = time.time()
            timer3 = time.time()

            burst = stack.createBurst()

            # How long did it take to create the burst?
            timingStat.append(time.time()-timer3)   
            timer3 = time.time()

            for frame in burst:
                transmit(radioTx, IRQ_TX, frame.getRawData())

            # How long did it take to transmit the burst
            timingStat.append(time.time()-timer3)
            timer3 = time.time()

            radioRx.flush_rx()
            radioRx.write_register(NRF24.STATUS, 0x70)    #clear the interrupt

            #now wait for the ACK
            data = receive(radioRx, IRQ_RX, ACK_TIMEOUT)

            # How long did we wait for the ACK
            timingStat.append(time.time() - timer3)
            timer3 = time.time()

            ack_message = ""
            if (data != None):
                burst.ACK(data,stack)
                acks.append(data)
            else:
                ack_message = " (ACK timeout)"
                ackLost+=1
                led_err.flash()

            #print(str(stack._packetCount) + " packets left" + ack_message)
            led_tx.flash()

            # How long did it take to process the ACK
            timingStat.append(time.time()-timer3)
            # How long did the whole burst transmission take?
            timingStat.append(time.time()-timer2)
            timingStat.append(count)
            timingStat.append(ackLost)

            stats.append(timingStat)

            pressTime = time.time()
            if (btn.isOn()):
                print("trying to escape Tx mode")
                led_err.blink()
                btn.waitForRelease()
                led_err.off()
                if (time.time()-pressTime > 5):
                    print("manual cancel of TX mode")
                    stop = True
                else:
                    print("not escaped from Tx after " + str(time.time()-pressTime) + "s")

        if (not stack.safeIsAllConfirmed()):
            print("not safe all confirmed!!!")

    except KeyboardInterrupt:
        print("")
    finally:

        totalTime = time.time()-timer1
        print("time elapsed: " + str(totalTime))
        print("transmitted: " + str(count))
        print("timeouts: " + str(ackLost))
        print("saving logfile to " + os.path.basename(FILE_NAME) + ".timelog")

        logFile = open(os.path.basename(FILE_NAME) + ".timelog","w+")

        logFile.write(time.asctime( time.localtime(time.time())) + "\n")
        logFile.write("total time elapsed: " + str(totalTime) + "\n")
        logFile.write("---------------------------------------\n")

        # Write the timing statistics
        logFile.write("Burst_create;Burst_transmit;ACK_wait;Process_ACK;total;burst_count;ack_timeout_count\n")
        for timingStat in stats:
            for datum in timingStat:
                logFile.write(str(datum) + ";")
            logFile.write("\n")
        logFile.close()

        print("saving ACKs to " + os.path.basename(FILE_NAME) + ".acks")
        ackFile = open(os.path.basename(FILE_NAME) + ".acks","w+")
        ackFile.write(time.asctime( time.localtime(time.time())) + "\n")
        for ack in acks:
            ackFile.write(str(ack) + "\n")
        ackFile.close()
        print("Tx finished")

        led_tx.on()