#!/usr/bin/python3
# -*- coding: UTF-8 -*-

import os, struct, sys, json, shutil, logging, hashlib, time
from serial import Serial
import serial.tools.list_ports
import zlib, platform

from ectool.ecstruct import *
from ectool.ecconst import *

COM_DEBUG = False
COM_DEBUG_FILE = False

is_win32 = platform.platform().upper() == "WINDOWS"

def com_write(burncom, data) :
    if COM_DEBUG :
        logging.debug(" == COM WRITE: " + data.hex().upper())
    if COM_DEBUG_FILE :
        with open("COM.txt", "a+") as f :
            f.write("-->({0}) {1}\n".format(len(data), data.hex().upper()))
    if is_win32 or len(data) <= 64 :
        burncom.write(data)
    else :
        remain = len(data)
        offset = 0
        while remain > 0 :
            if remain > 64 :
                burncom.write(data[offset:offset+64])
                offset += 64
                remain -= 64
                time.sleep(0.001)
            else :
                burncom.write(data[offset:])
                break

def com_read(burncom, slen) :
    if slen < 1 :
        return None
    recv = burncom.read(slen)
    if COM_DEBUG :
        if recv :
            logging.debug(" == COM READ : " + recv.hex().upper())
        else :
            logging.debug(" == COM READ None " + str(slen))
    if recv and COM_DEBUG_FILE :
        with open("COM.txt", "a+") as f :
            f.write("<--({0}) {1}\n".format(len(recv), recv.hex().upper()))
    return recv

def burn_sync(burncom, pType, counter) :
    logging.debug("burn_sync " + str(pType) + " " + str(counter))
    handshake = None
    if pType == enSynHandshakeType.SYNC_HANDSHAKE_DLBOOT :
        handshake = DLBOOT_HANDSHAKE
    elif pType == enSynHandshakeType.SYNC_HANDSHAKE_AGBOOT:
        handshake = AGBOOT_HANDSHAKE
    elif pType == enSynHandshakeType.SYNC_HANDSHAKE_LPC:
        handshake = LPC_HANDSHAKE
    else :
        logging.warn('unkown sync')
        return 0
    if not burncom :
        return 0
    send_buff = struct.pack("<I", handshake)
    for i in range(50) :
        for j in range(counter) :
            com_write(burncom, send_buff)
            time.sleep(0.002)
        recv_buff = com_read(burncom, 4)
        if recv_buff:
            if pType == enSynHandshakeType.SYNC_HANDSHAKE_DLBOOT :
                tmp = com_read(burncom, 1)
                if tmp and tmp[0] != 0 :
                    continue
            if send_buff == recv_buff :
                logging.debug("sync done")
                return 0

    logging.error("sync fail")
    return -1

def burn_agboot(burncom, path_or_data, baud, hashtype=None, pullupQspi=1):
    logging.debug("Burn agent boot start")
    ret = package_base_info(burncom, get_imageid(enBurnImageType.BTYPE_HEAD))
    if ret != 0:
        return ret
    if path_or_data.__class__.__name__ == "bytes" :
        fdata = path_or_data
    else :
        with open(path_or_data, "rb") as f :
            fdata = f.read()
    logging.debug("agentboot file size " + str(len(fdata)))
    ret = package_image_head(burncom, fdata, enBurnImageType.BTYPE_AGBOOT, 0)
    if ret != 0:
        return ret
    ret = burn_sync(burncom, enSynHandshakeType.SYNC_HANDSHAKE_DLBOOT, 2)
    if ret != 0:
        return ret
    ret = package_base_info(burncom, get_imageid(enBurnImageType.BTYPE_BOOTLOADER))
    if ret != 0:
        return ret
    pCmd = create_cmd(CMD_DOWNLOAD_DATA)
    pCmd.len = len(fdata)
    ret = package_data(burncom, pCmd, fdata, pullupQspi=1)
    if ret != 0:
        return ret

    return 0

