import concurrent.futures
import os
import subprocess
import sys

import numpy as np
import soundcard as sc
from PySide6.QtCore import QRect
from PySide6.QtWidgets import QApplication, QMainWindow, QPushButton, QLabel, QLineEdit


class ScreenStreamer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Screen Streamer")
        self.setGeometry(200, 200, 400, 200)
        self.label = QLabel("対象IP", self)
        self.label.setGeometry(QRect(20, 40, 80, 30))
        self.ip_input = QLineEdit(self)
        self.ip_input.setGeometry(QRect(100, 40, 260, 30))
        self.start_btn = QPushButton("開始", self)
        self.start_btn.setGeometry(QRect(20, 100, 340, 60))
        self.start_btn.clicked.connect(self.toggle_stream)

        self.ffmpeg = None
        self.running = False

    def toggle_stream(self):
        if not self.running:
            self.running = True
            self.start_btn.setText("ストップ")
            self.start_stream()
        else:
            self.running = False
            self.start_btn.setText("開始")
            subprocess.run('taskkill /f /im ffmpeg.exe', shell=True)

    def start_stream(self):
        target_ip = self.ip_input.text().strip()
        if target_ip.startswith("udp://"):
            target_ip = target_ip[6:]
        if ":" in target_ip:
            target_ip = target_ip.split(":")[0]
        if not target_ip:
            target_ip = "localhost"

        self.ffmpeg = subprocess.Popen([
            "ffmpeg", "-f", "s16le", "-ar", "44100", "-ac", "2", "-i", "pipe:0",
            "-fflags", "nobuffer", "-flags", "low_delay",
            "-flush_packets", "1",
            "-f", "gdigrab", "-framerate", "60", "-video_size", "1920x1080", "-i", "desktop",
            "-vcodec", "libx264", "-preset", "ultrafast", "-tune", "zerolatency",
            "-acodec", "aac", "-ar", "44100", "-b:a", "128k",
            "-f", "avi", f"udp://{target_ip}:1889"
        ], stdin=subprocess.PIPE, shell=True)

        def audio_thread():
            mic = sc.get_microphone(id=sc.default_speaker().name, include_loopback=True)
            with mic.recorder(samplerate=44100, channels=2) as rec:
                while self.running:
                    data = rec.record(numframes=44100)
                    pcm16 = np.int16(data * 32767).tobytes()
                    try:
                        self.ffmpeg.stdin.write(pcm16)
                        self.ffmpeg.stdin.flush()
                    except Exception as e:
                        print(f"[ERROR] ffmpeg write: {e}")
                        break

        concurrent.futures.ThreadPoolExecutor(os.cpu_count() * 999999).submit(audio_thread)

    def closeEvent(self, event):
        self.running = False
        subprocess.run('taskkill /f /im ffmpeg.exe', shell=True)
        event.accept()

def main():
    app = QApplication(sys.argv)
    win = ScreenStreamer()
    win.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()