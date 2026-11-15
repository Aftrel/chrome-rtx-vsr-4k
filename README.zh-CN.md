# Chrome 原生 4K RTX 视频超分辨率

[English](README.md)

这个实验工具让 Windows Chrome 网页播放器在全屏播放 UHD 和 4096 像素宽的 4K 视频时，调用 NVIDIA 驱动的 RTX VSR。后台程序直接接入你平时使用的 Chrome，可以继续用原来的标签页、登录状态和设置。

## 安装和使用

需要 64 位 Windows、开启图形加速的 Chrome、支持并已启用 RTX 视频超分辨率的 NVIDIA RTX 显卡，以及 64 位 Python 3.12。已确认 NVIDIA 621.01 和 621.24 驱动的 VSR 函数结构兼容。测试设备为 RTX 5070 Ti，Chrome 版本为 157.0.8103.52。

把源码解压到准备长期使用的目录。在该目录打开 PowerShell，运行以下命令。

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\Chrome-RTX-VSR-Current.cmd
```

最后一条也可以双击运行。首次运行即开启增强，以后登录当前 Windows 账号会自动在后台启动。Chrome 可以保持打开，增强程序没有常驻窗口。播放时选 4K 清晰度，再用网页播放器的全屏按钮。

| 操作 | 文件 |
| --- | --- |
| 关闭增强，重登后也保持关闭 | `Chrome-RTX-VSR-Off.cmd` |
| 重新开启 | `Chrome-RTX-VSR-Current.cmd` |
| 移除开机启动项并停止后台进程 | `Uninstall-Chrome-RTX-VSR.cmd` |

删除或替换项目目录前，请先运行卸载命令。后台日志在 `.runtime/current-chrome.log`。原来的 `Chrome-RTX-VSR-Native.cmd` 也可以启动独立的 Chrome 配置，适合对照测试。该模式会为自己打开的 Chrome 实例禁用 RTX Video HDR。

## 实测

| 片源分辨率 | 实测内容 |
| --- | --- |
| 3840×2160 | YouTube 30 帧，B 站点播和英雄联盟 4K 直播 60 帧 |
| 4096×2160 | H.264 30 帧，10-bit HEVC 60 帧 |
| 4096×1716 | H.264 30 帧 |
| 4096×1800 | H.264 30 帧 |
| 3840×1600 | H.264 30 帧 |

上表为 621.01 驱动的播放测试。较宽的尺寸使用测试短片在 3840×2160 屏幕上验证。驱动的逐帧记录和抓帧对比都确认了增强生效。在 621.24 上，驱动记录也确认了表中五种分辨率的测试短片触发 VSR，其中包括 4096×2160 的 10-bit HEVC。补丁按全屏时视频实际显示的区域判断，适配宽银幕黑边和 Chrome 将输出尺寸取整造成的几像素偏差。在 621.01 上挂着诊断探针做开关对照时，测试用的 Chrome GPU 进程被 NVIDIA 驱动重置了两次，具体原因未查明。受保护视频和长时间播放还没实测。

启动时会在 `nvwgf2umx.dll` 中自动定位 VSR 函数，并核对 Chrome 已加载的代码。如果驱动更新后函数仍保留已验证的结构，即使位置变了也能自动适配。无法确认结构时会跳过补丁。

补丁在 Chrome GPU 进程内调整 VSR 的输入像素数及缩放判断。输入宽度范围为 3840–4096、高度范围为 1440–2160，画面需要接近 4K 屏幕的全宽并保持片源比例。关闭增强后会从进程内卸载补丁，磁盘上的驱动文件不会被写入。
