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

def ecburn_auto_select() :
    for item in serial.tools.list_ports.comports():
        if not item.pid or not item.location :
            continue
        if item.vid == 0x17D1 and item.pid == 0x0001 :
            return item.device
            # return item.name
    return None

def select_com() :
    if not ecargs.port or ecargs.port == "auto" :
        ecargs.port = None
        logger.info("Searching for USB Boot COM, max wait 120s")
        logger.info("Pls Press BOOT button and poweron/reset the module/chip")
        for i in range(1200) :
            COM = ecburn_auto_select()
            if COM :
                logger.info("Found " + str(COM))
                ecargs.port = COM
                break
            time.sleep(0.1)
        if ecargs.port == None :
            logger.error("timeout for searching, exit")
            return None
    return True

def do_agentboot(burncom) :
    
    if ecargs.burn_agent == "y" :
        logging.info("Go   AgentBoot download")
        # TODO 支持uart刷机
        ret = burn_agboot(burncom, bytes.fromhex(ecag.ec618_usb), 921600)
        if ret != 0 :
            logging.error("agentboot download fail")
            return ret
        logging.info("Done AgentBoot download")
    return 0

def cli_burn() :
    if not ecargs.file :
        logger.error("require -f/--file !!!")
        sys.exit(3)
    import ectool.unpkg as unpkg
    jdata = unpkg.binpkg_unpack(ecargs.file, outpath_dir=None, ram=True, debug=ecargs.debug)
    logger.info("Files " + json.dumps(list(jdata.keys())))
    
    if not select_com() :
        sys.exit(2)
    logger.info("Select " + ecargs.port)
    

    # burncom = serial.Serial(COM, baudrate=921600, exclusive=None, timeout=1, xonxoff=False, rtscts=False, dsrdtr=False)
    burncom = serial.Serial(ecargs.port, baudrate=921600, timeout=0.8)
    burncom.dtr = 1
    # burncom.timeout = 0.1

    logging.info("Go   Sync")
    if 0 != burn_sync(burncom, enSynHandshakeType.SYNC_HANDSHAKE_DLBOOT, 2) :
        return -1
    logging.info("Done Sync")

    if do_agentboot(burncom) != 0 :
        return -1

    while 1 :
        if "ap_bootloader" in jdata and ecargs.burn_bl == "y" :
            logging.info("Go   BL download")
            ret = burn_img(burncom, jdata["ap_bootloader"]["data"], enBurnImageType.BTYPE_BOOTLOADER, STYPE_AP_FLASH, 0, tag="BL")
            if ret != 0 :
                logging.error("burn_img BootLoader fail")
                break
            logging.info("Done BL download")
        if "ap" in jdata and ecargs.burn_ap == "y" :
            logging.info("Go   AP download")
            ret = burn_img(burncom, jdata["ap"]["data"], enBurnImageType.BTYPE_AP, STYPE_AP_FLASH, 0x24000, tag="AP")
            if ret != 0 :
                logging.error("burn_img AP fail")
                break
            logging.info("Done AP download")
        if "cp-demo-flash" in jdata and ecargs.burn_cp == "y" :
            logging.info("Go   CP download")
            ret = burn_img(burncom, jdata["cp-demo-flash"]["data"], enBurnImageType.BTYPE_CP, STYPE_CP_FLASH, 0, tag="CP")
            if ret != 0 :
                logging.error("burn_img CP fail")
                break
            logging.info("Done CP download")

        if "script" in jdata and ecargs.burn_script == "y" :
            logging.info("Do   Script download")
            ret = burn_img(burncom, jdata["script"]["data"], enBurnImageType.BTYPE_FLEXFILE, STYPE_AP_FLASH, jdata["script"]["burn_addr"], tag="SCRIPT")
            if ret != 0 :
                logging.error("burn_img SCRIPT fail")
                break
            logging.info("Done Script download")

        break

    logging.info("sys reset " + str(sys_reset(burncom)))
    if ret == 0:
        logging.info("burn ok")
    else :
        logging.info("burn fail " + str(ret))
        
def cli_unpack() :
    if not ecargs.file :
        logger.error("require -f/--file !!!")
        sys.exit(3)
    import ectool.unpkg as unpkg
    unpkg.binpkg_unpack(ecargs.file, ecargs.outdir)

def cli_erase() :
    if ecargs.erase_addr == None or ecargs.erase_size == None :
        logger.error("require --erase_addr and --erase_size  !!!")
        sys.exit(3)
    erase_addr = int(ecargs.erase_addr, 16)
    erase_size = int(ecargs.erase_size, 16)
    if erase_addr < 0 :
        return 0
    if erase_size < 0 :
        return 0
    if not select_com() :
        sys.exit(2)
    logger.info("Select " + ecargs.port)
    

    # burncom = serial.Serial(COM, baudrate=921600, exclusive=None, timeout=1, xonxoff=False, rtscts=False, dsrdtr=False)
    burncom = serial.Serial(ecargs.port, baudrate=921600, timeout=0.8)
    burncom.dtr = 1
    # burncom.timeout = 0.1

    logging.info("Go   Sync")
    if 0 != burn_sync(burncom, enSynHandshakeType.SYNC_HANDSHAKE_DLBOOT, 2) :
        return -1
    logging.info("Done Sync")
    
    if do_agentboot(burncom) != 0 :
        return -1

    ret, _ = package_lpc_erase(burncom, erase_addr, erase_size)
    logging.error("erase ret " + str(ret))
    if ret != 0 :
        logging.error("erase fail")
    logging.info("sys reset " + str(sys_reset(burncom)))

def main() :
    # print("1.2.3.4.5")
    global ecargs
    global logger
    import argparse
    parser = argparse.ArgumentParser(description='A tool for EC modules, like EC618')
    parser.add_argument("action", choices=["burn", "unpack", "erase"], help="main action to perform")
    parser.add_argument("--file", "-f", help="file path")
    parser.add_argument("--burn_addr",  help="burn bin file to addr")
    parser.add_argument("--erase_addr",  help="addr of erase actoion")
    parser.add_argument("--erase_size",  help="size of erase action")
    parser.add_argument("--burn_agent",  default="y",  choices=["y", "n"], help="burn AgentBoot, default y")
    parser.add_argument("--burn_bl",  default="y",  choices=["y", "n"], help="burn BootLoader, default y")
    parser.add_argument("--burn_ap",  default="y",  choices=["y", "n"], help="burn AP zone, default y")
    parser.add_argument("--burn_cp",  default="y",  choices=["y", "n"], help="burn CP zone, default y")
    parser.add_argument("--burn_script",  default="y",  choices=["y", "n"], help="burn Script Zone, default y")
    parser.add_argument("--img_type", "-t", choices=["BL", "CP", "AP", "FF"], help="image type for bin file")
    parser.add_argument("--sysreset", help="reset the chip after burn success", const=True, nargs="?")
    parser.add_argument("--debug", "-d", const=True, nargs="?", help="debug mode")
    parser.add_argument("--port", "-p", default="auto", help="COM port or path, like COM49, default is auto search")
    parser.add_argument("--port_type", default="USB", choices=["USB", "UART"], help="USB or UART")
    parser.add_argument("--outdir", "-o", default="tmp", help="output dir for actoion like unpack/diff")
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
    elif ecargs.action == "erase":
        cli_erase()
    else:
        logger.error("not support action " + ecargs.action + " yet")
        sys.exit(1)

if __name__ == "__main__":
    main()
