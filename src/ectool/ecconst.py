#!/usr/bin/python3
# -*- coding: UTF-8 -*-



# 一些常数
DLBOOT_HANDSHAKE           = (0x2b02d300)
AGBOOT_HANDSHAKE           = (0x2b02d3aa)
LPC_HANDSHAKE              = (0x2b02d3cd)

IMGH_IDENTIFIER            = (0x54494d48)
AGBT_IDENTIFIER            = (0x4F424D49)
AIMG_IDENTIFIER            = (0x444B4249)
CIMG_IDENTIFIER            = (0x43504249)
FLEX_IDENTIFIER            = (0x464c5849)
DL_COMMAND_ID              = (0xcd)
DL_N_COMMAND_ID            = (0x32)
CP_FLASH_IND               = (0xe101)

CMD_GET_VERSION = 0x20
CMD_SEL_IMAGE = 0x21
CMD_VERIFY_IMAGE = 0x22
CMD_DATA_HEAD = 0x31
CMD_DOWNLOAD_DATA = 0x32
CMD_DONE = 0x3a
CMD_DISCONNECT = 0x40
CMD_INVALID = 0xff

FIXED_PROTOCAL_RSP_LEN = 6

LPC_FLASH_ERASE = 0x10

LPC_BURN_ONE = 0x42
LPC_GET_BURN_STATUS = 0x44
LPC_SYS_RST = 0xaa

LPC_COMMAND_ID           = (0x4c)
LPC_N_COMMAND_ID         = (0xb3)  
MAX_LPC_CMD_DATA_LEN     = (0x1000)
MAX_LPC_RSP_DATA_LEN     = (0x100)
FIXED_LPC_RSP_LEN        = (6)
FIXED_LPC_CMD_LEN        = (8)

STYPE_AP_FLASH = 0x0
STYPE_CP_FLASH = 0x1

STYPE_INVALID = 0xFF

ETYPE_BLOCK = 0x0
ETYPE_CHIP = 0x1

HTYPE_NOHASH = 0x0
HTYPE_SWHASH = 0x1
HTYPE_HWHASH = 0x2

MAX_DATA_BLOCK_SIZE = 0x10000

if __name__ == "__main__" :
    file_cnt = "\n"
    with open("./resources/ec618_agentboot_usb.bin", "rb") as f :
        file_cnt += "ec618_usb = \"\"\"" + f.read().hex() + "\"\"\"\n"
    # with open("../../resources/ec618_agentboot_uart.bin", "rb") as f :
    #     file_cnt += "ec618_uart = \"" + f.read().hex() + "\"\n"
    with open("./src/ectool/ecag.py", "w") as f :
        f.write(file_cnt)
    