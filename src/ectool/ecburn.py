#!/usr/bin/python3
# -*- coding: UTF-8 -*-

import os, struct, sys, json, shutil, logging, hashlib, time
from serial import Serial
import serial.tools.list_ports

logging.basicConfig(level=logging.DEBUG)

from ectool.ecstruct import *
from ectool.ecconst import *
from ectool.ecaction import *

# 参考文件 https://citeseerx.ist.psu.edu/document?repid=rep1&type=pdf&doi=483a9555e446577cefc31b5629e843cc814b83cb

def ecburn(action) :
    if action == "test":
        ecburn_test()

def ecburn_auto_select() :
    for item in serial.tools.list_ports.comports():
        if not item.pid or not item.location :
            continue
        if item.vid == 0x17D1 and item.pid == 0x0001 :
            return item.name
    return None

def ecburn_test() :
    COM = None
    for i in range(10000) :
        COM = ecburn_auto_select()
        if COM :
            break
        time.sleep(0.1)

    if not COM :
        logging.error("No COM Found")
        return
    burncom = serial.Serial(COM, baudrate=921600, timeout=1)
    burncom.dtr = 1

    if 0 != burn_sync(burncom, enSynHandshakeType.SYNC_HANDSHAKE_DLBOOT, 2) :
        return -1

    ret = burn_agboot(burncom, "agentboot.bin", 921600)
    if ret != 0 :
        logging.error("agentboot download fail")
        return ret
    logging.info("agentboot download complete")

    # time.sleep(1)

    logging.info("begin BL download")

    ret = burn_img(burncom, "luatos/ap_bootloader.bin", enBurnImageType.BTYPE_BOOTLOADER, STYPE_AP_FLASH, 0)
    if ret != 0 :
        logging.error("burn_img BootLoader fail")
        return ret
    ret = burn_img(burncom, "luatos/ap.bin", enBurnImageType.BTYPE_AP, STYPE_AP_FLASH, 0x24000)
    if ret != 0 :
        logging.error("burn_img ap fail")
        return ret
    ret = burn_img(burncom, "luatos/cp-demo-flash.bin", enBurnImageType.BTYPE_CP, STYPE_CP_FLASH, 0)
    if ret != 0 :
        logging.error("burn_img cp fail")
        return ret

    ret = sys_reset(burncom)
    logging.info("sys reset " + str(ret))

def main() :
    if len(sys.argv) > 1 :
        ecburn(sys.argv[1])
    else:
        ecburn_test()

def print_help():
    print("""
Usage:
    ectool <action> [options] [args]

example:
    ectool burn example.binpkg
    ectool burn --port COM46 example.binpkg
    ectool unpack --outdir tmp example.binpkg 
    """)

if __name__ == "__main__":
    if len(sys.argv) == 1 :
        print_help()
    else :
        main()
