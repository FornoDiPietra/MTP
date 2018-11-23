#!/usr/bin/python3

def ensure_crc(crc):
    #In final designs it was found that some text inputs
    #would generate crc lengths smaller than 5 (which is the usual one),
    #so this function ensures we always send 5 bytes through the antenna.

    crc = str(crc)
    if len(crc) == 1:
        return '0000'+crc
    elif len(crc) == 2:
        return '000'+crc
    elif len(crc) == 3:
        return '00'+crc
    elif len(crc) == 4:
        return '0'+crc
    elif len(crc) == 5:
        return crc
    else:
        print('There was a problem with the number ensure_crc')

def calculate_crc(chunk):
    # This function calculates the CRC for the given data.
    return ensure_crc(crc16.crc16xmodem(chunk))
