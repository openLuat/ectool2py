
#!/usr/bin/python3
# -*- coding: UTF-8 -*-

import os, struct, sys, json, shutil, logging, hashlib, time
from serial import Serial

# 7E 59 99 02 00 00 00 00 00 4C EA 73 0A 25 2E 2A 73 00 00 00 00 1C 00 00 00 49 2F 75 73 65 72 2E 47 50 49 4F 09 47 6F 20 47 6F 20 47 6F 09 30 09 45 43 36 31 38 7E

def main() :
    ctx = {}
    # 首先, 数据以 0x7E 开始和结束
    # 然后, 对数据内的 7E 7D 进行逆转义
    data = "7E 59 99 02 00 00 00 00 00 4C EA 73 0A 25 2E 2A 73 00 00 00 00 1C 00 00 00 49 2F 75 73 65 72 2E 47 50 49 4F 09 47 6F 20 47 6F 20 47 6F 09 30 09 45 43 36 31 38 7E"
    data = data.replace(" ", "")
    print(data)
    tmpdata = bytearray.fromhex(data)
    if tmpdata.startswith(b'\x7E') and tmpdata.endswith(b'\x7E') :
        print("Good log data")
    else :
        return
    tmpdata = tmpdata[1:-1]
    print(tmpdata.hex().upper())
    print(len(tmpdata))
    
    tmp_head1 = tmpdata[:4]
    tmp_head2 = tmpdata[4:8]
    tmp_head3 = tmpdata[8:12]
    tmpdata = tmpdata[12:]

    # 第一段是fmt的字符串, 4字节对齐, 0x00结尾
    fmt = ""
    for i in range(len(tmpdata)) :
        if tmpdata[i] == 0 :
            fmt = tmpdata[:i].decode("UTF-8")
            tmpdata = tmpdata[(i+4) & 0xC:]
            break
    print(fmt)
    print(tmpdata.hex().upper())
    if fmt == "%.*s" :
        print(tmpdata[4:].decode("UTF-8"))
    else :
        print("not support log fmt yet " + fmt)

    tmp = bytearray.fromhex("7E7D017D027E")
    print(tmp.hex().upper())
    print(log_unpack(tmp).hex().upper())

def log_unpack(data) :
    tmp = bytearray()
    count = len(data)
    offset = 0
    while offset < count :
        if data[offset] == 0x7D :
            if data[offset+1] == 0x01 :
                tmp.append(0x7D)
            elif data[offset+1] == 0x02 :
                tmp.append(0x7F)
            offset += 1
        else :
            tmp.append(data[offset])
        offset += 1
    return tmp

def log_split(tmpdata) :
    tmp_head1 = tmpdata[:4]
    tmp_head2 = tmpdata[4:8]
    tmp_head3 = tmpdata[8:12]
    tmpdata = tmpdata[12:]

    # 第一段是fmt的字符串, 4字节对齐, 0x00结尾
    fmt = ""
    for i in range(len(tmpdata)) :
        if tmpdata[i] == 0 :
            fmt = tmpdata[:i].decode("UTF-8")
            tmpdata = tmpdata[(i+4) & 0xC:]
            break
    # print(fmt)
    # print(tmpdata.hex().upper())
    if fmt == "%.*s" :
        return tmpdata[4:].decode("UTF-8")
    return None

def log_parse(ctx, data) :
    # print(data[0], data[-1])
    if "data" in ctx :
        data = ctx["data"] + data
        ctx["data"] = b''
    tmpdata = None
    max = len(data)
    offset = 0
    msgs = list()
    while offset < max :
        if data[offset] == 0x7E :
            # print("Found 7E start")
            tmpdata = None
            for j in range(offset + 1, max) :
                if data[j] == 0x7E :
                    # print("Found 7E end")
                    tmpdata = data[offset+1:j]
                    offset = j
                    break
            if tmpdata :
                tmpdata = log_unpack(tmpdata)
                if tmpdata :
                    tmpdata = log_split(tmpdata)
                    if tmpdata :
                        msgs.append(tmpdata)
                else :
                    print("unpack failed")
            else :
                break
        offset += 1
    if offset < max :
        ctx["data"] = data[offset:]
    return msgs

if __name__ == "__main__" :
    main()