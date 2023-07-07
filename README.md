 # 移芯工具箱

已支持:
1. EC618的刷机
2. binpkg格式解包

将要支持
1. binpkg格式的打包
2. EC718, EC616的刷机

## 用法

先安装ectool, 在命令行或控制台执行

```bash
# 清华镜像
pip3 install -U -i https://pypi.tuna.tsinghua.edu.cn/simple ectool
# 无镜像,或者系统默认镜像
pip3 install -U ectool
```

刷机(当前仅USB刷机), 支持binpkg和soc文件, 但暂不支持LuatOS的脚本刷机

```bash
ectool burn -f example.binpkg
# 启动后, 按住BOOT键, 复位模块, 或模块开机
```

## TODO List

* [ ] 完整的注释
* [ ] 测试Linux下的兼容性
* [ ] 测试Mac下的兼容性
* [ ] 支持刷LuatOS的script.bin
* [ ] 支持只刷AP

## 参考链接

* 流程参考 https://citeseerx.ist.psu.edu/document?repid=rep1&type=pdf&doi=483a9555e446577cefc31b5629e843cc814b83cb
* beanio做的逆向版本 https://github.com/beanjs/beanio-ec618-downloader

## 开源协议

MIT
