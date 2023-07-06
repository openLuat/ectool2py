#!/usr/bin/python3
# -*- coding: UTF-8 -*-

import os, struct, sys, json, shutil, logging, hashlib

logging.basicConfig(level=logging.DEBUG)

def binpkg_unpack(binpkg_path, outpath_dir) :
    logging.info("binpkg " + binpkg_path)
    logging.info("output " + outpath_dir)
    with open(binpkg_path, "rb") as f :
        fdata = f.read()
    if not os.path.exists(outpath_dir) :
        os.makedirs(outpath_dir)
    
    jdata = {}
    fsize = len(fdata)

    # 首先, 解析头部数据
    foffset = 0
    fhead = fdata[:52] 
    foffset += 52
    # 然后逐个文件解析出来
    while foffset < fsize :
        name,addr,flash_size,offset,img_size,hash,img_type,vt,vtsize,rsvd,pData = struct.unpack("64sIIII256s16sHHII", fdata[foffset:foffset+364])
        name = name.rstrip(b'\0').decode('utf8')
        hash = hash.rstrip(b'\0').decode('utf8').lower()
        img_type = img_type.rstrip(b'\0').decode('utf8')
        print(name, addr, flash_size, offset, img_size, hash, img_type)
        foffset += 364
        with open(os.path.join(outpath_dir, name + ".bin"), "wb") as f :
            tmpdata = fdata[foffset:foffset+img_size]
            sha256 = hashlib.sha256(tmpdata)
            f.write(tmpdata)
            print(sha256.hexdigest(), hash, hash == sha256.hexdigest())
        foffset += img_size
        jdata[name] = {
            "addr" : addr,
            "flash_size" : flash_size,
            "offset" : offset,
            "image_size" : img_size,
            "hash" : hash,
            "image_type" : img_type
        }
    with open(os.path.join(outpath_dir, "image_info.json"), "w") as f :
        json.dump(jdata, f, indent=2)

if __name__ == "__main__":
    if len(sys.argv) == 3 :
        binpkg_unpack(sys.argv[1], sys.argv[2])
