import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import pygame
import os
import random
from pathlib import Path
import threading
from datetime import timedelta
import json
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
try:
    from mutagen._file import File as MutagenFile
    MUTAGEN_AVAILABLE = True
except Exception:
    MutagenFile = None
    MUTAGEN_AVAILABLE = False

# ============================================================================
# MUSICFLOW - ADVANCED SPOTIFY-LIKE MUSIC PLAYER
# Professional Design with Full Functionality
# ============================================================================

class ModernMusicPlayer:
    def __init__(self, root):
        self.root = root
        self.root.title("🎵 MusicFlow - Professional Music Player")
        self.root.geometry("1400x800")
        self.root.minsize(1200, 700)
        
        # ====================== COLOR SCHEME (Spotify-Inspired) =======================
        # Dark mode with vibrant accents (like Spotify)
        self.BG_PRIMARY = "#121212"      # Dark background
        self.BG_SECONDARY = "#1DB954"    # Spotify green
        self.BG_TERTIARY = "#191414"     # Darker background
        self.TEXT_PRIMARY = "#FFFFFF"    # White text
        self.TEXT_SECONDARY = "#B3B3B3"  # Gray text
        self.ACCENT_COLOR = "#1ED760"    # Bright green
        self.BUTTON_COLOR = "#1DB954"    # Spotify green
        self.HOVER_COLOR = "#1aa34a"     # Darker green
        
        self.root.configure(bg=self.BG_PRIMARY)
        self.root.option_add("*Font", "{Segoe UI} 10")
        
        # ====================== PYGAME MIXER INIT =======================
        pygame.mixer.init()
        
        # ====================== VARIABLES =======================
        self.playlist = []
        self.current_index = -1
        self.is_playing = False
        self.is_paused = False
        self.shuffle_mode = False
        self.repeat_mode = 0  # 0: no repeat, 1: repeat all, 2: repeat one
        self.music_folder = "./songs"
        self.current_song_length = 0
        self.current_position = 0
        self.is_seeking = False
        self.played_indices = []
        
        # Create songs folder if it doesn't exist
        Path(self.music_folder).mkdir(exist_ok=True)
        
        # ====================== UI SETUP =======================
        self.setup_ui()
        
        # Load songs
        self.load_songs()
        
        # Start update thread for real-time updates
        self.update_thread_active = True
        self.start_update_thread()
        
    def load_songs(self):
        """Load all supported music files from the songs folder"""
        supported_formats = ('.mp3', '.wav', '.flac', '.ogg', '.m4a')
        self.playlist = []
        
        try:
            if os.path.exists(self.music_folder):
                for file in os.listdir(self.music_folder):
                    if file.lower().endswith(supported_formats):
                        full_path = os.path.join(self.music_folder, file)
                        self.playlist.append(full_path)
            
            self.playlist.sort()
            # maintain a filtered copy for search/filter operations
            self.filtered_playlist = self.playlist.copy()
            # precompute durations for faster UI updates
            self.song_metadata = {}
            for p in self.playlist:
                try:
                    self.song_metadata[p] = self.get_duration(p)
                except Exception:
                    self.song_metadata[p] = 0
            self.update_song_list()
            
            if self.playlist:
                self.status_label.config(text=f"✅ Loaded {len(self.playlist)} songs")
            else:
                self.status_label.config(text="❌ No songs found. Add .mp3/.wav files to 'songs' folder")
        except Exception as e:
            self.status_label.config(text=f"❌ Error loading songs: {str(e)}")

    def setup_ui(self):
        """Setup the modern Spotify-like interface"""
        
        # ==================== MAIN CONTAINER ====================
        main_container = tk.Frame(self.root, bg=self.BG_PRIMARY)
        main_container.pack(fill=tk.BOTH, expand=True)
        
        # ==================== TOP NAVIGATION BAR ====================
        nav_frame = tk.Frame(main_container, bg=self.BG_TERTIARY, height=70)
        nav_frame.pack(fill=tk.X, side=tk.TOP)
        nav_frame.pack_propagate(False)
        
        title_label = tk.Label(
            nav_frame,
            text="🎵 MusicFlow",
            font=("Segoe UI", 20, "bold"),
            fg=self.ACCENT_COLOR,
            bg=self.BG_TERTIARY
        )
        title_label.pack(side=tk.LEFT, padx=20, pady=15)
        
        # Status display
        self.status_label = tk.Label(
            nav_frame,
            text="Loading...",
            font=("Segoe UI", 10),
            fg=self.TEXT_SECONDARY,
            bg=self.BG_TERTIARY
        )
        self.status_label.pack(side=tk.LEFT, padx=10, pady=15)
        
        refresh_btn = tk.Button(
            nav_frame,
            text="🔄 Refresh",
            font=("Segoe UI", 10, "bold"),
            bg=self.BUTTON_COLOR,
            fg=self.TEXT_PRIMARY,
            relief=tk.FLAT,
            cursor="hand2",
            padx=15,
            pady=8,
            command=self.refresh_playlist,
            activebackground=self.HOVER_COLOR
        )
        refresh_btn.pack(side=tk.RIGHT, padx=20, pady=15)
        
        # ==================== MAIN CONTENT (Two Columns) ====================
        content_frame = tk.Frame(main_container, bg=self.BG_PRIMARY)
        content_frame.pack(fill=tk.BOTH, expand=True, padx=0)
        
        # LEFT SIDEBAR - Playlist
        left_frame = tk.Frame(content_frame, bg=self.BG_SECONDARY, width=350)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=False)
        left_frame.pack_propagate(False)
        
        playlist_title = tk.Label(
            left_frame,
            text="📋 PLAYLIST",
            font=("Segoe UI", 14, "bold"),
            fg=self.TEXT_PRIMARY,
            bg=self.BG_SECONDARY
        )
        playlist_title.pack(fill=tk.X, padx=15, pady=(15, 10))
        # Search/filter box
        search_frame = tk.Frame(left_frame, bg=self.BG_SECONDARY)
        search_frame.pack(fill=tk.X, padx=10, pady=(0, 6))

        self.search_var = tk.StringVar()
        search_entry = tk.Entry(
            search_frame,
            textvariable=self.search_var,
            font=("Segoe UI", 11),
            relief=tk.FLAT
        )
        search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.search_var.trace_add('write', lambda *_: self.filter_songs())

        clear_btn = tk.Button(
            search_frame,
            text="✖",
            command=lambda: self.search_var.set(''),
            bg=self.BG_TERTIARY,
            fg=self.TEXT_PRIMARY,
            relief=tk.FLAT,
            cursor="hand2",
            padx=8
        )
        clear_btn.pack(side=tk.LEFT, padx=(6, 0))

        # Playlist as Treeview for better presentation
        tree_frame = tk.Frame(left_frame, bg=self.BG_SECONDARY)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

        self.song_tree = ttk.Treeview(
            tree_frame,
            columns=("title", "duration"),
            show='headings',
            selectmode='browse',
            height=20
        )
        self.song_tree.heading('title', text='Title')
        self.song_tree.heading('duration', text='Duration')
        self.song_tree.column('title', anchor='w', width=220)
        self.song_tree.column('duration', anchor='center', width=70)

        tree_scroll = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.song_tree.yview)
        self.song_tree.configure(yscrollcommand=tree_scroll.set)
        tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.song_tree.pack(fill=tk.BOTH, expand=True)

        self.song_tree.bind('<Double-1>', self.play_selected)
        self.song_tree.bind('<<TreeviewSelect>>', self.select_song)
        
        # RIGHT SECTION - Now Playing & Controls
        right_frame = tk.Frame(content_frame, bg=self.BG_PRIMARY)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # ==================== NOW PLAYING SECTION ====================
        now_playing_frame = tk.Frame(right_frame, bg=self.BG_TERTIARY)
        now_playing_frame.pack(fill=tk.X, pady=(0, 20))
        
        # Album art placeholder
        art_label = tk.Label(
            now_playing_frame,
            text="🎧",
            font=("Arial", 100),
            fg=self.ACCENT_COLOR,
            bg=self.BG_TERTIARY
        )
        art_label.pack(pady=30)
        
        # Song title
        self.song_title = tk.Label(
            now_playing_frame,
            text="No song playing",
            font=("Segoe UI", 24, "bold"),
            fg=self.TEXT_PRIMARY,
            bg=self.BG_TERTIARY,
            wraplength=400
        )
        self.song_title.pack(pady=(0, 10))
        
        # Song artist/info
        self.song_info = tk.Label(
            now_playing_frame,
            text="Add songs to get started",
            font=("Segoe UI", 12),
            fg=self.TEXT_SECONDARY,
            bg=self.BG_TERTIARY,
            wraplength=400
        )
        self.song_info.pack(pady=(0, 30))
        
        # ==================== PROGRESS BAR SECTION ====================
        progress_frame = tk.Frame(right_frame, bg=self.BG_PRIMARY)
        progress_frame.pack(fill=tk.X, pady=(0, 15))
        
        self.time_label = tk.Label(
            progress_frame,
            text="00:00",
            font=("Segoe UI", 10),
            fg=self.TEXT_SECONDARY,
            bg=self.BG_PRIMARY
        )
        self.time_label.pack(side=tk.LEFT)
        
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Scale(
            progress_frame,
            from_=0,
            to=100,
            orient=tk.HORIZONTAL,
            variable=self.progress_var,
            command=self.on_progress_change
        )
        self.progress_bar.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(10, 10))
        self.progress_bar.config(style='Green.Horizontal.TScale')
        
        self.duration_label = tk.Label(
            progress_frame,
            text="00:00",
            font=("Segoe UI", 10),
            fg=self.TEXT_SECONDARY,
            bg=self.BG_PRIMARY
        )
        self.duration_label.pack(side=tk.RIGHT)
        
        # ==================== VOLUME CONTROL ====================
        volume_frame = tk.Frame(right_frame, bg=self.BG_PRIMARY)
        volume_frame.pack(fill=tk.X, pady=(0, 20))
        
        volume_label = tk.Label(
            volume_frame,
            text="🔊 Volume:",
            font=("Segoe UI", 11, "bold"),
            fg=self.TEXT_PRIMARY,
            bg=self.BG_PRIMARY
        )
        volume_label.pack(side=tk.LEFT, padx=(0, 10))
        
        self.volume_var = tk.DoubleVar(value=70)
        self.volume_slider = ttk.Scale(
            volume_frame,
            from_=0,
            to=100,
            orient=tk.HORIZONTAL,
            variable=self.volume_var,
            command=self.set_volume
        )
        self.volume_slider.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        self.volume_slider.config(style='Green.Horizontal.TScale')
        
        self.volume_label_display = tk.Label(
            volume_frame,
            text="70%",
            font=("Segoe UI", 10),
            fg=self.ACCENT_COLOR,
            bg=self.BG_PRIMARY,
            width=5
        )
        self.volume_label_display.pack(side=tk.LEFT)
        
        pygame.mixer.music.set_volume(0.7)
        
        # ==================== PLAYBACK CONTROLS ====================
        control_frame = tk.Frame(right_frame, bg=self.BG_PRIMARY)
        control_frame.pack(fill=tk.X, pady=(0, 20))
        
        button_style = {
            "font": ("Segoe UI", 12, "bold"),
            "fg": self.TEXT_PRIMARY,
            "bg": self.BUTTON_COLOR,
            "relief": tk.FLAT,
            "cursor": "hand2",
            "activebackground": self.HOVER_COLOR,
            "activeforeground": self.TEXT_PRIMARY,
            "padx": 20,
            "pady": 12,
            "height": 1
        }
        
        # Previous button
        self.prev_btn = tk.Button(
            control_frame,
            text="⏮️  PREVIOUS",
            command=self.prev_song,
            **button_style
        )
        self.prev_btn.pack(side=tk.LEFT, padx=5, fill=tk.BOTH, expand=True)
        
        # Play/Pause button
        self.play_btn = tk.Button(
            control_frame,
            text="▶️  PLAY",
            command=self.play_pause,
            **button_style
        )
        self.play_btn.pack(side=tk.LEFT, padx=5, fill=tk.BOTH, expand=True)
        
        # Next button
        self.next_btn = tk.Button(
            control_frame,
            text="NEXT  ⏭️",
            command=self.next_song,
            **button_style
        )
        self.next_btn.pack(side=tk.LEFT, padx=5, fill=tk.BOTH, expand=True)
        
        # ==================== FEATURE BUTTONS ====================
        feature_frame = tk.Frame(right_frame, bg=self.BG_PRIMARY)
        feature_frame.pack(fill=tk.X, pady=(0, 20))
        
        feature_button_style = {
            "font": ("Segoe UI", 10, "bold"),
            "fg": self.TEXT_PRIMARY,
            "bg": self.BG_TERTIARY,
            "relief": tk.FLAT,
            "cursor": "hand2",
            "activebackground": self.BUTTON_COLOR,
            "activeforeground": self.TEXT_PRIMARY,
            "padx": 15,
            "pady": 10,
            "height": 1,
            "bd": 1
        }
        
        # Shuffle button
        self.shuffle_btn = tk.Button(
            feature_frame,
            text="🔀 SHUFFLE",
            command=self.toggle_shuffle,
            **feature_button_style
        )
        self.shuffle_btn.pack(side=tk.LEFT, padx=5, fill=tk.BOTH, expand=True)
        
        # Repeat button
        self.repeat_btn = tk.Button(
            feature_frame,
            text="🔁 REPEAT",
            command=self.toggle_repeat,
            **feature_button_style
        )
        self.repeat_btn.pack(side=tk.LEFT, padx=5, fill=tk.BOTH, expand=True)
        
        # Browse folder button
        browse_btn = tk.Button(
            feature_frame,
            text="📂 BROWSE",
            command=self.browse_folder,
            **feature_button_style
        )
        browse_btn.pack(side=tk.LEFT, padx=5, fill=tk.BOTH, expand=True)
        
        # ==================== STATS ====================
        stats_frame = tk.Frame(right_frame, bg=self.BG_TERTIARY)
        stats_frame.pack(fill=tk.X, pady=10)
        
        self.stats_label = tk.Label(
            stats_frame,
            text="Songs: 0 | Currently: No song",
            font=("Segoe UI", 10),
            fg=self.TEXT_SECONDARY,
            bg=self.BG_TERTIARY,
            justify=tk.LEFT
        )
        self.stats_label.pack(fill=tk.X, padx=15, pady=10)
        
        # Configure ttk styles
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('Green.Horizontal.TScale', background=self.BG_PRIMARY)
        style.configure('Dark.Vertical', background=self.BG_TERTIARY, troughcolor=self.BG_TERTIARY)
        
    def update_song_list(self):
        """Update the song listbox"""
        # Use filtered playlist if present
        try:
            self.song_tree.delete(*self.song_tree.get_children())
        except Exception:
            pass

        display_list = getattr(self, 'filtered_playlist', self.playlist)

        if not display_list:
            self.song_tree.insert('', tk.END, iid='no_songs', values=("No songs found",))
            return

        for idx, song_path in enumerate(display_list):
            # If filtered_playlist is a subset, ensure we insert using original playlist index
            try:
                real_idx = self.playlist.index(song_path)
            except ValueError:
                real_idx = idx

            song_name = os.path.basename(song_path)
            song_name_clean = os.path.splitext(song_name)[0]

            display_text = song_name_clean
            if real_idx == self.current_index:
                display_text = f"▶️  {song_name_clean}"

            self.song_tree.insert('', tk.END, iid=str(real_idx), values=(display_text,))

        # ensure currently playing visible
        if self.current_index >= 0:
            try:
                self.song_tree.see(str(self.current_index))
                self.song_tree.selection_set(str(self.current_index))
            except Exception:
                pass

    def filter_songs(self):
        """Filter songs based on search entry"""
        query = getattr(self, 'search_var', tk.StringVar()).get().strip().lower()
        if not query:
            self.filtered_playlist = self.playlist.copy()
        else:
            self.filtered_playlist = [p for p in self.playlist if query in os.path.basename(p).lower()]

        self.update_song_list()
        # update status
        if hasattr(self, 'status_label'):
            self.status_label.config(text=f"Filtered: {len(self.filtered_playlist)} / {len(self.playlist)}")
    
    def play_pause(self):
        """Play or pause the current song"""
        if not self.playlist:
            messagebox.showwarning("No Songs", "Add songs to the 'songs' folder first!")
            return
        
        if self.is_paused:
            pygame.mixer.music.unpause()
            self.is_paused = False
            self.is_playing = True
            self.play_btn.config(text="⏸️  PAUSE")
        elif self.is_playing:
            pygame.mixer.music.pause()
            self.is_paused = True
            self.play_btn.config(text="▶️  PLAY")
        else:
            # Start playing
            if self.current_index < 0:
                self.current_index = 0 if not self.shuffle_mode else random.randint(0, len(self.playlist) - 1)
            self.play_song(self.current_index)
    
    def play_song(self, index):
        """Play the song at the specified index"""
        if index < 0 or index >= len(self.playlist):
            return
        
        self.current_index = index
        
        try:
            song_path = self.playlist[index]
            pygame.mixer.music.load(song_path)
            pygame.mixer.music.play()
            
            self.is_playing = True
            self.is_paused = False
            self.play_btn.config(text="⏸️  PAUSE")
            
            # Update display
            song_name = os.path.basename(song_path)
            song_name_clean = os.path.splitext(song_name)[0]
            self.song_title.config(text=song_name_clean)
            self.song_info.config(text=f"Track {index + 1} of {len(self.playlist)}")
            
            self.update_song_list()
            self.update_stats()

            # set current song length (seconds) and update duration label
            try:
                length = self.song_metadata.get(song_path, None)
                if not length:
                    length = self.get_duration(song_path)
                    self.song_metadata[song_path] = length
                self.current_song_length = length or 0
                self.duration_label.config(text=self.format_time(self.current_song_length) if self.current_song_length > 0 else "--:--")
                self.time_label.config(text="00:00")
                self.progress_var.set(0)
            except Exception:
                self.current_song_length = 0
            
            # Add to played history for shuffle
            if index not in self.played_indices:
                self.played_indices.append(index)
                
        except Exception as e:
            messagebox.showerror("Playback Error", f"Could not play song: {str(e)}")
    
    def next_song(self):
        """Play next song"""
        if not self.playlist:
            return
        
        if self.shuffle_mode:
            # Shuffle mode - pick random song
            if len(self.played_indices) >= len(self.playlist):
                self.played_indices = []  # Reset if all songs played
            
            while True:
                idx = random.randint(0, len(self.playlist) - 1)
                if idx not in self.played_indices:
                    self.play_song(idx)
                    break
        else:
            # Sequential mode
            next_idx = (self.current_index + 1) % len(self.playlist)
            self.play_song(next_idx)
    
    def prev_song(self):
        """Play previous song"""
        if not self.playlist:
            return
        
        prev_idx = (self.current_index - 1) % len(self.playlist)
        self.play_song(prev_idx)
    
    def play_selected(self, event):
        """Play the selected song from listbox"""
        try:
            sel = self.song_tree.selection()
            if sel:
                index = int(sel[0])
                self.play_song(index)
        except Exception:
            pass
    
    def select_song(self, event):
        """Just select without playing"""
        # selection handled by Treeview selection event; keep for compatibility
        return
    
    def toggle_shuffle(self):
        """Toggle shuffle mode"""
        self.shuffle_mode = not self.shuffle_mode
        
        if self.shuffle_mode:
            self.shuffle_btn.config(bg=self.ACCENT_COLOR, fg=self.BG_PRIMARY)
        else:
            self.shuffle_btn.config(bg=self.BG_TERTIARY, fg=self.TEXT_PRIMARY)
    
    def toggle_repeat(self):
        """Toggle repeat mode"""
        self.repeat_mode = (self.repeat_mode + 1) % 3
        
        if self.repeat_mode == 0:
            self.repeat_btn.config(bg=self.BG_TERTIARY, text="🔁 REPEAT")
        elif self.repeat_mode == 1:
            self.repeat_btn.config(bg=self.ACCENT_COLOR, fg=self.BG_PRIMARY, text="🔁 ALL")
        else:
            self.repeat_btn.config(bg=self.ACCENT_COLOR, fg=self.BG_PRIMARY, text="🔁 ONE")
    
    def set_volume(self, value):
        """Set the volume"""
        volume = float(value) / 100
        pygame.mixer.music.set_volume(volume)
        self.volume_label_display.config(text=f"{int(float(value))}%")
    
    def on_progress_change(self, value):
        """Handle progress bar change"""
        if self.is_seeking:
            return
        
        if not pygame.mixer.music.get_busy() and not self.is_paused:
            return
        
        # Try to seek
        try:
            pos = float(value) / 100.0 * self.current_song_length
            if pos >= 0:
                pygame.mixer.music.set_pos(pos)
        except:
            pass
    
    def browse_folder(self):
        """Browse and select music folder"""
        folder = filedialog.askdirectory(title="Select Music Folder")
        if folder:
            self.music_folder = folder
            self.refresh_playlist()
    
    def refresh_playlist(self):
        """Refresh the playlist"""
        self.load_songs()
        
        if self.playlist:
            messagebox.showinfo("Success", f"Found {len(self.playlist)} song(s)!")
        else:
            messagebox.showwarning("No Songs", "No songs found in the folder!")
    
    def update_stats(self):
        """Update statistics display"""
        if self.playlist and self.current_index >= 0:
            current_song = os.path.splitext(os.path.basename(self.playlist[self.current_index]))[0]
            self.stats_label.config(
                text=f"Songs: {len(self.playlist)} | Currently: {current_song}"
            )
        else:
            self.stats_label.config(text=f"Songs: {len(self.playlist)} | Currently: No song")
    
    def format_time(self, seconds):
        """Format seconds to MM:SS"""
        try:
            minutes = int(seconds) // 60
            secs = int(seconds) % 60
            return f"{minutes:02d}:{secs:02d}"
        except:
            return "00:00"

    def get_duration(self, path):
        """Return duration in seconds for the given audio file."""
        try:
            if MUTAGEN_AVAILABLE and MutagenFile:
                f = MutagenFile(path)
                if f and hasattr(f, 'info') and hasattr(f.info, 'length'):
                    return int(f.info.length)
        except Exception:
            pass

        # Fallback: try pygame (works for some formats like WAV/OGG)
        try:
            snd = pygame.mixer.Sound(path)
            return int(snd.get_length())
        except Exception:
            return 0
    
    def start_update_thread(self):
        """Start thread for real-time updates"""
        def update_loop():
            while self.update_thread_active:
                try:
                    if self.is_playing and not self.is_paused:
                        # Update progress
                        if pygame.mixer.music.get_busy():
                            # Get current position
                            pos = pygame.mixer.music.get_pos() / 1000.0  # Convert to seconds
                            
                            if pos >= 0:
                                self.current_position = pos
                                self.time_label.config(text=self.format_time(pos))
                                
                                if self.current_song_length > 0:
                                    progress = (pos / self.current_song_length) * 100
                                    if 0 <= progress <= 100:
                                        self.progress_var.set(progress)
                        else:
                            # Song ended, play next
                            if self.repeat_mode == 2:  # Repeat one
                                self.play_song(self.current_index)
                            else:
                                self.next_song()
                    
                    self.root.after(100, lambda: None)
                except:
                    pass
        
        self.update_thread = threading.Thread(target=update_loop, daemon=True)
        self.update_thread.start()
    
    def on_closing(self):
        """Handle window closing"""
        self.update_thread_active = False
        pygame.mixer.music.stop()
        self.root.destroy()

# ============================================================================
# MAIN EXECUTION
# ============================================================================

if __name__ == "__main__":
    root = tk.Tk()
    
    # Set window icon and styling
    root.configure(bg="#121212")
    
    app = ModernMusicPlayer(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    
    # Start application
    root.mainloop()