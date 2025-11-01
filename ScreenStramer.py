import os
import subprocess
import sys
import threading
import time

import soundcard
import soundfile
from PySide6.QtCore import (QCoreApplication, QMetaObject, QRect,
                            QSize, Qt)
from PySide6.QtGui import (QIcon,
                           QImage, QPixmap)
from PySide6.QtWidgets import (QApplication, QLabel, QLineEdit, QPushButton,
                               QMainWindow)


class MainWindow(QMainWindow):
    def __init__(self, parent=None):
        super(MainWindow, self).__init__(parent)
        self.setAcceptDrops(True)
        self.setWindowIcon(QIcon(QPixmap(QSize(96, 96)).fromImage(QImage(os.path.join(os.getcwd(), 'icons', 'icon.png')))))

    def closeEvent(self, event, /):
        subprocess.run('taskkill /f /im ffmpeg.exe', shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if os.path.exists(os.path.join(os.path.expanduser('~'), 'tmp.wav')):
            os.remove(os.path.join(os.path.expanduser('~'), 'tmp.wav'))

class Ui_ScreenSS(object):
    def setupUi(self, ScreenSS):
        if not ScreenSS.objectName():
            ScreenSS.setObjectName(u"ScreenSS")
        ScreenSS.resize(387, 267)
        self.ttile = QLabel(ScreenSS)
        self.ttile.setObjectName(u"ttile")
        self.ttile.setGeometry(QRect(50, 40, 271, 41))
        self.ttile.setTextFormat(Qt.TextFormat.PlainText)
        self.ttile.setScaledContents(False)
        self.ttile.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.target_ip = QLineEdit(ScreenSS)
        self.target_ip.setObjectName(u"target_ip")
        self.target_ip.setGeometry(QRect(100, 100, 281, 41))
        self.target_label = QLabel(ScreenSS)
        self.target_label.setObjectName(u"target_label")
        self.target_label.setGeometry(QRect(0, 106, 101, 31))
        self.target_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.start_btn = QPushButton(ScreenSS)
        self.start_btn.setObjectName(u"start_btn")
        self.start_btn.clicked.connect(self.start)
        self.start_btn.setGeometry(QRect(20, 180, 351, 61))
        self.check = True
        self.thread = None
        self.thread2 = None

        self.retranslateUi(ScreenSS)

        QMetaObject.connectSlotsByName(ScreenSS)
    # setupUi

    def retranslateUi(self, ScreenSS):
        ScreenSS.setWindowTitle('Screen Streamer')
        self.ttile.setText(QCoreApplication.translate("ScreenSS", u"Screen Streamer", None))
        self.target_label.setText('対象iP')
        self.start_btn.setText('開始')
    # retranslateUi

    def get_audio(self):
        while True:
            with soundcard.get_microphone(id='{}'.format(soundcard.default_speaker().name), include_loopback=True).recorder(samplerate=44100) as f:
                soundfile.write(os.path.join(os.path.expanduser('~'), 'tmp.wav'), data=f.record(48000), samplerate=44100)

    def process(self, ip):
        if ip != '':
            time.sleep(3)
            subprocess.run('ffmpeg -stream_loop -13 -f wav -i {} -video_size 1920x1080 -f gdigrab -i desktop -rtbufsize 100M -vcodec libx264 -preset ultrafast -tune zerolatency -acodec aac -f mpegts udp://{}:1889'.format(os.path.join(os.path.expanduser('~'), 'tmp.wav'), ip), shell=True, stderr=subprocess.PIPE, stdout=subprocess.PIPE)

    def check_text_format(self, text):
        if text != '':
            if 'udp://' == text[0:6]:
                text = text.replace(text[0:6], '')
            if ':' in text:
                text = text.split(':')[0]
            return text
        else:
            return ''

    def start(self):
        if self.check:
            self.check = False
            self.start_btn.setText('ストップ')
            self.thread = threading.Thread(target=self.process, daemon=True, args=(self.check_text_format(self.target_ip.text()), ))
            self.thread2 = threading.Thread(target=self.get_audio, daemon=True)
            self.thread.start()
            self.thread2.start()
        else:
            self.check = True
            subprocess.run('taskkill /f /im ffmpeg.exe', shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            # os.remove(os.path.join(os.path.expanduser('~'), 'tmp.wav'))
            self.start_btn.setText('開始')
            self.thread.join(0)
            self.thread2.join(0)

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