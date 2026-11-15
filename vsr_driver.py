"""Load the verified driver hook and remove it on disconnect."""

from pathlib import Path
import time

import frida

from vsr_layout import FUNCTION_SIZE, HOOK_OFFSETS, find_layout, matches_function


ROOT = Path(__file__).resolve().parent
RUNTIME = ROOT / '.runtime'


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
            addresses = find_layout(Path(driver))
            function_start = addresses[0] - HOOK_OFFSETS[0]
            if not matches_function(self.api.driver_code(function_start, FUNCTION_SIZE)):
                raise RuntimeError('The VSR function loaded by Chrome differs from the verified layout.')
            self.api.start(*addresses)
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
