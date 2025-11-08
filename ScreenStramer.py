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

running = [True]
ffmpeg_proc = [None]


def run_ffmpeg(target_ip):
    """FFmpegプロセスを起動"""
    proc = subprocess.Popen([
        "ffmpeg", "-hide_banner", "-loglevel", "error",
        "-f", "s16le", "-ar", "44100", "-ac", "2", "-i", "pipe:0",
        "-f", "gdigrab", "-video_size", "1920x1080", "-i", "desktop",
        "-framerate", "60", "-preset", "ultrafast", "-tune", "zerolatency",
        "-vf", "scale=1920:1080:flags=lanczos,hqdn3d=1.5:1.5:6:6",
        "-af", "afftdn=nf=-25",
        "-f", "mpegts", f"udp://{target_ip}:1889?pkt_size=1316"
    ], stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, shell=True)
    print(f"[FFmpeg] 起動: {target_ip}")
    return proc


def restart_ffmpeg(target_ip):
    """FFmpegを強制停止して再起動"""
    if ffmpeg_proc[0]:
        try:
            for pid in [ffmpeg_proc[0].pid] + [p.pid for p in psutil.Process(ffmpeg_proc[0].pid).children(recursive=True)]:
                psutil.Process(pid).terminate()
        except Exception:
            pass
    ffmpeg_proc[0] = run_ffmpeg(target_ip)


def stream_audio(target_ip):
    """ループバック音声を録音してFFmpegに渡す"""
    mic = sc.get_microphone(id=sc.default_speaker().name, include_loopback=True)
    samplerate = 44100
    chunk = 4410  # 約0.1秒分

    ffmpeg_proc[0] = run_ffmpeg(target_ip)

    # 🔄 FFmpegを45分ごとに再起動
    threading.Thread(target=ffmpeg_auto_restart, args=(target_ip,), daemon=True).start()

    with mic.recorder(samplerate=samplerate, channels=2) as rec:
        while running[0]:
            try:
                data = rec.record(numframes=chunk)
                pcm = np.int16(data * 32767).tobytes()
                if ffmpeg_proc[0] and ffmpeg_proc[0].poll() is None:
                    ffmpeg_proc[0].stdin.write(pcm)
            except (BrokenPipeError, OSError):
                time.sleep(1)


def ffmpeg_auto_restart(target_ip):
    """45分ごとにFFmpegを再起動"""
    while running[0]:
        time.sleep(60 * 45)
        if running[0]:
            print("[FFmpeg] 45分経過 → 再起動します")
            restart_ffmpeg(target_ip)

# ==========================================
# GUI構成
# ==========================================
class MainWindow(QMainWindow):
    def __init__(self, parent=None):
        super(MainWindow, self).__init__(parent)
        self.setAcceptDrops(True)
        icon_path = os.path.join(os.getcwd(), 'icons', 'icon.png')
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(QPixmap(QSize(96, 96)).fromImage(QImage(icon_path))))

    def closeEvent(self, event):
        subprocess.run('taskkill /f /im ffmpeg.exe', shell=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


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
        ScreenSS.setWindowTitle("Screen Streamer (UDP LocalIP + Auto Restart)")
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

        target_ip = '{}'.format(self.check_text_format(self.target_ip.text()))
        self.ffmpeg_audio = threading.Thread(target=stream_audio, args=(target_ip,), daemon=True)
        self.ffmpeg_audio.start()

    def stop_stream(self):
        running[0] = False
        self.ffmpeg = None
        subprocess.run('taskkill /f /im ffmpeg.exe', shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.start_btn.setText("▶ 開始")


# ==========================================
# アプリ起動
# ==========================================
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