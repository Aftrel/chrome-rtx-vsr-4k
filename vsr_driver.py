"""Load the verified driver hook and remove it on disconnect."""

import hashlib
from pathlib import Path
import time

import frida


ROOT = Path(__file__).resolve().parent
RUNTIME = ROOT / '.runtime'
DRIVER_HASH = 'bb6c170021de9a722eb16c6368faafda0266831d6ba9e8e343bce131f35949dc'


class DriverAttachment:
    def __init__(self, pid):
        self.pid = pid
        self.session = frida.attach(pid)
        try:
            source = (ROOT / 'Chrome-RTX-VSR-Native.js').read_text(encoding='utf-8')
            self.script = self.session.create_script(source)
            self.script.load()
            self.api = self.script.exports_sync
            deadline = time.monotonic() + 8
            driver = self.api.driver_path()
            while not driver and time.monotonic() < deadline:
                time.sleep(0.15)
                driver = self.api.driver_path()
            if not driver:
                raise RuntimeError('Chrome did not load the NVIDIA driver. Check graphics acceleration and GPU selection.')
            with Path(driver).open('rb') as handle:
                if hashlib.file_digest(handle, 'sha256').hexdigest() != DRIVER_HASH:
                    raise RuntimeError('The loaded NVIDIA driver does not match the tested 621.01 binary.')
            self.api.start()
        except Exception:
            self.session.detach()
            raise

    def close(self):
        if self.session.is_detached:
            return
        try:
            self.api.stop()
        finally:
            self.session.detach()
