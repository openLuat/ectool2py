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

def ecburn_auto_select(vid=0x17D1, pid=0x0001, location=None) :
    for item in serial.tools.list_ports.comports():
        if not item.pid or not item.location :
            continue
        if item.vid == vid and item.pid == pid :
            if location :
                if item.location.find(location) >= 0 :
                    return item.device
                else :
                    continue
            return item.device
            # return item.name
    return None

def select_com(vid=0x17D1, pid=0x0001, location=None) :
    if not ecargs.port or ecargs.port == "auto" :
        ecargs.port = None
        if vid == 0x17D1 and pid == 0x0001 :
            logger.info("Searching for USB Boot COM, max wait 120s")
            logger.info("Pls Press BOOT button and poweron/reset the module/chip")
        else :
            logger.info("Searching for SoC Log COM, max wait 120s")
        for i in range(1200) :
            COM = ecburn_auto_select(vid, pid, location)
            if COM :
                logger.info("Found " + str(COM))
                ecargs.port = COM
                break
            time.sleep(0.1)
        if ecargs.port == None :
            logger.error("timeout for searching, exit")
            return None
    return True

def port_open(baudrate=0) :
    if ecargs.port_type == "usb" :
        baudrate = 921600
    else :
        baudrate = 115200
    logger.info("open port {0} {1:d} {2}".format(str(ecargs.port), baudrate, str(ecargs.port_type)))
    burncom = serial.Serial(ecargs.port, baudrate=baudrate, timeout=0.8)
    burncom.dtr = 1
    return burncom

