"""Install and control the background patch for an existing Chrome session."""

import argparse
import ctypes
from ctypes import wintypes
import hashlib
import logging
from pathlib import Path
import subprocess
import time
import winreg

import psutil

from vsr_driver import DriverAttachment, ROOT, RUNTIME


PAUSED = RUNTIME / 'current-chrome.disabled'
PYTHONW = ROOT / '.venv' / 'Scripts' / 'pythonw.exe'
RUN_KEY = r'Software\Microsoft\Windows\CurrentVersion\Run'
RUN_NAME = 'Chrome RTX VSR 4K'
BACKGROUND_ARGS = [str(PYTHONW), str(Path(__file__).resolve()), 'background']
BACKGROUND_COMMAND = subprocess.list2cmdline(BACKGROUND_ARGS)
CHROME_LOCATION = ('google', 'chrome', 'application', 'chrome.exe')


def startup_command():
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
            return winreg.QueryValueEx(key, RUN_NAME)[0]
    except FileNotFoundError:
        return None


def write_startup(command):
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
        if command is None:
            try:
                winreg.DeleteValue(key, RUN_NAME)
            except FileNotFoundError:
                pass
        else:
            winreg.SetValueEx(key, RUN_NAME, 0, winreg.REG_SZ, command)


def default_chrome_gpu(kernel):
    browser_ids = set()
    gpu_processes = []
    own_session, process_session = wintypes.DWORD(), wintypes.DWORD()
    if not kernel.ProcessIdToSessionId(psutil.Process().pid, ctypes.byref(own_session)):
        raise ctypes.WinError(ctypes.get_last_error())

    for process in psutil.process_iter(['name']):
        if (process.info['name'] or '').lower() != 'chrome.exe':
            continue
        if not kernel.ProcessIdToSessionId(process.pid, ctypes.byref(process_session)):
            continue
        if process_session.value != own_session.value:
            continue
        try:
            with process.oneshot():
                command = process.cmdline()[1:]
                if '--type=gpu-process' in command:
                    gpu_processes.append((process.ppid(), process.pid))
                elif not any(arg.startswith(('--type=', '--user-data-dir')) for arg in command):
                    executable = tuple(part.lower() for part in Path(process.exe()).parts[-4:])
                    if executable == CHROME_LOCATION:
                        browser_ids.add(process.pid)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    candidates = [pid for parent, pid in gpu_processes if parent in browser_ids]
    if len(candidates) > 1:
        raise RuntimeError('Multiple default Chrome GPU processes were found.')
    return candidates[0] if candidates else None


def disconnect(attachment):
    try:
        attachment.close()
        logging.info('Detached from Chrome GPU process %s', attachment.pid)
    except Exception:
        logging.exception('Could not cleanly detach from Chrome GPU process %s', attachment.pid)


def monitor(kernel):
    attachment = None
    last_error = None
    reported = False
    try:
        while startup_command() == BACKGROUND_COMMAND:
            if attachment and (attachment.session.is_detached or PAUSED.exists()):
                disconnect(attachment)
                attachment = None
            if not PAUSED.exists():
                try:
                    if attachment is None:
                        pid = default_chrome_gpu(kernel)
                        if pid is not None:
                            attachment = DriverAttachment(pid)
                            reported = False
                            logging.info('Attached to the existing Chrome GPU process %s', pid)
                    if attachment and not reported and attachment.api.eligible_frames():
                        logging.info('Detected eligible 4K playback in Chrome GPU process %s', attachment.pid)
                        reported = True
                    last_error = None
                except Exception as error:
                    message = str(error)
                    if last_error != message:
                        logging.exception('Could not attach to the existing Chrome GPU process')
                        last_error = message
            time.sleep(2)
    finally:
        if attachment:
            disconnect(attachment)
        logging.info('Stopped the background launcher')


def background():
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.CreateMutexW.argtypes = (wintypes.LPVOID, wintypes.BOOL, wintypes.LPCWSTR)
    kernel.CreateMutexW.restype = wintypes.HANDLE
    kernel.CloseHandle.argtypes = (wintypes.HANDLE,)
    kernel.ProcessIdToSessionId.argtypes = (wintypes.DWORD, ctypes.POINTER(wintypes.DWORD))
    kernel.ProcessIdToSessionId.restype = wintypes.BOOL
    install_id = hashlib.sha256(str(ROOT).casefold().encode()).hexdigest()[:16]
    mutex = kernel.CreateMutexW(None, False, f'Local\\ChromeRTXVSR4KBackground-{install_id}')
    status = ctypes.get_last_error()
    if not mutex:
        raise ctypes.WinError(status)
    try:
        if status != 183 and startup_command() == BACKGROUND_COMMAND:
            logging.info('Started the background launcher')
            monitor(kernel)
    finally:
        kernel.CloseHandle(mutex)


def enable():
    if not PYTHONW.is_file():
        raise RuntimeError('Create the .venv environment before enabling VSR. See README.md.')
    if len(BACKGROUND_COMMAND) > 260:
        raise RuntimeError('The Windows startup path is too long. Move the project to a shorter directory and recreate .venv.')

    previous = startup_command()
    was_paused = PAUSED.exists()
    write_startup(BACKGROUND_COMMAND)
    try:
        PAUSED.unlink(missing_ok=True)
        subprocess.Popen(BACKGROUND_ARGS, cwd=ROOT, creationflags=subprocess.DETACHED_PROCESS)
    except Exception:
        if was_paused:
            PAUSED.touch()
        write_startup(previous)
        raise
    print('4K RTX VSR is enabled for the current Windows account.')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=('enable', 'disable', 'uninstall', 'background'))
    args = parser.parse_args()
    RUNTIME.mkdir(exist_ok=True)
    logging.basicConfig(filename=RUNTIME / 'current-chrome.log', encoding='utf-8', level=logging.INFO,
                        format='%(asctime)s %(message)s')
    if args.mode == 'background':
        background()
    elif args.mode == 'enable':
        enable()
    elif args.mode == 'disable' and startup_command() == BACKGROUND_COMMAND:
        PAUSED.touch()
        print('4K RTX VSR is disabled until you enable it again.')
    elif args.mode == 'uninstall' and startup_command() == BACKGROUND_COMMAND:
        write_startup(None)
        PAUSED.unlink(missing_ok=True)
        print('Removed 4K RTX VSR from Windows startup.')
    else:
        print('This copy of the 4K RTX VSR launcher is not registered for Windows startup.')


if __name__ == '__main__':
    main()
