"""
Minimal pexpect-compatible shim built on pywinpty for Windows.

Exposes the small slice of the pexpect API that vivado_session.py uses:
spawn(), TIMEOUT, EOF, plus the spawn child methods expect(), sendline(),
read_nonblocking(), close(), terminate(), and the .before attribute.

Why pywinpty (ConPTY) and not plain subprocess pipes:
- Vivado in -mode tcl detects whether stdout is a tty. With plain pipes it
  switches to block-buffered output, so the "Vivado%" prompt never reaches
  us until a multi-KB buffer fills up. That makes prompt-based parsing
  impossible.
- pywinpty wraps the Windows ConPTY API and gives the child a real
  pseudo-terminal, so Vivado emits its banner and prompt immediately
  (line-buffered), exactly like pexpect on Linux.

Why not wexpect:
- legacy_wexpect drives the child via Win32 console APIs that require
  the parent process to have a real console attached to its STD handles,
  which is never the case when this MCP server is spawned by Claude Code
  (stdin/stdout are JSON-RPC pipes). It dies with WriteConsoleInput:
  invalid handle.
"""

import re
import threading
import time

import winpty


# ANSI/VT escape sequences emitted by ConPTY that we want to strip from
# captured output before regex matching. Keeps the parser in
# vivado_session.run_tcl() working unchanged.
_ANSI_ESCAPE = re.compile(
    r"\x1b\[[\?]?[0-9;]*[a-zA-Z]"  # CSI sequences
    r"|\x1b\][^\x07]*\x07"           # OSC sequences ending with BEL
    r"|\x1b[=>]"                       # keypad mode
)


class TIMEOUT(Exception):
    pass


class EOF(Exception):
    pass


class spawn:
    def __init__(self, executable, args=None, encoding="utf-8",
                 timeout=300.0, **_ignored):
        self.encoding = encoding or "utf-8"
        self.timeout = timeout
        self.before = ""
        self._buffer = ""
        self._buffer_lock = threading.Lock()
        self._eof = False

        argv = [executable] + list(args or [])
        # 200 cols × 50 rows: wide enough to keep Vivado from wrapping its
        # long log lines mid-word, which would break regex matching.
        self.proc = winpty.PtyProcess.spawn(argv, dimensions=(50, 200))

        self._reader = threading.Thread(target=self._read_loop, daemon=True)
        self._reader.start()

    def _read_loop(self):
        try:
            while True:
                try:
                    data = self.proc.read(4096)
                except EOFError:
                    self._eof = True
                    return
                if not data:
                    if not self.proc.isalive():
                        self._eof = True
                        return
                    time.sleep(0.05)
                    continue
                # PtyProcess.read returns str when initialized without
                # an encoding arg. It uses utf-8 by default.
                if isinstance(data, bytes):
                    data = data.decode(self.encoding, errors="replace")
                # Strip ANSI escape sequences emitted by ConPTY
                cleaned = _ANSI_ESCAPE.sub("", data)
                with self._buffer_lock:
                    self._buffer += cleaned
        except Exception:
            self._eof = True

    def expect(self, pattern, timeout=None):
        if timeout is None:
            timeout = self.timeout
        if isinstance(pattern, str):
            regex = re.compile(pattern)
        else:
            regex = pattern
        deadline = time.time() + timeout
        while True:
            with self._buffer_lock:
                m = regex.search(self._buffer)
                if m:
                    self.before = self._buffer[: m.start()]
                    self._buffer = self._buffer[m.end():]
                    return 0
                buf_empty = len(self._buffer) == 0
            if self._eof and buf_empty:
                raise EOF("Child process ended")
            if time.time() >= deadline:
                with self._buffer_lock:
                    self.before = self._buffer
                    self._buffer = ""
                raise TIMEOUT(f"Timeout ({timeout}s) waiting for {pattern!r}")
            time.sleep(0.05)

    def sendline(self, text):
        try:
            self.proc.write(text + "\r\n")
        except Exception:
            self._eof = True
            raise EOF("Child stdin closed")

    def read_nonblocking(self, size=1, timeout=None):
        with self._buffer_lock:
            chunk = self._buffer[:size]
            self._buffer = self._buffer[size:]
        if not chunk and self._eof:
            raise EOF("Child process ended")
        return chunk

    def close(self, force=False):
        try:
            if force:
                self.proc.terminate(force=True)
            else:
                self.proc.terminate()
        except Exception:
            pass

    def terminate(self, force=False):
        self.close(force=force)
