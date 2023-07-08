# 移芯工具箱

支持移芯方案的刷机, 解包, windows/linux/macos 可用

当前支持EC618系列, 例如Air780E/Air700E等模块

## 用法

先安装ectool, 在命令行或控制台执行

```bash
# 清华镜像
pip3 install -U -i https://pypi.tuna.tsinghua.edu.cn/simple ectool
# 无镜像,或者系统默认镜像
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
* [x] 测试Linux下的兼容性
* [x] 支持只刷AP或CP
* [ ] EC618使用物理UART刷机
* [ ] 测试Mac下的兼容性
* [ ] 支持刷LuatOS的script.bin
* [ ] 完整的注释
* [ ] SoC日志解析
* [ ] 支持从http加载固件文件进行下载
* [ ] binpkg打包

## Linux刷机过程展示

[![asciicast](https://asciinema.org/a/595464.svg)](https://asciinema.org/a/595464)

## 参考链接

* 流程参考 https://citeseerx.ist.psu.edu/document?repid=rep1&type=pdf&doi=483a9555e446577cefc31b5629e843cc814b83cb
* beanio做的逆向版本 https://github.com/beanjs/beanio-ec618-downloader

## 开源协议

MIT
