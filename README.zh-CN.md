# Chrome 原生 4K RTX 视频超分辨率

[English](README.md)

这个实验启动器让 Windows Chrome 里的 NVIDIA 驱动 VSR 可以处理 **3840×2160 输入、3840×2160 输出**的视频，增强后的画面直接显示在网页播放器里。

## 使用方法

需要 64 位 Windows、开启图形加速的 Chrome、已启用 RTX 视频超分辨率的 NVIDIA RTX 显卡，以及 64 位 Python 3.12。补丁限定为已实测的 NVIDIA 621.01 驱动文件，启动器会按 SHA-256 校验。

下载并解压仓库。在项目目录打开 PowerShell，依次运行下面两条命令。

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

双击 `Chrome-RTX-VSR-Native.cmd`。在新开的 Chrome 里播放视频，选 2160p，在 3840×2160 显示器上全屏观看。独立的 Chrome 用户资料保存在 `.runtime/chrome-profile`，日志在 `.runtime/native-chrome.log`。

补丁只作用于启动器打开的 Chrome GPU 进程，进程退出后失效。这个实验窗口禁用了 RTX Video HDR，以复现实测的 SDR 配置。

## 实测

在 RTX 5070 Ti、驱动 621.01 和 Chrome 157.0.8103.52 上，未打补丁的 4K 视频没有调用驱动的逐帧 VSR 回调，打补丁后每秒调用约 30 次。固定帧的画面中央区域有约 68% 的像素在至少一个 RGB 通道上变化了两个色阶或更多，开启补丁后的两次抓帧在同一区域完全一致。

公开的 4K 30 帧 H.264 DASH 流播放约 12 秒，起播时掉了两帧。本地的 4K 60 帧 H.264 和 4K 30 帧 AV1 短片也跑通了。YouTube、B 站、受保护视频和长时间播放还没实测。