def burn_img(burncom, path_or_data, img_type, storType, addr, tag="NAME"):
    logging.debug("Burn image start " + str(img_type))
    # 1. 先执行一次 LPC Sync
    ret = burn_sync(burncom, enSynHandshakeType.SYNC_HANDSHAKE_LPC, 2)
    if ret != 0 :
        logging.error("lpc sync fail")
        return -1
    # 2. lpc burn one
    ret, _ = package_lpc_burn_one(burncom, img_type, storType)
    if ret != 0 :
        logging.error("package_lpc_burn_one fail")
        return -1
    # 执行两次 AgentBoot Sync
    ret = burn_sync(burncom, enSynHandshakeType.SYNC_HANDSHAKE_AGBOOT, 2)
    if ret != 0 :
        logging.error("agentboot(0) sync fail")
        return -1
    ret = burn_sync(burncom, enSynHandshakeType.SYNC_HANDSHAKE_AGBOOT, 2)
    if ret != 0 :
        logging.error("agentboot(1) sync fail")
        return -1
    ret = package_base_info(burncom, enBurnImageType.BTYPE_HEAD, False)
    if ret != 0 :
        logging.error("package_base_info fail")
        return -1
    
    if path_or_data.__class__.__name__ == "bytes" :
        fdata = path_or_data
    else :
        with open(path_or_data, "rb") as f :
            fdata = f.read()
    ret = package_image_head(burncom, fdata, img_type, addr, baud=0, bDlBoot=False, pullupQspi=0)
    if ret != 0 :
        logging.error("package_image_head fail")
        return -1

    remain = len(fdata)
    data_offset = 0
    data_len = 0
    # time.sleep(1)
    # recv_buff = com_read(burncom, 32)
    # if recv_buff :
    #     logging.debug("wtf " + recv_buff.hex().upper())
    logging.debug("start send file data ....")
    while remain > 0 :
        ret = burn_sync(burncom, enSynHandshakeType.SYNC_HANDSHAKE_AGBOOT, 2)
        if ret != 0:
            logging.error("burn_sync fail")
            break
        if remain > MAX_DATA_BLOCK_SIZE :
            data_len = MAX_DATA_BLOCK_SIZE
        else :
            data_len = remain

        pCmd = create_cmd(CMD_DOWNLOAD_DATA)
        pCmd.len = data_len
        ret = package_data(burncom, pCmd, fdata[data_offset:data_offset + data_len], False)
        if ret != 0:
            logging.error("package_data fail")
            break

        data_offset += data_len
        remain -= data_len
        logging.info("downloading " + tag + " " + str(int(data_offset*100/len(fdata))) + "%")
    logging.debug("almost done burn_img")
    if ret == 0 :
        ret, tmpdata = package_lpc_get_burn_status(burncom)
    logging.info("downloading " + tag + " 100%")
    return ret


def sys_reset(burncom) :
    ret = burn_sync(burncom, enSynHandshakeType.SYNC_HANDSHAKE_LPC, 2)
    if ret != 0 :
        logging.error("sys_reset fail")
        return -1
    return package_lpc_sys_reset(burncom)

def package_lpc_sys_reset(burncom) :
    pCmd = create_cmd_lpc(LPC_SYS_RST)
    ret, data = send_recv_lpcCmd(burncom, pCmd, bytes())
    logging.debug("lpc_sys_reset " + str(ret))
    if ret == 0 and data == b'ZzZzZzZz':
        return 0, data
    return -1, data

def package_lpc_get_burn_status(burncom):
    pCmd = create_cmd_lpc(LPC_GET_BURN_STATUS)
    ret, data = send_recv_lpcCmd(burncom, pCmd, bytes())
    logging.debug("lpc_get_burn_status " + str(ret))
    if ret == 0 and data == b'\0\0\0\0':
        return 0, data
    return -1, data

def package_lpc_erase(burncom, addr, slen):
    pCmd = create_cmd_lpc(LPC_FLASH_ERASE)
    pCmd.len = 8
    ret, data = send_recv_lpcCmd(burncom, pCmd, struct.pack("<II", slen, addr))
    return ret, data

def package_lpc_burn_one(burncom, img_type, storType) :
    pCmd = create_cmd_lpc(LPC_BURN_ONE)
    imgId = get_imageid(img_type)
    data = None
    if storType == STYPE_CP_FLASH :
        data = struct.pack("<IH", imgId, CP_FLASH_IND)
        pCmd.len = 6
    else :
        data = struct.pack("<I", imgId)
        pCmd.len = 4
    logging.debug("lpc burn one %s %s" % (str(img_type), str(pCmd.len)))
    ret, data = send_recv_lpcCmd(burncom, pCmd, data)
    logging.debug("lpc_burn_one " + str(ret))
    return ret, data

def self_def_check1(pCmd, data):
    ckVal = pCmd.cmd + pCmd.index + pCmd.order_id + pCmd.norder_id + (pCmd.len & 0xff) + ((pCmd.len>>8)&0xff) + ((pCmd.len>>16)&0xff) + ((pCmd.len>>24)&0xff)
    for k in data :
        ckVal += k
        ckVal = ckVal & 0xFFFFFFFF
    ckVal = ckVal & 0xFFFFFFFF
    logging.debug("self_def_check1 " + str("%08X" % (ckVal, )))

    return struct.pack("<I", ckVal)

