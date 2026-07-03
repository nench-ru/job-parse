import queue
from datetime import datetime

import customtkinter as ctk


class LogConsole(ctk.CTkTextbox):
    def __init__(self, master: any, **kwargs):
        super().__init__(master, **kwargs)
        self.log_queue: queue.Queue[str] = queue.Queue()
        self._running = True
        self._is_redirecting = False
        self.after(100, self._poll_queue)

    def write(self, text: str):
        self.log_queue.put(text)

    def flush(self):
        pass

    def _poll_queue(self):
        try:
            while True:
                msg = self.log_queue.get_nowait()
                self._append_msg(msg)
        except queue.Empty:
            pass
        if self._running:
            self.after(100, self._poll_queue)

    def _append_msg(self, msg: str):
        if not msg.strip():
            return
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.insert("end", f"[{timestamp}] {msg}\n")
        self.see("end")

    def clear(self):
        self.delete("0.0", "end")

    def stop(self):
        self._running = False

    def __del__(self):
        self._running = False


class LogRedirector:
    def __init__(self, console: LogConsole):
        self.console = console

    def emit(self, record):
        try:
            msg = record.getMessage()
            level = record["level"].name
            if level == "ERROR":
                prefix = "ERROR"
            elif level == "WARNING":
                prefix = "WARN"
            else:
                prefix = "INFO"
            self.console.write(f"[{prefix}] {msg}")
        except Exception:
            pass