def do_agentboot(burncom) :
    
    if ecargs.burn_agent == "y" :
        logging.info("Go   AgentBoot download")
        # TODO 支持uart刷机
        ag = None
        if ecargs.port_type == "usb" :
            ag = bytes.fromhex(ecag.ec618_usb)
        else :
            ag = bytes.fromhex(ecag.ec618_uart)
        ret = burn_agboot(burncom, ag, 921600)
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

    if str(ecargs.file).startswith("http://") or str(ecargs.file).startswith("https://") :
        logger.info("downloading ... " + ecargs.file)
        import requests
        resp = requests.get(ecargs.file)
        if resp.status_code != 200 :
            logger.error("http resp {}".format(resp.status_code))
            sys.exit(4)
        fdata = resp.content
        logger.info("size {}".format(len(fdata)))
        jdata = unpkg.binpkg_unpack(fdata, outpath_dir=None, ram=True, debug=ecargs.debug)
    else :
        jdata = unpkg.binpkg_unpack(ecargs.file, outpath_dir=None, ram=True, debug=ecargs.debug)
    logger.info("Files " + json.dumps(list(jdata.keys())))
    
    if not select_com() :
        sys.exit(2)
    logger.info("Select " + ecargs.port)
    

    # burncom = serial.Serial(COM, baudrate=921600, exclusive=None, timeout=1, xonxoff=False, rtscts=False, dsrdtr=False)
    burncom = port_open()
    # burncom.timeout = 0.1

    logging.info("Go   Sync")
    if 0 != burn_sync(burncom, enSynHandshakeType.SYNC_HANDSHAKE_DLBOOT, 2) :
        return -1
    logging.info("Done Sync")

    if do_agentboot(burncom) != 0 :
        return -1

    # 根据image_type得出各分区的名称
    BL_NAME = None
    CP_NAME = None
    AP_NAME = None
    for name in jdata :
        if not "data" in jdata[name] :
            continue
        if jdata[name]["image_type"] == "BL" :
            BL_NAME = name
        if jdata[name]["image_type"] == "CP" :
            CP_NAME = name
        if jdata[name]["image_type"] == "AP" :
            if name == "script" :
                continue
            else :
                AP_NAME = name

    while 1 :
        if BL_NAME and ecargs.burn_bl == "y" :
            logging.info("Go   BL download")
            ret = burn_img(burncom, jdata[BL_NAME]["data"], enBurnImageType.BTYPE_BOOTLOADER, STYPE_AP_FLASH, 0, tag="BL")
            if ret != 0 :
                logging.error("burn_img BootLoader fail")
                break
            logging.info("Done BL download")
        if AP_NAME and ecargs.burn_ap == "y" :
            logging.info("Go   AP download")
            ret = burn_img(burncom, jdata[AP_NAME]["data"], enBurnImageType.BTYPE_AP, STYPE_AP_FLASH, 0x24000, tag="AP")
            if ret != 0 :
                logging.error("burn_img AP fail")
                break
            logging.info("Done AP download")
        if CP_NAME and ecargs.burn_cp == "y" :
            logging.info("Go   CP download")
            ret = burn_img(burncom, jdata[CP_NAME]["data"], enBurnImageType.BTYPE_CP, STYPE_CP_FLASH, 0, tag="CP")
            if ret != 0 :
                logging.error("burn_img CP fail")
                break
            logging.info("Done CP download")

        if "script" in jdata and ecargs.burn_script == "y" :
            logging.info("Do   Script download")
            burn_addr = jdata["script"]["burn_addr"]
            if burn_addr < 0x800000 :
                burn_addr += 0x800000
            ret = burn_img(burncom, jdata["script"]["data"], enBurnImageType.BTYPE_FLEXFILE, STYPE_AP_FLASH, burn_addr, tag="SCRIPT")
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
    burncom = port_open()
    # burncom.timeout = 0.1

    logging.info("Go   Sync")
    if 0 != burn_sync(burncom, enSynHandshakeType.SYNC_HANDSHAKE_DLBOOT, 2) :
        return -1
    logging.info("Done Sync")
    
    if do_agentboot(burncom) != 0 :
        return -1

    if ecargs.port_type == "uart" :
        burncom.close()
        time.sleep(0.5)
        burncom = port_open(921600)

    if erase_addr < 0x800000 :
        erase_addr += 0x800000
    ret = burn_sync(burncom, enSynHandshakeType.SYNC_HANDSHAKE_LPC, 2)
    if ret != 0 :
        logging.error("lpc sync fail")
    else :
        remain = erase_size
        while remain > 0 :
            if remain < 0x400 :
                ret, _ = package_lpc_erase(burncom, erase_addr, remain)
                remain = 0
            else :
                ret, _ = package_lpc_erase(burncom, erase_addr, 0x400)
                erase_addr += 0x400
                remain -= 0x400
            logging.error("erase 0x{0:X} 0x{1:X} {2:X}".format(erase_addr, erase_size, ret))
            if ret != 0 :
                logging.error("erase fail")
                break
    logging.info("sys reset " + str(sys_reset(burncom)))

def cli_logs():
    
    if not select_com(vid=0x19d1, pid=0x0001, location="x.2") :
        sys.exit(2)
    logger.info("Select " + ecargs.port)
    logcom = port_open()
    logcom.dtr = 1
    logcom.timeout = 0.1
    logcom.write(bytearray.fromhex("7E00007E"))
    import ectool.eclogs
    ctx = {}
    while 1 :
        data = logcom.read(512)
        if data :
            # logger.debug("LOGCOM " + data.hex().upper())
            msgs = ectool.eclogs.log_parse(ctx, data)
            # print("log ?? " + str(msgs))
            if msgs and len(msgs) > 0 :
                for msg in msgs :
                    logger.info(msg)

def main() :
    # print("1.2.3.4.5")
    global ecargs
    global logger
    import argparse
    parser = argparse.ArgumentParser(description='A tool for EC modules, like EC618')
    parser.add_argument("action", choices=["burn", "unpack", "erase", "logs"], help="main action to perform")
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
    parser.add_argument("--port_type", default="usb", choices=["usb", "uart"], help="USB or UART")
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
    elif ecargs.action == "logs" :
        cli_logs()
    else:
        logger.error("not support action " + ecargs.action + " yet")
        sys.exit(1)

if __name__ == "__main__":
    main()
