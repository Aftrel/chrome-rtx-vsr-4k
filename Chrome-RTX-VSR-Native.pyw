"""Run an isolated Chrome profile with the native 4K RTX VSR patch."""

import argparse
import ctypes
from ctypes import wintypes
import hashlib
import logging
import os
from pathlib import Path
import subprocess
import time


HERE = Path(__file__).resolve().parent
RUNTIME = HERE / '.runtime'
PROFILE = RUNTIME / 'chrome-profile'
CHROME = Path(os.environ['ProgramFiles']) / 'Google' / 'Chrome' / 'Application' / 'chrome.exe'
DRIVER_HASH = 'bb6c170021de9a722eb16c6368faafda0266831d6ba9e8e343bce131f35949dc'


def gpu_process(browser):
    import psutil

    for child in browser.children(recursive=False):
        try:
            if '--type=gpu-process' in child.cmdline():
                return child.pid
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return None


def patch_gpu(browser, child, source):
    import frida

    session = frida.attach(child)
    try:
        script = session.create_script(source)
        script.load()
        until = time.monotonic() + 10
        while time.monotonic() < until and browser.poll() is None:
            driver = script.exports_sync.driver_path()
            if driver:
                with Path(driver).open('rb') as handle:
                    if hashlib.file_digest(handle, 'sha256').hexdigest() != DRIVER_HASH:
                        raise RuntimeError('The loaded NVIDIA driver does not match the tested 621.01 binary.')
                if script.exports_sync.enable_native4k():
                    return session, script
            time.sleep(0.15)
        raise RuntimeError('Chrome did not load the NVIDIA driver. Check graphics acceleration and GPU selection.')
    except Exception:
        session.detach()
        raise


def monitor(browser, state):
    import frida
    import psutil

    source = (HERE / 'Chrome-RTX-VSR-Native.js').read_text(encoding='utf-8')
    process = psutil.Process(browser.pid)
    session = None
    patched_pid = None
    deadline = time.monotonic() + 15
    reported = False
    try:
        while browser.poll() is None:
            try:
                pid = gpu_process(process)
            except psutil.NoSuchProcess:
                break
            if session and (pid != patched_pid or session.is_detached):
                session.detach()
                session = patched_pid = None
                reported = False
                deadline = time.monotonic() + 15
            if not session and pid:
                try:
                    session, script = patch_gpu(browser, pid, source)
                except (frida.ProcessNotFoundError, frida.InvalidOperationError):
                    time.sleep(0.25)
                else:
                    patched_pid = pid
                    logging.info('Patch installed in Chrome GPU process %s', pid)
                    if state:
                        state.write_text(f'patched {pid}\n', encoding='utf-8')
            if not session and time.monotonic() >= deadline:
                raise RuntimeError('The Chrome GPU process did not become available.')
            if session and not reported:
                try:
                    seen = script.exports_sync.native_frames()
                except frida.InvalidOperationError:
                    continue
                if seen:
                    logging.info('Native 4K frames detected in Chrome GPU process %s', patched_pid)
                    if state:
                        state.write_text(f'native 4K {patched_pid}\n', encoding='utf-8')
                    reported = True
            time.sleep(0.25)
    finally:
        if session:
            session.detach()


def launch(args):
    if not CHROME.is_file():
        raise RuntimeError(f'Google Chrome was not found at {CHROME}.')
    flags = [f'--user-data-dir={args.profile}', '--no-first-run', '--no-default-browser-check',
             '--new-window', '--disable_vp_auto_hdr', '--do-not-de-elevate']
    if args.test_state:
        flags += ['--remote-debugging-port=0', '--start-fullscreen', '--autoplay-policy=no-user-gesture-required',
                  '--disable-backgrounding-occluded-windows', '--disable-renderer-backgrounding',
                  '--disable-features=CalculateNativeWinOcclusion']
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.CreateMutexW.argtypes = [wintypes.LPVOID, wintypes.BOOL, wintypes.LPCWSTR]
    kernel.CreateMutexW.restype = wintypes.HANDLE
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    profile_id = hashlib.sha256(str(args.profile).lower().encode()).hexdigest()[:16]
    mutex = kernel.CreateMutexW(None, False, f'Local\\ChromeNativeVsr_{profile_id}')
    already_open = ctypes.get_last_error() == 183
    if not mutex:
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        chrome = subprocess.Popen([str(CHROME), *flags, args.url], stdout=subprocess.DEVNULL,
                                  stderr=subprocess.DEVNULL)
        if not already_open:
            monitor(chrome, args.test_state)
    finally:
        kernel.CloseHandle(mutex)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('url', nargs='?', default='chrome://newtab/')
    parser.add_argument('--profile', type=lambda path: Path(path).resolve(), default=PROFILE)
    parser.add_argument('--test-state', type=Path)
    args = parser.parse_args()
    if args.test_state and args.profile == PROFILE:
        parser.error('Diagnostic mode requires a separate temporary Chrome profile.')
    try:
        RUNTIME.mkdir(exist_ok=True)
        logging.basicConfig(filename=RUNTIME / 'native-chrome.log', encoding='utf-8', level=logging.INFO,
                            format='%(asctime)s %(message)s')
        launch(args)
    except Exception as exc:
        logging.exception('Native VSR launcher failed')
        if args.test_state:
            raise
        ctypes.windll.user32.MessageBoxW(None, str(exc), 'Chrome Native 4K RTX VSR', 0x10)


if __name__ == '__main__':
    main()
