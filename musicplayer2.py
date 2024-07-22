import os
import sys
import pygame
from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QPushButton, QFileDialog, QSlider, QHBoxLayout, QVBoxLayout, QTextEdit, QListWidget, QListWidgetItem, QMessageBox, QProgressBar
from PyQt5.QtCore import Qt, QUrl, QThread, pyqtSignal
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent
from PyQt5.QtGui import QPixmap
import mutagen
import requests
import musicbrainzngs
import time  # Import time for simulation

musicbrainzngs.set_useragent("My Music Player", "1.0", "https://example.com/my_music_player")

class FetchMetadataThread(QThread):
    """Thread to fetch metadata in the background."""
    progress_signal = pyqtSignal(int)  # Signal for progress updates
    finished_signal = pyqtSignal()  # Signal for thread completion
    lyrics_signal = pyqtSignal(str)  # Signal for lyrics updates

    def __init__(self, filename, player):
        super().__init__()
        self.filename = filename
        self.player = player

    def run(self):
        try:
            self.progress_signal.emit(10)
            # Use mutagen to get song name, artist name, and album name
            if self.filename.lower().endswith('.m4a'):
                tags = mutagen.File(self.filename)
                artist = tags.get('\xa9ART', [''])[0]
                title = tags.get('\xa9nam', [''])[0]
                album = tags.get('\xa9alb', [''])[0]
            else:
                tags = mutagen.File(self.filename)
                artist = tags.get("TPE1", [""])[0]
                title = tags.get("TIT2", [""])[0]
                album = tags.get("TALB", [""])[0]
            self.progress_signal.emit(30)
            
        

            # Search for the recording on MusicBrainz
            result = musicbrainzngs.search_recordings(artist=artist, recording=title, release=album)
            if result['recording-list']:
                recording = result['recording-list'][0]
                release = musicbrainzngs.get_release_by_id(recording['release-list'][0]['id'])
                self.progress_signal.emit(50)

                # Update artist and title labels
                if 'artist-credit' in release['release'] and release['release']['artist-credit']:
                    self.player.artist_label.setText(release['release']['artist-credit'][0]['artist']['name'])
                self.player.title_label.setText(recording['title'])
                self.player.album_label.setText(release['release']['title'])
                if 'tag-list' in release['release']:
                    self.player.genre_label.setText(release['release']['tag-list'][0]['name'])
                    self.progress_signal.emit(70)

                # Fetch and display cover art
                if 'id' in release['release']:
                    cover_art_url = f"https://coverartarchive.org/release/{release['release']['id']}/front-250.jpg"
                image = QPixmap()
                if image.loadFromData(requests.get(cover_art_url).content):
                    self.player.cover_art_label.setPixmap(image.scaled(200, 200, Qt.KeepAspectRatio))
            else:
                # Display a dialog box if metadata is not found on MusicBrainz
                QMessageBox.information(self.player, "Metadata Not Found", "No metadata found on server.")

            # Fetch and display lyrics
            self.fetch_lyrics(artist, title)


            # Fetch and display artist art
            artist_art = self.fetch_artist_art(artist)
            if artist_art:
                self.player.fanart_label.setPixmap(artist_art.scaled(200, 200, Qt.KeepAspectRatio))  # Set fanart label

            # Fetch and display cover art
            if 'id' in release['release']:
                cover_art_url = f"https://coverartarchive.org/release/{release['release']['id']}/front-250.jpg"
            image = QPixmap()
            if image.loadFromData(requests.get(cover_art_url).content):
                self.player.cover_art_label.setPixmap(image.scaled(200, 200, Qt.KeepAspectRatio))
        except Exception as e:
            print(f"Error fetching meta {e}")
        finally:
            self.progress_signal.emit(100)
            self.finished_signal.emit()

    def fetch_lyrics(self, artist, title):
        try:
            # Replace with your preferred lyrics API and endpoint
            lyrics_url = f"https://api.lyrics.ovh/v1/{artist}/{title}"
            response = requests.get(lyrics_url)
            if response.status_code == 200:
                lyrics = response.json()['lyrics']
                self.lyrics_signal.emit(lyrics)  # Emit signal with lyrics
            else:
                self.lyrics_signal.emit("Lyrics not found")
        except Exception as e:
            print(f"Error fetching lyrics: {e}")

    def fetch_artist_art(self, artist_name):
        try:
            # Use a different API for fetching artist art
            url = f"https://api.deezer.com/search/artist?q={artist_name}"
            response = requests.get(url)

            if response.status_code == 200:
                data = response.json()
                if 'data' in data and data['data']:
                    artist_id = data['data'][0]['id']
                    artist_url = f"https://api.deezer.com/artist/{artist_id}"
                    artist_response = requests.get(artist_url)
                    if artist_response.status_code == 200:
                        artist_data = artist_response.json()
                        if 'picture_big' in artist_data:  # Corrected the condition
                            image_url = artist_data['picture_big']
                            image = QPixmap()
                            if image.loadFromData(requests.get(image_url).content):
                                return image
        except Exception as e:
            print(f"Error fetching artist art: {e}")
        return None

