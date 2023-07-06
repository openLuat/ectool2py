#!/usr/bin/python3
# -*- coding: UTF-8 -*-

import os, struct, sys, json, shutil, logging, hashlib, time
from serial import Serial
import serial.tools.list_ports

import cstruct
from ectool.ecconst import *


class stCmd(cstruct.MemCStruct):
    __byte_order__ = cstruct.LITTLE_ENDIAN
    __def__ = """
        struct {
            uint8_t cmd;
            uint8_t index;
            uint8_t order_id;
            uint8_t norder_id;
            uint32_t  len;
            //uint8_t data[4];
            //uint32_t  fcs;
        }
    """

class stRsp(cstruct.MemCStruct):
    __byte_order__ = cstruct.LITTLE_ENDIAN
    __def__ = """
        struct {
            uint8_t cmd;
            uint8_t index;
            uint8_t order_id;
            uint8_t norder_id;
            uint8_t state;
            uint8_t  len;
            //uint8_t data[12];   
            //uint32_t  fcs;
        }
    """

class stLpcCmd(cstruct.MemCStruct):
    __byte_order__ = cstruct.LITTLE_ENDIAN
    __def__ = """
        struct {
    uint8_t cmd;
    uint8_t index;
    uint8_t order_id;
    uint8_t norder_id;
    uint32_t  len;
    //uint8_t data[MAX_LPC_CMD_DATA_LEN];
    //uint32_t  fcs;
        }
    """

class stlpcRsp(cstruct.MemCStruct):
    __byte_order__ = cstruct.LITTLE_ENDIAN
    __def__ = """
        struct {
    uint8_t cmd;
    uint8_t index;
    uint8_t order_id;
    uint8_t norder_id;
    uint8_t state;
    uint8_t  len;
    //uint8_t data[MAX_LPC_RSP_DATA_LEN];   
    //uint32_t  fcs;
        }
    """


class stVersionInfo(cstruct.MemCStruct):
    __byte_order__ = cstruct.LITTLE_ENDIAN
    __def__ = """
        struct {
    uint32_t vVal;     
    uint32_t id; 
    uint32_t dtm; 
    uint32_t rsvd;
        }
    """
class stCtlInfo(cstruct.MemCStruct):
    __byte_order__ = cstruct.LITTLE_ENDIAN
    __def__ = """
        struct {
    uint8_t hashtype;  
    uint8_t loadtype;
    uint16_t baudratectrl; 
        }
    """
class stImgBody(cstruct.MemCStruct):
    __byte_order__ = cstruct.LITTLE_ENDIAN
    __def__ = """
        struct {
    uint32_t id;
    uint32_t burnaddr;
    uint32_t ldloc;
    uint32_t img_size;
    uint8_t  reserve[16];
    uint8_t  hashv[32];
    uint8_t  ecdsasign[64];
    uint8_t  pubkey[64];
        }
    """
class stReservedArea(cstruct.MemCStruct):
    __byte_order__ = cstruct.LITTLE_ENDIAN
    __def__ = """
        struct {
    uint32_t rsvdAreaId;
    uint32_t rsvdAreaSize;
    uint8_t  rsvd[8];
        }
    """
class stImgHead(cstruct.MemCStruct):
    __byte_order__ = cstruct.LITTLE_ENDIAN
    __def__ = """
        struct {
    struct stVersionInfo  verinfo;
    uint32_t       imgnum;
    struct stCtlInfo      ctlinfo;
    uint32_t       rsvd0; 
    uint32_t       rsvd1;
    uint8_t        hashih[32];
    struct stImgBody      imgbody;
    struct stReservedArea rsvdarea; 
        }
    """

class enBurnImageType(cstruct.CEnum) :
    __byte_order__ = cstruct.LITTLE_ENDIAN
    __size__ = 4
    __def__ = """
enum {
    BTYPE_BOOTLOADER = 0,
    BTYPE_AP,
    BTYPE_CP,
    BTYPE_FLEXFILE,

    BTYPE_HEAD,
    BTYPE_AGBOOT,
    BTYTE_DLBOOT,
    BTYPE_INVALID
}
    """

