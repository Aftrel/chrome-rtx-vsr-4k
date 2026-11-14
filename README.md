# Chrome Native 4K RTX Video Super Resolution

[中文说明](README.zh-CN.md)

This experimental launcher enables NVIDIA's driver-side RTX Video Super Resolution (VSR) for 3840×2160 video displayed at 3840×2160 in Windows Chrome. The processed video appears in the original player.

## Requirements

- Windows x64, Google Chrome with graphics acceleration, and an NVIDIA RTX GPU with RTX Video Super Resolution enabled in NVIDIA App or Control Panel.
- NVIDIA 621.01 with the exact `nvwgf2umx.dll` SHA-256 recorded in the launcher. Other driver binaries are rejected before applying the patch.
- Python 3.12 x64 with pip. Development was tested on Windows with Chrome 157.0.8103.52 and an RTX 5070 Ti.

## Run

Download and extract the repository. Run both commands in PowerShell from the project directory.

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Double-click `Chrome-RTX-VSR-Native.cmd`. Open a video in the new Chrome window, select 2160p, and use full screen on a 3840×2160 display. This launcher uses a separate Chrome profile in `.runtime/chrome-profile`. Its log is `.runtime/native-chrome.log`.

The patch applies only to the GPU process of the Chrome instance launched here and expires when that process exits. The launcher disables Chrome's RTX Video HDR integration in that instance to reproduce the tested SDR configuration. Full-screen SDR playback was tested. YouTube, Bilibili, protected streams and long sessions remain unverified.

## Results

On the tested system, the driver accepted the VSR stream request even for unmodified 4K playback. The trace showed zero calls to the VSR per-frame processing callback on the unmodified 4K path and 30 calls per one-second sample with the patch. In the 3840×1400 central crop of a repeated-frame test, 68.47% of pixels changed by at least two code values in one or more RGB channels. Repeated captures with the patch enabled matched in that region.

The launcher also played about 12 seconds of a [public 4K H.264 DASH stream](https://dash.akamaized.net/akamai/bbb_30fps/bbb_30fps_3840x2160_12000k/) at 30 fps with two dropped frames during startup. Local short clips exercised 4K60 H.264 and 4K30 AV1.

## How it works

`Chrome-RTX-VSR-Native.js` raises two input-area comparisons in NVIDIA's user-mode D3D driver from 3,686,400 pixels to 8,294,400 pixels. It then overrides the driver's scale eligibility flag specifically when the input and destination rectangles both measure 3840×2160. The Python launcher checks the loaded binary's SHA-256 and the patch checks the expected instructions. The system driver file stays on disk in its original form.

NVIDIA documents the default browser input range in its [RTX Video FAQ](https://nvidia.custhelp.com/app/answers/detail/a_id/5448/~/rtx-video-super-resolution-faq). For related driver-side VSR reverse engineering, see Philip Langdale's [FFmpeg `vsr_drv_cuda` submission](https://github.com/FFmpeg/FFmpeg/commit/47d0aa27ab1029b24e64596773211f1c3e143eb2).