def send_recv_Cmd(burncom, cmd, data, bDlBoot=True):
    tmpdata = cmd.pack()
    logging.debug("CMD " + tmpdata.hex().upper())
    tmpdata += data
    if not bDlBoot :
        ckVal = zlib.crc32(tmpdata)
        if cmd.len > 0 :
            tmplen = cmd.len & 0xFFFFFF
            tmp = crc8_maxim(struct.pack("<I", tmplen)[:3])
            cmd.len = (tmp << 24) + tmplen
            tmpdata = cmd.pack() + data
        tmpdata += struct.pack("<I", ckVal)
    elif cmd.cmd == CMD_DOWNLOAD_DATA :
        tmpdata += self_def_check1(cmd, data)
    com_write(burncom, tmpdata)
    time.sleep(0.002)
    recv_buff = com_read(burncom, FIXED_PROTOCAL_RSP_LEN)
    if not recv_buff :
        logging.warning("read resp timeout!!")
        return -1, None
    logging.debug("rsp buff " + recv_buff.hex())
    rsp = stRsp()
    rsp.unpack(recv_buff)
    logging.debug("rsp.len " + str(rsp.len))
    recv_buff = None
    if rsp.len > 0:
        recv_buff = com_read(burncom, rsp.len)
    if not bDlBoot :
        crc32_buff = com_read(burncom, 4)# 读CRC32, TODO 校验一下
        logging.debug("read crc32 " + crc32_buff.hex().upper())
    if rsp.state != 0 :
        logging.warning("read resp not ACK " + str(rsp.state))
        if recv_buff :
            logging.warning("read resp not ACK data " + recv_buff.hex().upper())
        return -2, None
    if recv_buff:
        logging.debug("send_recv_Cmd " + str(0) + " " + recv_buff.hex().upper())
    return 0, recv_buff

def send_recv_lpcCmd(burncom, cmd, data, bDlBoot=True):
    logging.debug("CMD lpc " + cmd.pack().hex().upper())
    # 首先, 计算crc32
    ckVal = zlib.crc32(cmd.pack() + data)
    # tmpdata = cmd.pack() + data + struct.pack("<I", ckVal)
    if cmd.len > 0 :
        tmplen = cmd.len & 0xFFFFFF
        cmd.len = (crc8_maxim(struct.pack("<I", tmplen)[:3]) << 24) + tmplen
    com_write(burncom, cmd.pack() + data + struct.pack("<I", ckVal))
    recv_buff = com_read(burncom, 6)
    if recv_buff :
        logging.debug("rsp buff " + recv_buff.hex())
        rsp = stlpcRsp()
        rsp.unpack(recv_buff)
        logging.debug("lpc rsp " + str(rsp.state) + " " + str(rsp.len))
        if rsp.len > 0 :
            recv_buff = com_read(burncom, rsp.len)
        crc32_buff = com_read(burncom, 4)
        if crc32_buff :
            logging.debug("lpc rsp CRC32 " + crc32_buff.hex().upper())
        if rsp.state != 0 :
            logging.warning("read lpc rsp not ACK " + str(rsp.state))
            return -2, recv_buff
    return 0, recv_buff
    
def package_data_head(burncom, remainSize, bDlBoot = True, pullupQspi=1) :
    logging.debug("CALL package_data_head remainSize " + ("%08X" % (remainSize)))
    pCmd = stCmd()
    pCmd.cmd = CMD_DATA_HEAD
    pCmd.index = 0
    pCmd.order_id = DL_COMMAND_ID
    pCmd.norder_id = DL_N_COMMAND_ID
    pCmd.len = 4
    tmpdata = struct.pack("<I", remainSize)
    ok, recv = send_recv_Cmd(burncom, pCmd, tmpdata, bDlBoot)
    logging.debug("package_data_head " + str(ok))
    if ok == 0 :
        tbsize = struct.unpack("<I", recv)[0]
        logging.debug("package_data_head tbsize " + ("%08X" % (tbsize)) + " remainSize " + ("%08X" % (remainSize)))
        return ok, tbsize
    return ok, 0

def package_data_single(burncom, pCmd, data, bDlBoot = True):
    logging.debug("CALL package_data_single data " + str(len(data)))
    pCmd.len = len(data)
    ok, data = send_recv_Cmd(burncom, pCmd, data, bDlBoot)
    logging.debug("package_data_single " + str(ok))
    return ok, data

def package_done(burncom, bDlBoot=True) :
    pCmd = stCmd()
    pCmd.cmd = CMD_DONE
    pCmd.index = 0
    pCmd.order_id = DL_COMMAND_ID
    pCmd.norder_id = DL_N_COMMAND_ID
    pCmd.len = 0

    ok, data = send_recv_Cmd(burncom, pCmd, bytes(), bDlBoot)
    logging.debug("CALL package_done " + str(ok))
    return ok, data