class enSynHandshakeType(cstruct.CEnum) :
    __byte_order__ = cstruct.LITTLE_ENDIAN
    __size__ = 4
    __def__ = """
enum {
    SYNC_HANDSHAKE_DLBOOT = 0x0,
    SYNC_HANDSHAKE_AGBOOT,
    SYNC_HANDSHAKE_LPC
}
    """

# def main() :
#     print(stCmd())
#     print(stRsp())
#     imgHead = stImgHead()
#     imgHead.verInfo.vVal = 0x10000001
#     print(imgHead.pack().hex())

def create_imgHead():
    imgHead = stImgHead()
    imgHead.verinfo.vVal = 0x10000001
    imgHead.verinfo.id = IMGH_IDENTIFIER
    imgHead.verinfo.dtm = 0x20180507
    imgHead.imgnum = 1
    imgHead.ctlinfo.hashtype = 0xee
    imgHead.imgbody.id = AGBT_IDENTIFIER
    imgHead.imgbody.ldloc = 0x04010000
    return imgHead

def create_cmd(id, data=bytes()) :
    pCmd = stCmd()
    pCmd.cmd = id
    pCmd.order_id = DL_COMMAND_ID
    pCmd.norder_id = DL_N_COMMAND_ID
    pCmd.len = len(data)
    return pCmd

def create_cmd_lpc(id, data=bytes()) :
    pCmd = stLpcCmd()
    pCmd.cmd = id
    pCmd.order_id = LPC_COMMAND_ID
    pCmd.norder_id = LPC_N_COMMAND_ID
    pCmd.len = len(data)
    return pCmd

def get_imageid(id) :
    if id == "BL" or id == "AG" or id == enBurnImageType.BTYPE_BOOTLOADER or id == enBurnImageType.BTYPE_AGBOOT :
        return AGBT_IDENTIFIER
    if id == "AP" or id == enBurnImageType.BTYPE_AP:
        return AIMG_IDENTIFIER
    if id == "CP" or id == enBurnImageType.BTYPE_CP:
        return CIMG_IDENTIFIER
    if id == "FF" or id == enBurnImageType.BTYPE_FLEXFILE:
        return FLEX_IDENTIFIER
    if id == "HEAD" or id  == "DLBOOT" or id == enBurnImageType.BTYPE_HEAD or id == enBurnImageType.BTYPE_DLBOOT:
        return IMGH_IDENTIFIER
    return 0xFFFFFFFF

def package_with_crc(cmd,mask,data):
    pkgLen = len(data)
    import binascii
    pkg = struct.pack('>I',cmd) + struct.pack('<I',pkgLen) + data
    pkg = pkg + struct.pack('<I', binascii.crc32(pkg)&0xFFFFFFFF)

    pkg = bytearray(pkg)
    pkg[6] = (mask >> 8) & 0xFF
    pkg[7] = (mask >> 0) & 0xFF

    return pkg

# https://gist.github.com/eaydin/768a200c5d68b9bc66e7
def crc8_maxim(stream):
    crc = 0
    for c in stream:
        for i in range(0, 8):
            b = (crc & 1) ^ ((( int(c) & (1 << i))) >> i)
            crc = (crc ^ (b * 0x118)) >> 1
    return crc

if __name__ == "__main__":
    
    print(stCmd())
    print(stRsp())
    imgHead = create_imgHead()
    print(imgHead.pack().hex())
    print(enBurnImageType.BTYPE_AP)

    # 42004CB30400009E494D424F2E82DA6C
    # 42004CB3040000AB494D424F2E82DA6C
    tmp = package_with_crc(0x42004CB3,0x009E,struct.pack('>I',0x494D424F))
    print(tmp.hex().upper())
    print(imgHead.__size__)