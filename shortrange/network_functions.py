import nw_unified as nw
import os
import time

def runNetworkmode(leds,SW2,SW3,BTN):
    global deviceID
    filePath = '/home/pi/lib_nrf24/nw-file.txt'

    if (SW3.isOn()):
        nw.deviceID = 0
        leds[3].on()
        leds[4].off()
    else:
        nw.deviceID = 4
        leds[4].on()
        leds[3].off()

    print("Network mode address: " + str(nw.getDeviceID()))

    if os.path.isfile(filePath) == True:

        leds[2].blink()

        BTN.waitForPress()
        BTN.waitForRelease()

        leds[2].on()

        nw.main_Source()

    else:

        leds[1].on()
        print("network_functions: launching main_Repeater")
        nw.main_Repeater()
        time.sleep(2)

        leds[1].off()
        leds[2].on()
        nw.main_Source()