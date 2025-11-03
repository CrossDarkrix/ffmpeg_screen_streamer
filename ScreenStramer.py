import os
import subprocess
import sys
import threading

import numpy as np
import soundcard as sc
from PySide6.QtCore import Qt, QRect, QMetaObject, QSize
from PySide6.QtGui import QIcon, QPixmap, QImage
from PySide6.QtWidgets import QApplication, QLabel, QLineEdit, QPushButton, QMainWindow


class MainWindow(QMainWindow):
    def __init__(self, parent=None):
        super(MainWindow, self).__init__(parent)
        self.setAcceptDrops(True)
        icon_path = os.path.join(os.getcwd(), 'icons', 'icon.png')
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(QPixmap(QSize(96, 96)).fromImage(QImage(icon_path))))

    def closeEvent(self, event):
        subprocess.run('taskkill /f /im ffmpeg.exe', shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

class Ui_ScreenSS(object):
    def setupUi(self, ScreenSS):
        if not ScreenSS.objectName():
            ScreenSS.setObjectName(u"ScreenSS")
        ScreenSS.resize(387, 267)

        self.ttile = QLabel(ScreenSS)
        self.ttile.setGeometry(QRect(50, 40, 271, 41))
        self.ttile.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.ttile.setText("Screen Streamer")

        self.target_label = QLabel(ScreenSS)
        self.target_label.setGeometry(QRect(0, 106, 101, 31))
        self.target_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.target_label.setText("対象IP")

        self.target_ip = QLineEdit(ScreenSS)
        self.target_ip.setGeometry(QRect(100, 100, 281, 41))

        self.start_btn = QPushButton(ScreenSS)
        self.start_btn.setGeometry(QRect(20, 180, 351, 61))
        self.start_btn.setText("開始")
        self.start_btn.clicked.connect(self.start)

        self.ffmpeg = None
        self.audio_thread = None
        self.running = False

        QMetaObject.connectSlotsByName(ScreenSS)

    def clean_ip(self, text):
        if text.startswith("udp://"):
            text = text[6:]
        if ":" in text:
            text = text.split(":")[0]
        return text

    def start(self):
        if not self.running:
            target_ip = self.clean_ip(self.target_ip.text())
            if not target_ip:
                print("Error: IPが入力されていません。")
                return

            # FFmpeg起動
            self.ffmpeg = subprocess.Popen([
                "ffmpeg", "-hide_banner", "-loglevel", "error", 
                "-fflags", "nobuffer", "-flags", "low_delay", "-rtbufsize", "100M",
                "-f", "s16le", "-threads", "350", "-ar", "44100", "-ac", "2", "-i", "pipe:0",
                "-f", "gdigrab", "-framerate", "30", "-video_size", "1920x1080", "-i", "desktop",
                "-vcodec", "libx264", "-preset", "ultrafast", "-tune", "zerolatency",
                "-acodec", "aac", "-b:a", "256k",
                "-f", "mpegts", f"udp://{target_ip}:1889"
            ], stdin=subprocess.PIPE, shell=True)
            # 音声スレッド開始
            self.running = True
            self.audio_thread = threading.Thread(target=self.stream_audio, daemon=True)
            self.audio_thread.start()

            self.start_btn.setText("ストップ")
            print(f"🎥 ストリーム開始: udp://{target_ip}:1889")

        else:
            # 停止処理
            self.running = False
            if self.ffmpeg:
                self.ffmpeg.stdin.close()
                subprocess.run('taskkill /f /im ffmpeg.exe', shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                self.ffmpeg = None
            self.start_btn.setText("開始")
            print("🛑 ストリーム停止")

    def stream_audio(self):
        try:
            mic = sc.get_microphone(id=sc.default_speaker().name, include_loopback=True)
            samplerate = 44100
            chunk = 4410  # 約0.1秒分

            with mic.recorder(samplerate=samplerate, channels=2) as rec:
                while self.running and self.ffmpeg and self.ffmpeg.poll() is None:
                    data = rec.record(numframes=chunk)
                    pcm = np.int16(data * 32767).tobytes()
                    try:
                        self.ffmpeg.stdin.write(pcm)
                    except (BrokenPipeError, OSError):
                        break
        except Exception as e:
            print(f"[AudioThread Error] {e}")
        finally:
            if self.ffmpeg:
                try:
                    self.ffmpeg.stdin.close()
                except Exception:
                    pass

def main():
    app = QApplication(sys.argv)
    main_win = MainWindow()
    ui = Ui_ScreenSS()
    ui.setupUi(main_win)
    main_win.setFixedSize(main_win.size())
    main_win.show()
    app.exec()

if __name__ == '__main__':
    main()