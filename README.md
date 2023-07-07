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
# 无镜像,或者系统默认镜像
pip install -U ectool
# 清华镜像
pip install -i https://pypi.tuna.tsinghua.edu.cn/simple ectool
```

刷机(当前仅USB刷机), 支持binpkg和soc文件, 但暂不支持LuatOS的脚本刷机

```bash
ectool burn -f example.binpkg
# 启动后, 按住BOOT键, 复位模块, 或模块开机
```