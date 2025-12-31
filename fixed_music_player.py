import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import pygame
import os
import random
from pathlib import Path
import threading
import time

# ============================================================================
# MUSICFLOW - ULTIMATE SPOTIFY-LIKE MUSIC PLAYER (FIXED & WORKING)
# ============================================================================

class SpotifyMusicPlayer:
    def __init__(self, root):
        self.root = root
        self.root.title("🎵 MusicFlow Pro")
        self.root.geometry("1400x800")
        self.root.minsize(1200, 700)
        
        # ====================== COLORS (Spotify + StudentConnect) =======================
        self.BG_PRIMARY = "#121212"
        self.BG_SECONDARY = "#1DB954"
        self.BG_TERTIARY = "#191414"
        self.TEXT_PRIMARY = "#FFFFFF"
        self.TEXT_SECONDARY = "#B3B3B3"
        self.ACCENT_COLOR = "#1ED760"
        self.BUTTON_COLOR = "#1DB954"
        self.HOVER_COLOR = "#1aa34a"
        
        self.root.configure(bg=self.BG_PRIMARY)
        
        # ====================== PYGAME INIT =======================
        pygame.mixer.init()
        
        # ====================== STATE VARIABLES =======================
        self.playlist = []
        self.current_index = -1
        self.is_playing = False
        self.is_paused = False
        self.shuffle_mode = False
        self.repeat_mode = 0
        self.music_folder = "./songs"
        self.current_song_length = 0
        self.played_indices = []
        
        Path(self.music_folder).mkdir(exist_ok=True)
        
        # ====================== BUILD UI =======================
        self.build_ui()
        self.load_songs()
        
        # ====================== START UPDATE THREAD =======================
        self.update_active = True
        self.start_updates()
        
    def build_ui(self):
        """Build the complete user interface"""
        
        # ==================== TOP NAVIGATION ====================
        nav = tk.Frame(self.root, bg=self.BG_TERTIARY, height=70)
        nav.pack(fill=tk.X, side=tk.TOP)
        nav.pack_propagate(False)
        
        # Title
        title = tk.Label(
            nav,
            text="🎵 MusicFlow Pro",
            bg=self.BG_TERTIARY,
            fg=self.ACCENT_COLOR,
            font=("Arial", 18, "bold")
        )
        title.pack(side=tk.LEFT, padx=20, pady=15)
        
        # Status
        self.status = tk.Label(
            nav,
            text="Loading...",
            bg=self.BG_TERTIARY,
            fg=self.TEXT_SECONDARY,
            font=("Arial", 10)
        )
        self.status.pack(side=tk.LEFT, padx=10, pady=15)
        
        # Refresh button
        refresh_btn = tk.Button(
            nav,
            text="🔄 Refresh",
            bg=self.BUTTON_COLOR,
            fg=self.TEXT_PRIMARY,
            relief=tk.FLAT,
            cursor="hand2",
            padx=15,
            pady=8,
            command=self.refresh_playlist,
            font=("Arial", 10, "bold"),
            activebackground=self.HOVER_COLOR
        )
        refresh_btn.pack(side=tk.RIGHT, padx=20, pady=15)
        
        # ==================== MAIN CONTENT ====================
        content = tk.Frame(self.root, bg=self.BG_PRIMARY)
        content.pack(fill=tk.BOTH, expand=True, padx=0)
        
        # LEFT SIDEBAR - PLAYLIST
        left = tk.Frame(content, bg=self.BG_SECONDARY, width=350)
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=False)
        left.pack_propagate(False)
        
        playlist_title = tk.Label(
            left,
            text="📋 PLAYLIST",
            bg=self.BG_SECONDARY,
            fg=self.TEXT_PRIMARY,
            font=("Arial", 12, "bold")
        )
        playlist_title.pack(fill=tk.X, padx=15, pady=(15, 10))
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(left)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y, padx=(0, 5), pady=10)
        
        # Song listbox
        self.songlist = tk.Listbox(
            left,
            yscrollcommand=scrollbar.set,
            bg=self.BG_TERTIARY,
            fg=self.TEXT_PRIMARY,
            relief=tk.FLAT,
            borderwidth=0,
            activestyle="none",
            font=("Arial", 10),
            highlightthickness=0
        )
        self.songlist.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        scrollbar.config(command=self.songlist.yview)
        
        self.songlist.bind("<Double-Button-1>", self.on_song_double_click)
        
        # RIGHT SECTION - CONTROLS
        right = tk.Frame(content, bg=self.BG_PRIMARY)
        right.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # NOW PLAYING
        now_playing = tk.Frame(right, bg=self.BG_TERTIARY)
        now_playing.pack(fill=tk.X, pady=(0, 20))
        
        # Album art
        art = tk.Label(
            now_playing,
            text="🎧",
            bg=self.BG_TERTIARY,
            fg=self.ACCENT_COLOR,
            font=("Arial", 80)
        )
        art.pack(pady=20)
        
        # Song title
        self.song_title = tk.Label(
            now_playing,
            text="No song playing",
            bg=self.BG_TERTIARY,
            fg=self.TEXT_PRIMARY,
            font=("Arial", 20, "bold"),
            wraplength=400
        )
        self.song_title.pack(pady=(0, 10))
        
        # Song info
        self.song_info = tk.Label(
            now_playing,
            text="Add songs to get started",
            bg=self.BG_TERTIARY,
            fg=self.TEXT_SECONDARY,
            font=("Arial", 11),
            wraplength=400
        )
        self.song_info.pack(pady=(0, 30))
        
        # PROGRESS BAR
        progress_frame = tk.Frame(right, bg=self.BG_PRIMARY)
        progress_frame.pack(fill=tk.X, pady=(0, 15))
        
        self.time_label = tk.Label(
            progress_frame,
            text="00:00",
            bg=self.BG_PRIMARY,
            fg=self.TEXT_SECONDARY,
            font=("Arial", 9)
        )
        self.time_label.pack(side=tk.LEFT)
        
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Scale(
            progress_frame,
            from_=0,
            to=100,
            orient=tk.HORIZONTAL,
            variable=self.progress_var
        )
        self.progress_bar.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(10, 10))
        
        self.duration_label = tk.Label(
            progress_frame,
            text="00:00",
            bg=self.BG_PRIMARY,
            fg=self.TEXT_SECONDARY,
            font=("Arial", 9)
        )
        self.duration_label.pack(side=tk.RIGHT)
        
        # VOLUME
        vol_frame = tk.Frame(right, bg=self.BG_PRIMARY)
        vol_frame.pack(fill=tk.X, pady=(0, 20))
        
        vol_label = tk.Label(
            vol_frame,
            text="🔊 Volume:",
            bg=self.BG_PRIMARY,
            fg=self.TEXT_PRIMARY,
            font=("Arial", 10, "bold")
        )
        vol_label.pack(side=tk.LEFT, padx=(0, 10))
        
        self.volume_var = tk.DoubleVar(value=70)
        vol_slider = ttk.Scale(
            vol_frame,
            from_=0,
            to=100,
            orient=tk.HORIZONTAL,
            variable=self.volume_var,
            command=self.set_volume
        )
        vol_slider.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        
        self.vol_display = tk.Label(
            vol_frame,
            text="70%",
            bg=self.BG_PRIMARY,
            fg=self.ACCENT_COLOR,
            font=("Arial", 9),
            width=5
        )
        self.vol_display.pack(side=tk.LEFT)
        
        pygame.mixer.music.set_volume(0.7)
        
        # CONTROL BUTTONS
        btn_frame = tk.Frame(right, bg=self.BG_PRIMARY)
        btn_frame.pack(fill=tk.X, pady=(0, 20))
        
        btn_style = {
            "bg": self.BUTTON_COLOR,
            "fg": self.TEXT_PRIMARY,
            "relief": tk.FLAT,
            "cursor": "hand2",
            "activebackground": self.HOVER_COLOR,
            "padx": 20,
            "pady": 12,
            "font": ("Arial", 11, "bold")
        }
        
        tk.Button(btn_frame, text="⏮️ PREVIOUS", command=self.prev_song, **btn_style).pack(side=tk.LEFT, padx=5, fill=tk.BOTH, expand=True)
        self.play_btn = tk.Button(btn_frame, text="▶️ PLAY", command=self.play_pause, **btn_style)
        self.play_btn.pack(side=tk.LEFT, padx=5, fill=tk.BOTH, expand=True)
        tk.Button(btn_frame, text="NEXT ⏭️", command=self.next_song, **btn_style).pack(side=tk.LEFT, padx=5, fill=tk.BOTH, expand=True)
        
        # FEATURE BUTTONS
        feat_frame = tk.Frame(right, bg=self.BG_PRIMARY)
        feat_frame.pack(fill=tk.X, pady=(0, 20))
        
        feat_style = {
            "bg": self.BG_TERTIARY,
            "fg": self.TEXT_PRIMARY,
            "relief": tk.FLAT,
            "cursor": "hand2",
            "padx": 15,
            "pady": 10,
            "font": ("Arial", 10, "bold"),
            "activebackground": self.BUTTON_COLOR
        }
        
        self.shuffle_btn = tk.Button(feat_frame, text="🔀 SHUFFLE", command=self.toggle_shuffle, **feat_style)
        self.shuffle_btn.pack(side=tk.LEFT, padx=5, fill=tk.BOTH, expand=True)
        
        self.repeat_btn = tk.Button(feat_frame, text="🔁 REPEAT", command=self.toggle_repeat, **feat_style)
        self.repeat_btn.pack(side=tk.LEFT, padx=5, fill=tk.BOTH, expand=True)
        
        tk.Button(feat_frame, text="📂 BROWSE", command=self.browse_folder, **feat_style).pack(side=tk.LEFT, padx=5, fill=tk.BOTH, expand=True)
        
        # STATS
        self.stats = tk.Label(
            right,
            text="Songs: 0",
            bg=self.BG_TERTIARY,
            fg=self.TEXT_SECONDARY,
            font=("Arial", 9),
            justify=tk.LEFT
        )
        self.stats.pack(fill=tk.X, padx=15, pady=10)
        
    def load_songs(self):
        """Load songs from folder"""
        supported = ('.mp3', '.wav', '.flac', '.ogg', '.m4a')
        self.playlist = []
        
        try:
            if os.path.exists(self.music_folder):
                for file in os.listdir(self.music_folder):
                    if file.lower().endswith(supported):
                        self.playlist.append(os.path.join(self.music_folder, file))
            
            self.playlist.sort()
            self.update_songlist()
            
            if self.playlist:
                self.status.config(text=f"✅ Loaded {len(self.playlist)} songs")
            else:
                self.status.config(text="❌ No songs found")
        except Exception as e:
            self.status.config(text=f"❌ Error: {str(e)}")
    
    def update_songlist(self):
        """Update the song listbox"""
        self.songlist.delete(0, tk.END)
        
        for idx, path in enumerate(self.playlist):
            name = os.path.splitext(os.path.basename(path))[0]
            if idx == self.current_index:
                self.songlist.insert(tk.END, f"▶️  {name}")
                self.songlist.itemconfig(idx, {'fg': self.ACCENT_COLOR})
            else:
                self.songlist.insert(tk.END, f"   {name}")
        
        if self.current_index >= 0:
            self.songlist.see(self.current_index)
        
        self.stats.config(text=f"Songs: {len(self.playlist)} | Now: {self.current_index + 1 if self.current_index >= 0 else 'None'}/{len(self.playlist)}")
    
    def play_pause(self):
        """Play or pause"""
        if not self.playlist:
            messagebox.showwarning("No Songs", "Add songs first!")
            return
        
        if self.is_paused:
            pygame.mixer.music.unpause()
            self.is_paused = False
            self.is_playing = True
            self.play_btn.config(text="⏸️ PAUSE")
        elif self.is_playing:
            pygame.mixer.music.pause()
            self.is_paused = True
            self.play_btn.config(text="▶️ PLAY")
        else:
            if self.current_index < 0:
                self.current_index = random.randint(0, len(self.playlist) - 1) if self.shuffle_mode else 0
            self.play_song(self.current_index)
    
    def play_song(self, index):
        """Play specific song"""
        if index < 0 or index >= len(self.playlist):
            return
        
        self.current_index = index
        
        try:
            path = self.playlist[index]
            pygame.mixer.music.load(path)
            pygame.mixer.music.play()
            
            self.is_playing = True
            self.is_paused = False
            self.play_btn.config(text="⏸️ PAUSE")
            
            name = os.path.splitext(os.path.basename(path))[0]
            self.song_title.config(text=name)
            self.song_info.config(text=f"Track {index + 1} of {len(self.playlist)}")
            
            self.update_songlist()
            
            if index not in self.played_indices:
                self.played_indices.append(index)
        except Exception as e:
            messagebox.showerror("Error", f"Could not play: {str(e)}")
    
    def next_song(self):
        """Play next song"""
        if not self.playlist:
            return
        
        if self.shuffle_mode:
            while True:
                idx = random.randint(0, len(self.playlist) - 1)
                if idx not in self.played_indices or len(self.played_indices) >= len(self.playlist):
                    if len(self.played_indices) >= len(self.playlist):
                        self.played_indices = []
                    self.play_song(idx)
                    break
        else:
            self.play_song((self.current_index + 1) % len(self.playlist))
    
    def prev_song(self):
        """Play previous song"""
        if not self.playlist:
            return
        self.play_song((self.current_index - 1) % len(self.playlist))
    
    def on_song_double_click(self, event):
        """Double-click to play"""
        sel = self.songlist.curselection()
        if sel:
            self.play_song(sel[0])
    
    def toggle_shuffle(self):
        """Toggle shuffle"""
        self.shuffle_mode = not self.shuffle_mode
        if self.shuffle_mode:
            self.shuffle_btn.config(bg=self.ACCENT_COLOR, fg=self.BG_PRIMARY)
        else:
            self.shuffle_btn.config(bg=self.BG_TERTIARY, fg=self.TEXT_PRIMARY)
    
    def toggle_repeat(self):
        """Toggle repeat"""
        self.repeat_mode = (self.repeat_mode + 1) % 3
        if self.repeat_mode == 0:
            self.repeat_btn.config(bg=self.BG_TERTIARY, fg=self.TEXT_PRIMARY, text="🔁 REPEAT")
        elif self.repeat_mode == 1:
            self.repeat_btn.config(bg=self.ACCENT_COLOR, fg=self.BG_PRIMARY, text="🔁 ALL")
        else:
            self.repeat_btn.config(bg=self.ACCENT_COLOR, fg=self.BG_PRIMARY, text="🔁 ONE")
    
    def set_volume(self, val):
        """Set volume"""
        vol = float(val) / 100
        pygame.mixer.music.set_volume(vol)
        self.vol_display.config(text=f"{int(float(val))}%")
    
    def browse_folder(self):
        """Browse folder"""
        folder = filedialog.askdirectory(title="Select Music Folder")
        if folder:
            self.music_folder = folder
            self.refresh_playlist()
    
    def refresh_playlist(self):
        """Refresh songs"""
        self.load_songs()
        if self.playlist:
            messagebox.showinfo("Success", f"Found {len(self.playlist)} songs!")
        else:
            messagebox.showwarning("Empty", "No songs found!")
    
    def format_time(self, seconds):
        """Format MM:SS"""
        try:
            m = int(seconds) // 60
            s = int(seconds) % 60
            return f"{m:02d}:{s:02d}"
        except:
            return "00:00"
    
    def start_updates(self):
        """Update thread"""
        def update_loop():
            while self.update_active:
                try:
                    if self.is_playing and not self.is_paused and pygame.mixer.music.get_busy():
                        pos = pygame.mixer.music.get_pos() / 1000.0
                        if pos >= 0:
                            self.time_label.config(text=self.format_time(pos))
                            if self.current_song_length > 0:
                                progress = (pos / self.current_song_length) * 100
                                self.progress_var.set(min(100, progress))
                    elif self.is_playing and not pygame.mixer.music.get_busy() and not self.is_paused:
                        if self.repeat_mode == 2:
                            self.play_song(self.current_index)
                        else:
                            self.next_song()
                    
                    time.sleep(0.1)
                except:
                    pass
        
        self.thread = threading.Thread(target=update_loop, daemon=True)
        self.thread.start()
    
    def on_close(self):
        """Close app"""
        self.update_active = False
        pygame.mixer.music.stop()
        self.root.destroy()

# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    root = tk.Tk()
    app = SpotifyMusicPlayer(root)
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.mainloop()