class MusicPlayer(QWidget):
    def __init__(self):
        super().__init__()

        self.init_ui()

    def init_ui(self):
        # Initialize Pygame mixer
        pygame.mixer.init()

        # Create media player
        self.player = QMediaPlayer()

        # Create widgets
        self.title_label = QLabel("No song loaded")
        self.artist_label = QLabel("")
        self.album_label = QLabel("")
        self.genre_label = QLabel("")
        self.cover_art_label = QLabel()
        self.fanart_label = QLabel()  # Added fanart label
        self.play_button = QPushButton("Play")
        self.pause_button = QPushButton("Pause")
        self.stop_button = QPushButton("Stop")
        self.seek_slider = QSlider(Qt.Horizontal)
        self.load_button = QPushButton("Load Songs")  # Changed button text
        self.volume_slider = QSlider(Qt.Horizontal)
        self.time_label = QLabel("0:00 / 0:00")  # Added time label
        self.lyrics_text = QTextEdit("No lyrics found")  # Moved lyrics_text creation to init_ui
        self.lyrics_text.setReadOnly(True)
        self.song_list_widget = QListWidget()  # Added song list widget
        self.current_folder_path = ""  # Initialize current folder path
        self.progress_bar = QProgressBar()  # Added progress bar
        self.progress_bar.setRange(0, 100)  # Set range for progress bar

        # Set up widgets
        self.cover_art_label.setFixedSize(200, 200)
        self.fanart_label.setFixedSize(200, 200)  # Set size for fanart label
        self.seek_slider.setRange(0, 0)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(50)

        # Connect signals
        self.play_button.clicked.connect(self.play_music)
        self.pause_button.clicked.connect(self.pause_music)
        self.stop_button.clicked.connect(self.stop_music)
        self.load_button.clicked.connect(self.open_file_dialog)
        self.seek_slider.sliderMoved.connect(self.set_position)
        self.volume_slider.valueChanged.connect(self.set_volume)
        self.player.positionChanged.connect(self.update_seek_slider)
        self.player.positionChanged.connect(self.update_time_label)  # Connect position change to update time label
        self.player.durationChanged.connect(self.update_seek_slider_range)
        self.song_list_widget.itemDoubleClicked.connect(self.play_selected_song)  # Connect song list double click

        # Create layout
        hbox = QHBoxLayout()
        hbox.addWidget(self.play_button)
        hbox.addWidget(self.load_button)
        hbox.addWidget(self.pause_button)
        hbox.addWidget(self.stop_button)

        # Layout for metadata
        metadata_layout = QVBoxLayout()
        metadata_layout.addWidget(self.title_label)
        metadata_layout.addWidget(self.artist_label)
        metadata_layout.addWidget(self.album_label)
        metadata_layout.addWidget(self.genre_label)

        # Layout for cover art, lyrics, and song list
        content_layout = QHBoxLayout()
        content_layout.addWidget(self.cover_art_label)
        content_layout.addWidget(self.fanart_label)  # Added fanart label to layout
        content_layout.addWidget(self.lyrics_text)
        content_layout.addWidget(self.song_list_widget)  # Added song list to layout

        # Layout for playback controls
        controls_layout = QHBoxLayout()
        controls_layout.addWidget(self.seek_slider)
        controls_layout.addWidget(self.time_label)  # Added time label to layout
        controls_layout.addWidget(self.volume_slider)

        # Main layout
        main_layout = QVBoxLayout()
        main_layout.addLayout(metadata_layout)
        main_layout.addLayout(content_layout)
        main_layout.addLayout(hbox)  # Added button layout to main layout
        main_layout.addLayout(controls_layout)
        main_layout.addWidget(self.progress_bar)  # Added progress bar to main layout

        self.setLayout(main_layout)
        self.setWindowTitle("Music Player")
        self.show()

        # Create metadata thread after initializing UI
        self.metadata_thread = FetchMetadataThread(None, self)  # Initialize with None for now
        self.metadata_thread.lyrics_signal.connect(self.update_lyrics)  # Connect lyrics signal

    def open_file_dialog(self):
        folder_path = QFileDialog.getExistingDirectory(self, "Select Music Folder")
        if folder_path:
            self.current_folder_path = folder_path  # Store the selected folder path
            self.load_folder(folder_path)

    def load_folder(self, folder_path):
        self.song_list_widget.clear()
        for file_name in os.listdir(folder_path):
            if file_name.endswith((".mp3", ".m4a")):  # Support both .mp3 and .m4a
                self.song_list_widget.addItem(QListWidgetItem(file_name, self.song_list_widget))

    def play_selected_song(self):
        selected_item = self.song_list_widget.currentItem()
        if selected_item:
            song_name = selected_item.text()
            self.load_music(song_name)
            self.play_music()

    def load_music(self, filename):
        # Construct the full file path using the selected folder path
        full_file_path = os.path.join(self.current_folder_path, filename)
        self.player.setMedia(QMediaContent(QUrl.fromLocalFile(full_file_path)))
        self.title_label.setText(filename)
        self.fetch_metadata(full_file_path)

    def play_music(self):
        self.player.play()

    def pause_music(self):
        self.player.pause()

    def stop_music(self):
        self.player.stop()

    def set_position(self, position):
        self.player.setPosition(position)

    def set_volume(self, volume):
        self.player.setVolume(volume)

    def update_seek_slider(self, position):
        self.seek_slider.setValue(position)

    def format_time(self, milliseconds):
        """Formats milliseconds to minutes:seconds format."""
        seconds = int(milliseconds / 1000)
        minutes = int(seconds / 60)
        seconds %= 60
        return f"{minutes}:{seconds:02}"

    def update_time_label(self, position):
        """Updates the time label with current position and duration."""
        current_time = self.format_time(position)
        total_time = self.format_time(self.player.duration())
        self.time_label.setText(f"{current_time} / {total_time}")

    def update_seek_slider_range(self, duration):
        self.seek_slider.setRange(0, duration)
        self.update_time_label(self.player.position())  # Update time label when duration changes

    def fetch_metadata(self, filename):
        self.progress_bar.setValue(0)  # Reset progress bar
        self.progress_bar.show()  # Show progress bar

        self.metadata_thread = FetchMetadataThread(filename, self)  # Create the thread here
        self.metadata_thread.progress_signal.connect(self.update_progress_bar)
        self.metadata_thread.finished_signal.connect(self.metadata_thread_finished)
        self.metadata_thread.lyrics_signal.connect(self.update_lyrics)  # Connect lyrics signal
        self.metadata_thread.start()

    def update_progress_bar(self, value):
        self.progress_bar.setValue(value)

    def metadata_thread_finished(self):
        self.progress_bar.hide()  # Hide progress bar after completion

    def update_lyrics(self, lyrics):
        self.lyrics_text.setText(lyrics)  # Update lyrics text from the signal

    def fetch_artist_art(self, artist_name):
        try:
            # Use a different API for fetching artist art
            url = f"https://api.deezer.com/search/artist?q={artist_name}"
            response = requests.get(url)

            if response.status_code == 200:
                data = response.json()
                if 'data' in data and data['data']:
                    artist_id = data['data'][0]['id']
                    artist_url = f"https://api.deezer.com/artist/{artist_id}"
                    artist_response = requests.get(artist_url)
                    if artist_response.status_code == 200:
                        artist_data = artist_response.json()
                        if 'picture_big' in artist_data:  # Corrected the condition
                            image_url = artist_data['picture_big']
                            image = QPixmap()
                            if image.loadFromData(requests.get(image_url).content):
                                return image
        except Exception as e:
            print(f"Error fetching artist art: {e}")
        return None

if __name__ == "__main__":
    
    app = QApplication(sys.argv)
    player = MusicPlayer()
    sys.exit(app.exec_())