# Chrome Native 4K RTX Video Super Resolution

[中文说明](README.zh-CN.md)

Enable NVIDIA's driver-side RTX Video Super Resolution (VSR) for full-screen UHD and DCI-width 4K video in Windows Chrome. The background launcher attaches to the Chrome instance you already use, with its open tabs, sign-ins and settings.

## Requirements

- Windows x64, Google Chrome with graphics acceleration, and an NVIDIA RTX GPU with RTX Video Super Resolution enabled in the NVIDIA app or Control Panel.
- An NVIDIA driver with a supported VSR function. Driver versions 621.01 and 621.24 have supported layouts. Playback testing used an RTX 5070 Ti and Chrome 157.0.8103.52.
- Python 3.12 x64 with pip.

## Set up background mode

Download and extract the repository to a folder you plan to keep. Run these commands in PowerShell from that folder.

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\Chrome-RTX-VSR-Current.cmd
```

The last command also works by double-clicking it. It enables VSR immediately, registers it for the current Windows account at sign-in, and runs the background helper without a window. Chrome can stay open during setup. Select the 4K stream and use the player's full-screen button.

| Command | Effect |
| --- | --- |
| `Chrome-RTX-VSR-Off.cmd` | Detach the patch within a few seconds and keep it off across sign-ins. |
| `Chrome-RTX-VSR-Current.cmd` | Enable it again. |
| `Uninstall-Chrome-RTX-VSR.cmd` | Remove the Windows startup entry and stop the background helper. Run it before deleting or replacing the project folder. |

The background log is in `.runtime/current-chrome.log`. The previous `Chrome-RTX-VSR-Native.cmd` entry is still available for an isolated Chrome profile. That mode uses `.runtime/chrome-profile` and disables Chrome's RTX Video HDR integration in its own instance.

## Tested playback

| Source resolution | Tested configuration |
| --- | --- |
| 3840×2160 | YouTube at 30 fps, Bilibili video and a 4K League of Legends livestream at 60 fps |
| 4096×2160 | H.264 at 30 fps and 10-bit HEVC at 60 fps |
| 4096×1716 | H.264 at 30 fps |
| 4096×1800 | H.264 at 30 fps |
| 3840×1600 | H.264 at 30 fps |

The table summarizes playback testing on driver 621.01. The wider formats were verified with short test clips on a 3840×2160 display. Driver traces and frame captures confirmed that VSR processed the video inside Chrome. On 621.24, driver traces confirmed VSR processing in short clips at all five listed resolutions, including 10-bit HEVC at 4096×2160. The patch follows the displayed video rectangle, including letterboxed video and the few pixels Chrome can add when rounding to the swap-chain size. The NVIDIA driver reset the test Chrome GPU process twice during instrumented on/off comparisons on 621.01. The cause is still unknown. Protected playback and long sessions remain unverified.

## How it works

The launcher locates the VSR function in `nvwgf2umx.dll` and checks the function loaded in Chrome before applying the hook. It can handle a driver update that moves the function while preserving its verified code layout. It skips the patch when the layout cannot be verified.

The in-memory hook adjusts RTX VSR's input-area checks and scaling eligibility for near-full-width video on a 4K display. It applies to source widths from 3840 through 4096 and heights from 1440 through 2160 when the destination is near the screen width and preserves the aspect ratio. Disabling it removes the hooks from Chrome's GPU process. The NVIDIA driver file on disk stays intact.

NVIDIA documents the default browser input range in its [RTX Video FAQ](https://nvidia.custhelp.com/app/answers/detail/a_id/5448/~/rtx-video-super-resolution-faq). For related driver-side reverse engineering, see Philip Langdale's [FFmpeg `vsr_drv_cuda` submission](https://github.com/FFmpeg/FFmpeg/commit/47d0aa27ab1029b24e64596773211f1c3e143eb2).
