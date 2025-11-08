import multiprocessing
import os
import subprocess
import sys
import threading
import time
import numpy as np
import psutil
import soundcard as sc
from PySide6.QtCore import Qt, QRect, QMetaObject, QSize
from PySide6.QtGui import QIcon, QPixmap, QImage
from PySide6.QtWidgets import QApplication, QLabel, QLineEdit, QPushButton, QMainWindow

running = [False]

def stream_audio():
    try:
        _ffmpeg = subprocess.Popen([
            "ffmpeg", "-hide_banner", "-loglevel", "error",
            "-f", "s16le", "-ar", "44100", "-ac", "2", "-i", "pipe:0",
            "-f", "gdigrab", "-video_size", "1920x1080", "-i", "desktop", "-framerate", "60", "-preset", "ultrafast",
            "-tune", "zerolatency",
            "-vf", "scale=1920:1080:flags=lanczos", "-vf", "hqdn3d=1.5:1.5:6:6", "-af", "afftdn=nf=-25", "-f", "mpegts",
            "tcp://127.0.0.1:5000"
        ], stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, shell=True)
        mic = sc.get_microphone(id=sc.default_speaker().name, include_loopback=True)
        samplerate = 44100
        chunk = 4410  # 約0.1秒分

        with mic.recorder(samplerate=samplerate, channels=2) as rec:
            while running[0] and _ffmpeg and _ffmpeg.poll() is None:
                data = rec.record(numframes=chunk)
                pcm = np.int16(data * 32767).tobytes()
                try:
                    _ffmpeg.stdin.write(pcm)
                except (BrokenPipeError, OSError):
                    break
    except Exception as e:
        print(f"[AudioThread Error] {e}")


def _ffmpeg_relay(ip):
    subprocess.run([
                "ffmpeg", "-fflags", "nobuffer", "-i", "tcp://127.0.0.1:5000?listen=1", "-framerate", "60", "-c", "copy",
                "-flags", "low_delay", "-preset", "ultrafast", "-tune", "zerolatency", "-b:a", "128k",
                "-f", "mpegts", f"udp://{ip}:1889?pkt_size=1316"
            ],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, shell=True)

class MainWindow(QMainWindow):
    def __init__(self, parent=None):
        super(MainWindow, self).__init__(parent)
        self.setAcceptDrops(True)
        icon_path = os.path.join(os.getcwd(), 'icons', 'icon.png')
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(QPixmap(QSize(96, 96)).fromImage(QImage(icon_path))))

    def closeEvent(self, event):
        subprocess.run('taskkill /f /im ffmpeg.exe', shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

class Ui_ScreenSS(object):
    def setupUi(self, ScreenSS):
        if not ScreenSS.objectName():
            ScreenSS.setObjectName(u"ScreenSS")
        ScreenSS.resize(400, 260)

        self.title = QLabel(ScreenSS)
        self.title.setGeometry(QRect(60, 40, 271, 41))
        self.title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.target_ip = QLineEdit(ScreenSS)
        self.target_ip.setGeometry(QRect(100, 100, 281, 41))

        self.target_label = QLabel(ScreenSS)
        self.target_label.setGeometry(QRect(10, 106, 91, 31))
        self.target_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.start_btn = QPushButton(ScreenSS)
        self.start_btn.setGeometry(QRect(20, 180, 351, 61))
        self.start_btn.clicked.connect(self.start_or_stop)

        running[0] = False
        self.ffmpeg = None
        self.ffmpeg_relay = None
        self.relay_timer_thread = None

        self.retranslateUi(ScreenSS)
        QMetaObject.connectSlotsByName(ScreenSS)

    def retranslateUi(self, ScreenSS):
        ScreenSS.setWindowTitle("Screen Streamer (Relay + Auto Restart)")
        self.title.setText("Screen Streamer")
        self.target_label.setText("対象IP")
        self.start_btn.setText("▶ 開始")

    def check_text_format(self, text):
        if not text:
            return ""
        if text.startswith("udp://"):
            text = text[6:]
        if ":" in text:
            text = text.split(":")[0]
        return text.strip()

    def start_or_stop(self):
        if not running[0]:
            self.start_stream()
        else:
            self.stop_stream()

    # ==== ストリーム開始 ====
    def start_stream(self):
        running[0] = True
        self.start_btn.setText("⛔ 停止")

        # --- 送信側 ffmpeg ---
        self.ffmpeg = threading.Thread(target=stream_audio, daemon=True)
        self.ffmpeg.start()
        threading.Thread(target=self.start_relay, daemon=True).start()
        self.relay_timer_thread = threading.Thread(target=self.relay_auto_restart, daemon=True)
        self.relay_timer_thread.start()

    # ==== リレー起動 ====
    def start_relay(self):
        target_ip = '{}'.format(self.check_text_format(self.target_ip.text()))
        self.ffmpeg_relay = multiprocessing.Process(target=_ffmpeg_relay, daemon=True, args=(target_ip))
        self.ffmpeg_relay.start()

    # ==== リレー自動再起動 ====
    def relay_auto_restart(self):
        while running[0]:
            time.sleep(60 * 45)  # 45分
            if not running[0]:
                break
            self.restart_relay()

    def restart_relay(self):
        if self.ffmpeg_relay:
            for pid in [pc.pid for pc in psutil.Process(self.ffmpeg_relay.pid).children(recursive=True)]:
                psutil.Process(pid).terminate()
        if running[0]:
            self.start_relay()

    # ==== ストリーム停止 ====
    def stop_stream(self):
        running[0] = False
        if self.ffmpeg_relay:
            for pid in [pc.pid for pc in psutil.Process(self.ffmpeg_relay.pid).children(recursive=True)]:
                psutil.Process(pid).terminate()
        self.ffmpeg = None
        self.ffmpeg_relay = None
        subprocess.run('taskkill /f /im ffmpeg.exe', shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.start_btn.setText("▶ 開始")


def main():
    app = QApplication(sys.argv)
    main_win = MainWindow()
    ui = Ui_ScreenSS()
    ui.setupUi(main_win)
    main_win.setFixedSize(main_win.size())
    main_win.show()
    app.exec()

if __name__ == '__main__':
    multiprocessing.freeze_support()
    main()