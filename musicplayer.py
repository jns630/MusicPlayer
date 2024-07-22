
import sys
import os
from PyQt5.QtWidgets import (
    QApplication,
    QWidget,
    QLabel,
    QPushButton,
    QHBoxLayout,
    QVBoxLayout,
    QSlider,
    QFileDialog,
)
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent
from PyQt5.QtMultimediaWidgets import QVideoWidget
from PyQt5.QtGui import QIcon, QPixmap
from PyQt5.QtCore import Qt, QUrl, QTimer
import pygame
import musicbrainzngs

musicbrainzngs.set_useragent("MusicPlayer", "1.0", "https://github.com/yourusername")

class MusicPlayer(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Music Player")
        self.setGeometry(100, 100, 800, 500)

        # Initialize pygame mixer
        pygame.mixer.init()

        # Create media player
        self.player = QMediaPlayer()

        # Create video widget
        self.video_widget = QVideoWidget()
        self.video_widget.hide()  # Hide video widget initially

        # Create buttons
        self.play_button = QPushButton()
        self.play_button.setIcon(QIcon("icons/play.png"))
        self.play_button.clicked.connect(self.play_music)

        self.pause_button = QPushButton()
        self.pause_button.setIcon(QIcon("icons/pause.png"))
        self.pause_button.clicked.connect(self.pause_music)

        self.stop_button = QPushButton()
        self.stop_button.setIcon(QIcon("icons/stop.png"))
        self.stop_button.clicked.connect(self.stop_music)

        self.open_button = QPushButton("Open File")
        self.open_button.clicked.connect(self.open_file)

        # Create volume slider
        self.volume_slider = QSlider(Qt.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(50)
        self.volume_slider.valueChanged.connect(self.set_volume)

        # Create seekbar
        self.seekbar = QSlider(Qt.Horizontal)
        self.seekbar.setRange(0, 0)
        self.seekbar.sliderMoved.connect(self.seek_music)

        # Create labels
        self.song_title_label = QLabel("No song loaded")
        self.artist_label = QLabel("")
        self.album_label = QLabel("")
        self.cover_art_label = QLabel()

        # Create layouts
        control_layout = QHBoxLayout()
        control_layout.addWidget(self.play_button)
        control_layout.addWidget(self.pause_button)
        control_layout.addWidget(self.stop_button)
        control_layout.addWidget(self.open_button)
        control_layout.addWidget(self.volume_slider)

        info_layout = QVBoxLayout()
        info_layout.addWidget(self.song_title_label)
        info_layout.addWidget(self.artist_label)
        info_layout.addWidget(self.album_label)
        info_layout.addWidget(self.cover_art_label)

        main_layout = QVBoxLayout()
        main_layout.addWidget(self.video_widget)
        main_layout.addLayout(info_layout)
        main_layout.addWidget(self.seekbar)
        main_layout.addLayout(control_layout)

        self.setLayout(main_layout)

        # Timer to update seekbar
        self.timer = QTimer(self)
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self.update_seekbar)

    def open_file(self):
        filename, _ = QFileDialog.getOpenFileName(self, "Open Music File", "", "MP3 Files (*.mp3)")
        if filename:
            self.load_music(filename)

    def load_music(self, filename):
        self.player.setMedia(QMediaContent(QUrl.fromLocalFile(filename)))
        self.song_title_label.setText(os.path.basename(filename))
        self.get_metadata(filename)
        self.play_music()

    def play_music(self):
        self.player.play()
        self.timer.start()

    def pause_music(self):
        self.player.pause()
        self.timer.stop()

    def stop_music(self):
        self.player.stop()
        self.timer.stop()
        self.seekbar.setValue(0)

    def set_volume(self, value):
        self.player.setVolume(value)

    def seek_music(self, position):
        self.player.setPosition(position * 1000)

    def update_seekbar(self):
        self.seekbar.setValue(int(self.player.position() / 1000))
        self.seekbar.setMaximum(int(self.player.duration() / 1000))

    def get_metadata(self, filename):
        try:
            song = pygame.mixer.Sound(filename)
            title = song.get_tag("title")
            artist = song.get_tag("artist")
            album = song.get_tag("album")

            self.song_title_label.setText(title if title else os.path.basename(filename))
            self.artist_label.setText(f"Artist: {artist}" if artist else "")
            self.album_label.setText(f"Album: {album}" if album else "")

        except Exception as e:
            print(f"Error fetching meta {e}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    player = MusicPlayer()
    player.show()
    sys.exit(app.exec_())
