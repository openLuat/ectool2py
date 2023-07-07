#!/usr/bin/python3
# -*- coding: UTF-8 -*-

import os, struct, sys, json, shutil, logging, hashlib, time
from serial import Serial
import serial.tools.list_ports



from ectool.ecstruct import *
from ectool.ecconst import *
from ectool.ecaction import *

import ectool.ecag as ecag

ecargs = None
logger = None

# 参考文件 https://citeseerx.ist.psu.edu/document?repid=rep1&type=pdf&doi=483a9555e446577cefc31b5629e843cc814b83cb

def ecburn_auto_select() :
    for item in serial.tools.list_ports.comports():
        if not item.pid or not item.location :
            continue
        if item.vid == 0x17D1 and item.pid == 0x0001 :
            return item.name
    return None

def cli_burn() :
    if not ecargs.file :
        logger.error("require -f/--file !!!")
        sys.exit(3)
    import ectool.unpkg as unpkg
    jdata = unpkg.binpkg_unpack(ecargs.file, outpath_dir=None, ram=True, debug=ecargs.debug)
    logger.info("Files " + json.dumps(list(jdata.keys())))
    if not ecargs.port or ecargs.port == "auto" :
        ecargs.port = None
        logger.info("Searching for USB Boot COM, max wait 120s")
        logger.info("Pls Press BOOT button and poweron/reset the module/chip")
        for i in range(1200) :
            COM = ecburn_auto_select()
            if COM :
                logger.info("Found " + COM)
                ecargs.port = COM
                break
            time.sleep(0.1)
        if ecargs.port == None :
            logger.error("timeout for searching, exit")
            sys.exit(2)
            return
    logger.info("Select " + ecargs.port)
    COM = ecargs.port

    burncom = serial.Serial(COM, baudrate=921600, timeout=1)
    burncom.dtr = 1

    logging.info("Go   Sync")
    if 0 != burn_sync(burncom, enSynHandshakeType.SYNC_HANDSHAKE_DLBOOT, 2) :
        return -1
    logging.info("Done Sync")
    
    logging.info("Go   AgentBoot download")
    # TODO 支持uart刷机
    ret = burn_agboot(burncom, bytes.fromhex(ecag.ec618_usb), 921600)
    if ret != 0 :
        logging.error("agentboot download fail")
        return ret
    logging.info("Done AgentBoot download")

    # time.sleep(1)

    logging.info("Go   BL download")
    ret = burn_img(burncom, jdata["ap_bootloader"]["data"], enBurnImageType.BTYPE_BOOTLOADER, STYPE_AP_FLASH, 0, tag="BL")
    if ret != 0 :
        logging.error("burn_img BootLoader fail")
        return ret
    logging.info("Done BL download")
    logging.info("Go   AP download")
    ret = burn_img(burncom, jdata["ap"]["data"], enBurnImageType.BTYPE_AP, STYPE_AP_FLASH, 0x24000, tag="AP")
    if ret != 0 :
        logging.error("burn_img AP fail")
        return ret
    logging.info("Done AP download")
    logging.info("Go   CP download")
    ret = burn_img(burncom, jdata["cp-demo-flash"]["data"], enBurnImageType.BTYPE_CP, STYPE_CP_FLASH, 0, tag="CP")
    if ret != 0 :
        logging.error("burn_img CP fail")
        return ret
    logging.info("Done CP download")

    ret = sys_reset(burncom)
    logging.info("sys reset " + str(ret))
    logging.info("burn ok")
        
def cli_unpack() :
    if not ecargs.file :
        logger.error("require -f/--file !!!")
        sys.exit(3)
    import ectool.unpkg as unpkg
    unpkg.binpkg_unpack(ecargs.file, ecargs.outdir)

def main() :
    global ecargs
    global logger
    import argparse
    parser = argparse.ArgumentParser(description='A tool for EC modules, like EC618')
    parser.add_argument("action", choices=["burn", "unpack"], help="main action to perform")
    parser.add_argument("--file", "-f", help="file path")
    parser.add_argument("--burn_addr",  help="burn bin file to addr")
    parser.add_argument("--img_type", "-t", choices=["BL", "CP", "AP", "FF"], help="image type for bin file")
    parser.add_argument("--sysreset", help="reset the chip after burn success", const=True, nargs="?")
    parser.add_argument("--debug", "-d", const=True, nargs="?", help="debug mode")
    parser.add_argument("--port", "-p", default="auto", nargs=1, help="COM port or path, like COM49, default is auto search")
    parser.add_argument("--outdir", "-o", default="tmp", nargs=1, help="output dir for actoion like unpack/diff")
    parser.add_argument("--allow-upload", const=True, nargs="?", help="diff action require upload binpkg/soc to remote server, add this option means you agree it")
    ecargs = parser.parse_args()
    if len(sys.argv) == 1 or not ecargs.action :
        parser.print_help()
        return
    if ecargs.debug :
        logging.basicConfig(level=logging.DEBUG)
    else :
        logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("ectool")
    logger.debug("Command Args " + str(ecargs))
    if ecargs.action == "burn" :
        cli_burn()
    elif ecargs.action == "unpack" :
        cli_unpack()
    else:
        logger.error("not support action " + ecargs.action + " yet")
        sys.exit(1)

if __name__ == "__main__":
    main()
