import os
import subprocess
import sys
import threading
import platform
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
        if platform.system() == 'Windows':
            subprocess.run('taskkill /f /im ffplay.exe', shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        else:
            subprocess.run('killall -9 ffplay', shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

class Ui_ScreenSS(object):
    def setupUi(self, ScreenSS):
        if not ScreenSS.objectName():
            ScreenSS.setObjectName(u"ScreenSS")
        ScreenSS.resize(387, 267)

        self.ttile = QLabel(ScreenSS)
        self.ttile.setGeometry(QRect(50, 40, 271, 41))
        self.ttile.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.ttile.setText("Screen Streamer")
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
            self.running = True
            self.audio_thread = threading.Thread(target=self.stream_audio, daemon=True)
            self.audio_thread.start()
            self.start_btn.setText("ストップ")
        else:
            # 停止処理
            self.running = False
            if self.ffmpeg:
                self.ffmpeg.stdin.close()
                if platform.system() == 'Windows':
                    subprocess.run('taskkill /f /im ffplay.exe', shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                else:
                    subprocess.run('killall -9 ffplay', shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                self.ffmpeg = None
            self.start_btn.setText("開始")
            print("🛑 ストリーム停止")

    def stream_audio(self):
        subprocess.run('ffplay -fflags nobuffer -flags low_delay -framedrop -sync ext "udp://localhost:1889"', shell=True)

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