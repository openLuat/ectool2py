#!/usr/bin/python3
# -*- coding: UTF-8 -*-

import os, struct, sys, json, shutil, logging, hashlib

# logging.basicConfig(level=logging.DEBUG)

def binpkg_unpack(path_or_data, outpath_dir=None, ram=False, debug=False) :
    # logging.info("binpkg " + binpkg_path)
    # logging.info("output " + outpath_dir)
    if outpath_dir and not os.path.exists(outpath_dir) :
        os.makedirs(outpath_dir)
    if ram :
        outpath_dir = None
    jdata = {}
    if path_or_data.__class__.__name__ == "bytes" :
        fdata = path_or_data
    else:
        if str(path_or_data).endswith(".binpkg") :
            with open(path_or_data, "rb") as f :
                fdata = f.read()
        elif str(path_or_data).endswith(".soc") :
            import py7zr
            info_json = None
            with py7zr.SevenZipFile(path_or_data, 'r') as zip:
                for fname, bio in zip.readall().items():
                    if str(fname).endswith(".binpkg") :
                        fdata = bio.read()
                    elif str(fname).endswith("script.bin") :
                        tmpdata = bio.read()
                        jdata["script"] = {
                            "addr" : 0,
                            "flash_size" : 0,
                            "offset" : 0,
                            "image_size" : len(tmpdata),
                            "hash" : hashlib.sha256(tmpdata).hexdigest(),
                            "image_type" : "AP"
                        }
                        if outpath_dir :
                            with open(os.path.join(outpath_dir, fname), "wb") as f :
                                f.write(tmpdata)
                        if ram :
                            jdata["script"]["data"] = tmpdata
                    elif str(fname) == "info.json" :
                        info_json = json.load(bio)
            if info_json and "script" in jdata :
                jdata["script"]["burn_addr"] = int(info_json["download"]["script_addr"], 16)
        else:
            raise Exception("unkown file type")
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
        # if debug:
        #     print(name, addr, flash_size, offset, img_size, hash, img_type)
        foffset += 364
        tmpdata = fdata[foffset:foffset+img_size]
        # sha256 = hashlib.sha256(tmpdata).hexdigest()
        # if debug:
        #     print(sha256, hash, hash == sha256)
        if outpath_dir :
            with open(os.path.join(outpath_dir, name + ".bin"), "wb") as f :
                f.write(tmpdata)
        foffset += img_size
        jdata[name] = {
            "addr" : addr,
            "flash_size" : flash_size,
            "offset" : offset,
            "image_size" : img_size,
            "hash" : hash,
            "image_type" : img_type,
            "burn_addr" : 0
        }
        if img_type == "AP" :
            jdata[name]["burn_addr"] = 0x24000
        if ram :
            jdata[name]["data"] = tmpdata
    if outpath_dir :
        with open(os.path.join(outpath_dir, "image_info.json"), "w") as f :
            json.dump(jdata, f, indent=2)
    if outpath_dir and debug :
        print(json.dumps(jdata, indent=2))
    return jdata

if __name__ == "__main__":
    if len(sys.argv) == 3 :
        binpkg_unpack(sys.argv[1], sys.argv[2], False, True)
    else :
        print(sys.argv[0], "<binpath>", "<outdir>")
