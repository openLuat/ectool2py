# 移芯工具箱

支持移芯方案的刷机, 解包, windows/linux/macos 可用

当前支持EC618系列, 例如Air780E/Air700E/Air600E/Air780EG等模块

本库可支持被引用, eccli本身就是调用实例.

## 用法

先安装ectool, 在命令行或控制台执行

```bash
# 清华镜像
pip3 install -U -i https://pypi.tuna.tsinghua.edu.cn/simple ectool
# 若安装失败, 可尝试以下命令, 从pypi直接进行安装
pip3 install -U ectool
```

刷机(当前仅USB刷机), 支持binpkg和soc文件

```bash
ectool burn -f example.binpkg
# 启动后, 按住BOOT键, 复位模块, 或模块开机
```

更多参数执行 `ectool -h` 获取说明

## TODO List

* [x] EC618使用USB刷机
* [x] binpkg解包
* [x] 兼容Linux下刷机
* [x] 兼容Mac下刷机
* [x] 支持只刷AP或CP
* [x] 支持跳过AgentBoot
* [x] 支持擦除指定区域的数据
* [x] SoC日志解析(简易)
* [x] 支持从http加载固件文件进行下载
* [ ] EC618使用物理UART刷机
* [ ] 支持刷LuatOS的script.bin
* [ ] 完整的注释
* [ ] SoC日志解析(完整)
* [ ] ~~binpkg打包~~

## Linux刷机过程展示

[![asciicast](https://asciinema.org/a/595464.svg)](https://asciinema.org/a/595464)

## 参考链接

* 流程参考 [PSU的某种设备的文档](https://citeseerx.ist.psu.edu/document?repid=rep1&type=pdf&doi=483a9555e446577cefc31b5629e843cc814b83cb)
* beanio做的逆向版本 [beanio-ec618-downloader](https://github.com/beanjs/beanio-ec618-downloader)

## 开源协议

MIT