def package_data(burncom, pCmd, data, bDlBoot=True, pullupQspi=1) :
    logging.debug("CALL package_data ====================")
    if burncom == None:
        return 0
    data_offset = 0
    remainSize = len(data)
    counter = 0
    ret = 0
    # logging.debug(">>> " + str(remainSize))
    while remainSize > 0 :
        ok, tbSize = package_data_head(burncom, remainSize, bDlBoot, pullupQspi)
        if ok != 0:
            return -1
        pCmd.index = counter
        pCmd.len = tbSize
        if tbSize >= remainSize :
            logging.debug("final data packet")
            ret, _ = package_data_single(burncom, pCmd, data[data_offset:], bDlBoot)
            break
        tmpdata = data[data_offset:data_offset + tbSize]
        ret, _ = package_data_single(burncom, pCmd, tmpdata, bDlBoot)
        if ret != 0:
            break
        counter += 1
        data_offset += tbSize
        remainSize -= tbSize
    logging.debug("package_data almost end " + str(ret))
    if ret == 0 :
        ret, _ = package_done(burncom, bDlBoot)
    return ret

def package_image_head(burncom, fdata, image_type, addr, baud=921600, pullupQspi=1, bDlBoot=True):
    logging.debug("CALL package_image_head")
    fhash = hashlib.sha256(fdata).digest()
    imgHd = create_imgHead()
    imgHd.imgbody.id = get_imageid(image_type)
    imgHd.imgbody.img_size = len(fdata)
    imgHd.imgbody.burnaddr = addr
    imgHd.imgbody.hashv = fhash
    # if image_type == "AG" or image_type == enBurnImageType.BTYPE_AGBOOT :
    if baud != 0 :
        imgHd.ctlinfo.baudratectrl = int(((baud/100)) + 0x8000)
    else :
        imgHd.ctlinfo.baudratectrl = 0
        # imgHd.ctlinfo.baudratectrl = 9216 + 0x8000
    imgHd.ctlinfo.hashtype = 0xee
    imgHd.rsvd0 = pullupQspi
    imgHdHash = hashlib.sha256(imgHd.pack()).digest()
    imgHd.hashih = imgHdHash

    pCmd = create_cmd(CMD_DOWNLOAD_DATA)
    tmpdata = imgHd.pack()
    pCmd.len = len(tmpdata)

    # logging.debug(tmpdata.hex())
    if 0 != package_data(burncom, pCmd, tmpdata, bDlBoot) :
        logging.error("package_image_head fail!!!")
        return -1
    return 0

#-----------------------------------
# 以下3个是必须的操作
#-----------------------------------

def package_get_version(burncom, bDlBoot=True) :
    logging.debug("package_get_version ------->")
    pCmd = create_cmd(CMD_GET_VERSION)
    ok, data = send_recv_Cmd(burncom, pCmd, bytes(), bDlBoot)
    logging.debug("package_get_version " + str(ok))
    if ok == 0 and data :
        logging.debug("get_version " + data.hex())
    return ok

def package_sel_image(burncom, img_type, bDlBoot=True) :
    logging.debug("package_sel_image ------->")
    pCmd = create_cmd(CMD_SEL_IMAGE)
    ok, data = send_recv_Cmd(burncom, pCmd, bytes(), bDlBoot)
    logging.debug("package_sel_image " + str(ok))
    if ok == 0 and data :
        ck_img = struct.unpack("<I", data)[0]
        if img_type < 10 :
            img_type = get_imageid(img_type)
        logging.debug("%08X %08X" % (img_type, ck_img))
        if img_type == ck_img :
            return 0
        logging.error("package_sel_image NOT match")
    return -1

def package_verify_image(burncom, bDlBoot=True) :
    logging.debug("package_verify_image ------->")
    pCmd = create_cmd(CMD_VERIFY_IMAGE)
    ok, data = send_recv_Cmd(burncom, pCmd, bytes(), bDlBoot)
    logging.debug("package_verify_image " + str(ok))
    if ok == 0 and data :
        logging.debug("verify_image " + data.hex())
    return ok

# 三个操作按顺序发送
def package_base_info(burncom, img_type, bDlBoot=True) :
    if package_get_version(burncom, bDlBoot) != 0 :
        return -1
    if package_sel_image(burncom, img_type, bDlBoot) != 0 :
        return -1
    if package_verify_image(burncom, bDlBoot) != 0 :
        return -1
    return 0