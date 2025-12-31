import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import tkinter.font as tkfont
import pygame
import traceback
import math
import os
import random
import shutil
from pathlib import Path
import threading
from datetime import timedelta
import json
from PIL import Image, ImageDraw, ImageFont, ImageTk, ImageFilter
from io import BytesIO
try:
    from mutagen._file import File as MutagenFile
    from mutagen.id3._util import ID3NoHeaderError
    MUTAGEN_AVAILABLE = True
except ImportError:
    MutagenFile = None
    MUTAGEN_AVAILABLE = False

# ============================================================================
# MUSICFLOW - TRUE SPOTIFY CLONE (2025 RADICAL REDESIGN)
# Completely different layout: Collapsible sidebar, grid playlist, full-width player
# ============================================================================

class SpotifyClonePlayer:
    def __init__(self, root):
        self.root = root
        self.root.title("🎵 MusicFlow - Spotify Clone")
        self.root.geometry("1400x850")
        self.root.minsize(1100, 700)
        
        # ====================== SPOTIFY 2025 COLOR PALETTE =======================
        self.BG_BLACK = "#000000"
        self.BG_DARK = "#0F0F0F"
        self.BG_CARD = "#181818"
        self.BG_HOVER = "#2A2A2A"
        self.BG_SELECTED = "#1ED760"
        self.TEXT_WHITE = "#FFFFFF"
        self.TEXT_GRAY = "#B3B3B3"
        self.TEXT_LIGHT = "#E5E5E5"
        self.GREEN_ACCENT = "#1ED760"
        self.GREEN_DARK = "#1AA34A"
        
        self.root.configure(bg=self.BG_BLACK)
        # Configure default font via tkinter.font to avoid splitting family names
        try:
            default_font = tkfont.nametofont("TkDefaultFont")
            default_font.configure(family="Segoe UI", size=10)
        except Exception:
            # fallback to option_add if nametofont not available
            try:
                self.root.option_add("*Font", "Segoe UI 10")
            except Exception:
                pass
        
        # ====================== PYGAME INIT =======================
        pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)
        
        # ====================== STATE VARS =======================
        self.playlist = []
        self.current_index = -1
        self.is_playing = False
        self.is_paused = False
        self.shuffle_mode = False
        self.repeat_mode = 0
        self.music_folder = "./songs"
        self.current_song_length = 0
        self.current_position = 0
        self.played_indices = []
        self.filtered_playlist = []
        self.song_metadata = {}
        self.card_widgets = {}
        self.current_art_photo = None
        self.small_art_photo = None
        self.sidebar_visible = True  # For collapsible sidebar
        self.COMPACT_THRESHOLD = 60
        self.compact_tree = None
        
        Path(self.music_folder).mkdir(exist_ok=True)
        
        # ====================== UI SETUP =======================
        self.setup_ui()
        self.load_songs()
        self.start_update_thread()
        self.root.after(100, self.check_music_end)
        
    def get_duration(self, path):
        if MUTAGEN_AVAILABLE and MutagenFile is not None:
            try:
                if callable(MutagenFile):
                    audio = MutagenFile(path)
                    if audio is not None and hasattr(audio, 'info') and audio.info is not None:
                        return audio.info.length
            except:
                pass
        try:
            sound = pygame.mixer.Sound(path)
            return int(sound.get_length())
        except:
            pass
        return 0
    
    def get_metadata(self, path):
        if path in self.song_metadata:
            return self.song_metadata[path]
        
        duration = self.get_duration(path)
        title = os.path.splitext(os.path.basename(path))[0]
        artist = "Unknown Artist"
        
        if MUTAGEN_AVAILABLE and MutagenFile is not None and callable(MutagenFile):
            try:
                audio = MutagenFile(path)
                if audio is not None and audio.tags:
                    if 'TIT2' in audio.tags:
                        title = str(audio.tags['TIT2'])
                    if 'TPE1' in audio.tags:
                        artist = str(audio.tags['TPE1'])
            except:
                pass
        
        meta = {'duration': duration, 'title': title, 'artist': artist}
        self.song_metadata[path] = meta
        return meta
    
    def get_album_art(self, path):
        if not MUTAGEN_AVAILABLE or MutagenFile is None:
            return None
        try:
            audio = MutagenFile(path)
            if audio is None or 'APIC:' not in audio.tags:
                return None
            artwork = audio.tags['APIC:'].data
            img = Image.open(BytesIO(artwork))
            img.thumbnail((400, 400), Image.Resampling.LANCZOS)
            # Circular with shadow
            size = 400
            mask = Image.new('L', (size, size), 0)
            draw = ImageDraw.Draw(mask)
            draw.ellipse((0, 0, size, size), fill=255)
            img = img.convert('RGBA')
            output = Image.composite(img, Image.new('RGBA', img.size, (0, 0, 0, 0)), mask)
            # Add shadow
            shadow = Image.new('RGBA', (size + 20, size + 20), (0, 0, 0, 0))
            shadow_draw = ImageDraw.Draw(shadow)
            shadow_draw.ellipse((10, 10, size + 10, size + 10), fill=(0, 0, 0, 80))
            shadow = shadow.filter(ImageFilter.GaussianBlur(5))
            return output, shadow
        except:
            return None, None
    
    def load_songs(self):
        supported_formats = ('.mp3', '.wav', '.flac', '.ogg', '.m4a', '.aac')
        self.playlist = []
        
        try:
            if os.path.exists(self.music_folder):
                for file in os.listdir(self.music_folder):
                    if file.lower().endswith(supported_formats):
                        full_path = os.path.join(self.music_folder, file)
                        self.playlist.append(full_path)
            
            self.playlist.sort()
            self.filtered_playlist = self.playlist.copy()
            # Initialize metadata placeholders quickly to keep UI responsive
            self.song_metadata = {}
            for p in self.playlist:
                title = os.path.splitext(os.path.basename(p))[0]
                self.song_metadata[p] = {'duration': 0, 'title': title, 'artist': 'Unknown Artist'}

            # Build the UI first
            self.update_playlist_grid()

            # Then start background thread to populate metadata (duration, tags)
            threading.Thread(target=self._populate_metadata_background, daemon=True).start()
            # Start background thread to lazily load album art
            threading.Thread(target=self._populate_art_background, daemon=True).start()
            if self.playlist:
                self.status_label.config(text=f"Loaded {len(self.playlist)} tracks")
            else:
                self.status_label.config(text="No tracks found")
        except Exception as e:
            self.status_label.config(text=f"Error: {str(e)}")
    
    def setup_ui(self):
        # ==================== TOP BAR (SLIM) ====================
        top_bar = tk.Frame(self.root, bg=self.BG_DARK, height=50)
        top_bar.pack(fill=tk.X)
        top_bar.pack_propagate(False)
        
        title_label = tk.Label(top_bar, text="MusicFlow", font=("Segoe UI", 16, "bold"), fg=self.GREEN_ACCENT, bg=self.BG_DARK)
        title_label.pack(side=tk.LEFT, padx=20, pady=10)
        
        self.status_label = tk.Label(top_bar, text="Ready", font=("Segoe UI", 10), fg=self.TEXT_GRAY, bg=self.BG_DARK)
        self.status_label.pack(side=tk.LEFT, padx=10, pady=10)
        
        # Sidebar toggle
        sidebar_toggle = tk.Button(top_bar, text="☰", font=("Segoe UI", 16), bg=self.BG_DARK, fg=self.TEXT_GRAY, 
                                   relief=tk.FLAT, command=self.toggle_sidebar, activebackground=self.BG_HOVER)
        sidebar_toggle.pack(side=tk.RIGHT, padx=10, pady=10)
        
        # ==================== MAIN FRAME ====================
        main_frame = tk.Frame(self.root, bg=self.BG_BLACK)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # ==================== COLLAPSIBLE SIDEBAR ====================
        self.sidebar = tk.Frame(main_frame, bg=self.BG_DARK, width=250)
        self.sidebar.pack(side=tk.LEFT, fill=tk.Y)
        self.sidebar.pack_propagate(False)
        
        # Sidebar content
        nav_items = [
            ("🏠 Home", self.switch_to_home),
            ("🔍 Search", self.switch_to_search),
            ("📂 Library", self.switch_to_library),
            ("❤️ Liked", self.switch_to_liked)
        ]
        
        for text, cmd in nav_items:
            btn = tk.Button(self.sidebar, text=text, bg=self.BG_DARK, fg=self.TEXT_GRAY, 
                            activebackground=self.BG_HOVER, activeforeground=self.GREEN_ACCENT,
                            relief=tk.FLAT, anchor="w", font=("Segoe UI", 12), padx=20, pady=15, bd=0, command=cmd)
            btn.pack(fill=tk.X, padx=10)
        
        # Playlist section in sidebar
        sep = tk.Frame(self.sidebar, bg=self.BG_CARD, height=1)
        sep.pack(fill=tk.X, pady=10)
        
        playlist_label = tk.Label(self.sidebar, text="Your Library", font=("Segoe UI", 14, "bold"), fg=self.TEXT_WHITE, bg=self.BG_DARK)
        playlist_label.pack(pady=(10, 5), padx=10, anchor="w")
        
        # Search in sidebar
        search_frame = tk.Frame(self.sidebar, bg=self.BG_DARK)
        search_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        self.search_var = tk.StringVar()
        self.search_var.trace_add('write', lambda *_: self.filter_songs())
        search_entry = tk.Entry(search_frame, textvariable=self.search_var, font=("Segoe UI", 11), relief=tk.FLAT,
                                bg=self.BG_CARD, fg=self.TEXT_WHITE, insertbackground=self.TEXT_WHITE, bd=0)
        search_entry.pack(fill=tk.X, ipady=5)
        
        # ==================== MAIN CONTENT (Full Width) ====================
        self.main_content = tk.Frame(main_frame, bg=self.BG_BLACK)
        self.main_content.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Now Playing Header (Full Width)
        self.now_playing_header = tk.Frame(self.main_content, bg=self.BG_CARD, height=80)
        self.now_playing_header.pack(fill=tk.X, pady=(20, 0))
        self.now_playing_header.pack_propagate(False)
        
        # Big Art in header
        self.header_art = tk.Label(self.now_playing_header, text="🎵 Select a track", font=("Arial", 50), fg=self.GREEN_ACCENT, bg=self.BG_CARD)
        self.header_art.pack(side=tk.LEFT, padx=20, pady=15)
        
        # Title/Artist in header
        header_text = tk.Frame(self.now_playing_header, bg=self.BG_CARD)
        header_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 20), pady=15)
        
        self.header_title = tk.Label(header_text, text="Nothing playing", font=("Segoe UI", 20, "bold"), fg=self.TEXT_WHITE, bg=self.BG_CARD, anchor="w")
        self.header_title.pack(anchor="w")
        
        self.header_artist = tk.Label(header_text, text="—", font=("Segoe UI", 14), fg=self.TEXT_GRAY, bg=self.BG_CARD, anchor="w")
        self.header_artist.pack(anchor="w")
        
        # ==================== PLAYLIST GRID (Different from Treeview) ====================
        grid_frame = tk.Frame(self.main_content, bg=self.BG_BLACK)
        grid_frame.pack(fill=tk.BOTH, expand=True, pady=20)
        
        # Canvas for scrollable grid
        self.canvas = tk.Canvas(grid_frame, bg=self.BG_BLACK, highlightthickness=0)
        scrollbar = ttk.Scrollbar(grid_frame, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = tk.Frame(self.canvas, bg=self.BG_BLACK)
        
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=scrollbar.set)
        
        self.canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Bind mousewheel
        self.canvas.bind_all("<MouseWheel>", lambda e: self.canvas.yview_scroll(int(-1*(e.delta/120)), "units"))
        
        # ==================== BOTTOM PLAYER BAR (Ultra Slim) ====================
        bottom_player = tk.Frame(self.root, bg=self.BG_CARD, height=70)
        bottom_player.pack(side=tk.BOTTOM, fill=tk.X)
        bottom_player.pack_propagate(False)
        
        # Left: Mini Art + Info
        left_player = tk.Frame(bottom_player, bg=self.BG_CARD)
        left_player.pack(side=tk.LEFT, fill=tk.BOTH, expand=False, padx=(10, 0))
        
        self.mini_art = tk.Label(left_player, text="♪", font=("Arial", 30), fg=self.GREEN_ACCENT, bg=self.BG_CARD)
        self.mini_art.pack(side=tk.LEFT, pady=10, padx=(5, 10))
        
        player_info = tk.Frame(left_player, bg=self.BG_CARD)
        player_info.pack(side=tk.LEFT, fill=tk.BOTH, pady=10)
        
        self.player_title = tk.Label(player_info, text="No track", font=("Segoe UI", 13, "bold"), fg=self.TEXT_WHITE, bg=self.BG_CARD, anchor="w")
        self.player_title.pack(anchor="w")
        
        self.player_artist = tk.Label(player_info, text="—", font=("Segoe UI", 11), fg=self.TEXT_GRAY, bg=self.BG_CARD, anchor="w")
        self.player_artist.pack(anchor="w")
        
        # Center: Controls + Progress
        center_player = tk.Frame(bottom_player, bg=self.BG_CARD)
        center_player.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Progress
        prog_frame = tk.Frame(center_player, bg=self.BG_CARD)
        prog_frame.pack(fill=tk.X, pady=(5, 0))
        
        self.prog_time = tk.Label(prog_frame, text="0:00", font=("Segoe UI", 9), fg=self.TEXT_GRAY, bg=self.BG_CARD)
        self.prog_time.pack(side=tk.LEFT, padx=15)
        
        self.progress_var = tk.DoubleVar()
        self.progress = ttk.Scale(prog_frame, from_=0, to=100, orient=tk.HORIZONTAL, variable=self.progress_var,
                                  command=self.seek_progress)
        self.progress.pack(fill=tk.X, expand=True, padx=(10, 0))
        style = ttk.Style()
        # Use orientation-specific style name so ttk can find proper layout
        style_name = "Custom.Horizontal.TScale"
        style.configure(style_name, troughcolor=self.BG_HOVER, background=self.BG_CARD)
        style.map(style_name, background=[('active', self.GREEN_ACCENT)])
        self.progress.configure(style=style_name)
        
        self.prog_duration = tk.Label(prog_frame, text="—:—", font=("Segoe UI", 9), fg=self.TEXT_GRAY, bg=self.BG_CARD)
        self.prog_duration.pack(side=tk.RIGHT, padx=15)
        
        # Buttons
        btn_frame = tk.Frame(center_player, bg=self.BG_CARD)
        btn_frame.pack(pady=5)
        
        self.prev_small = tk.Button(btn_frame, text="⏮", font=("Segoe UI", 12), bg=self.BG_CARD, fg=self.TEXT_GRAY,
                                    relief=tk.FLAT, command=self.prev_song, activebackground=self.BG_HOVER, bd=0, padx=15)
        self.prev_small.pack(side=tk.LEFT, padx=20)
        
        self.play_small = tk.Button(btn_frame, text="▶", font=("Segoe UI", 16, "bold"), bg=self.BG_CARD, fg=self.TEXT_WHITE,
                                    relief=tk.FLAT, command=self.play_pause, activebackground=self.BG_HOVER, bd=0, padx=20)
        self.play_small.pack(side=tk.LEFT, padx=(0, 20))
        
        self.next_small = tk.Button(btn_frame, text="⏭", font=("Segoe UI", 12), bg=self.BG_CARD, fg=self.TEXT_GRAY,
                                    relief=tk.FLAT, command=self.next_song, activebackground=self.BG_HOVER, bd=0, padx=15)
        self.next_small.pack(side=tk.LEFT)
        
        # Right: Volume + Icons
        right_player = tk.Frame(bottom_player, bg=self.BG_CARD, width=200)
        right_player.pack(side=tk.RIGHT, fill=tk.Y, padx=10)
        
        vol_frame = tk.Frame(right_player, bg=self.BG_CARD)
        vol_frame.pack(side=tk.RIGHT, fill=tk.X, pady=15)
        
        self.volume_var = tk.DoubleVar(value=70)
        vol_scale = ttk.Scale(vol_frame, from_=0, to=100, orient=tk.HORIZONTAL, variable=self.volume_var,
                              command=self.update_volume, length=80)
        vol_scale.pack(side=tk.LEFT, fill=tk.X, expand=True)
        vol_scale.configure(style=style_name)
        
        vol_icon = tk.Label(vol_frame, text="🔊", font=("Segoe UI", 12), fg=self.TEXT_GRAY, bg=self.BG_CARD)
        vol_icon.pack(side=tk.RIGHT, padx=(5, 0))
        
        # Icons row
        icons_frame = tk.Frame(right_player, bg=self.BG_CARD)
        icons_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=(0, 10))
        
        self.shuffle_icon = tk.Button(icons_frame, text="🔀", font=("Segoe UI", 10), bg=self.BG_CARD, fg=self.TEXT_GRAY,
                                      relief=tk.FLAT, command=self.toggle_shuffle, activebackground=self.BG_HOVER, bd=0, padx=10)
        self.shuffle_icon.pack(side=tk.LEFT)
        
        self.repeat_icon = tk.Button(icons_frame, text="🔁", font=("Segoe UI", 10), bg=self.BG_CARD, fg=self.TEXT_GRAY,
                                     relief=tk.FLAT, command=self.toggle_repeat, activebackground=self.BG_HOVER, bd=0, padx=10)
        self.repeat_icon.pack(side=tk.LEFT)
        
        queue_btn = tk.Button(icons_frame, text="⏸", font=("Segoe UI", 10), bg=self.BG_CARD, fg=self.TEXT_GRAY,
                              relief=tk.FLAT, command=lambda: messagebox.showinfo("Queue", "Queue coming soon!"), 
                              activebackground=self.BG_HOVER, bd=0, padx=10)
        queue_btn.pack(side=tk.LEFT)
        
        devices_btn = tk.Button(icons_frame, text="📱", font=("Segoe UI", 10), bg=self.BG_CARD, fg=self.TEXT_GRAY,
                                relief=tk.FLAT, command=lambda: messagebox.showinfo("Devices", "Devices coming soon!"), 
                                activebackground=self.BG_HOVER, bd=0, padx=10)
        devices_btn.pack(side=tk.LEFT)
        
        pygame.mixer.music.set_volume(0.7)
    
    def toggle_sidebar(self):
        self.sidebar_visible = not self.sidebar_visible
        if self.sidebar_visible:
            self.sidebar.pack(side=tk.LEFT, fill=tk.Y, before=self.main_content)
        else:
            self.sidebar.pack_forget()
    
    def switch_to_home(self):
        self.update_main_content("Home - Featured Playlists")
    
    def switch_to_search(self):
        self.update_main_content("Search - Discover Music")
    
    def switch_to_library(self):
        self.update_playlist_grid()
        self.update_main_content("Library - Your Tracks")
    
    def switch_to_liked(self):
        self.update_main_content("Liked Songs")
    
    def update_main_content(self, title):
        # Clear and add placeholder
        for widget in self.main_content.winfo_children():
            if widget != self.now_playing_header:
                widget.destroy()
        content_label = tk.Label(self.main_content, text=title, font=("Segoe UI", 24, "bold"), fg=self.TEXT_WHITE, bg=self.BG_BLACK)
        content_label.pack(pady=20, padx=20, anchor="w")

        # Home view: animated carousel + featured
        if "Home" in title:
            self.create_home_carousel()
            self.start_header_pulse()

        # Add grid if library
        if "Library" in title:
            self.update_playlist_grid()

    def create_playlist_grid(self):
        """Create the scrollable playlist grid widgets if missing or destroyed."""
        # If canvas/scrollable_frame do not exist or were destroyed, recreate them
        if not hasattr(self, 'canvas') or not getattr(self, 'canvas') or not self.canvas.winfo_exists():
            grid_frame = tk.Frame(self.main_content, bg=self.BG_BLACK)
            grid_frame.pack(fill=tk.BOTH, expand=True, pady=20)

            # Canvas for scrollable grid
            self.canvas = tk.Canvas(grid_frame, bg=self.BG_BLACK, highlightthickness=0)
            scrollbar = ttk.Scrollbar(grid_frame, orient="vertical", command=self.canvas.yview)
            self.scrollable_frame = tk.Frame(self.canvas, bg=self.BG_BLACK)

            self.scrollable_frame.bind(
                "<Configure>",
                lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
            )

            self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
            self.canvas.configure(yscrollcommand=scrollbar.set)

            self.canvas.pack(side="left", fill="both", expand=True)
            scrollbar.pack(side="right", fill="y")

            # Bind mousewheel
            self.canvas.bind_all("<MouseWheel>", lambda e: self.canvas.yview_scroll(int(-1*(e.delta/120)), "units"))

    
    def update_playlist_grid(self):
        # Ensure grid exists (recreate if user switched views and it was destroyed)
        self.create_playlist_grid()

        # Clear grid and card registry
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
        self.card_widgets = {}
        
        display_list = self.filtered_playlist if self.filtered_playlist else self.playlist
        # if library large, switch to compact view
        if len(display_list) > self.COMPACT_THRESHOLD:
            self._show_compact_list(display_list)
            return
        cols = 4
        row = 0
        col = 0
        
        for idx, path in enumerate(display_list):
            real_idx = self.playlist.index(path) if path in self.playlist else idx
            meta = self.song_metadata.get(path, {'title': os.path.splitext(os.path.basename(path))[0], 'artist': 'Unknown Artist', 'duration': 0})
            title = meta.get('title', os.path.splitext(os.path.basename(path))[0])
            artist = meta.get('artist', 'Unknown Artist')
            duration = self.format_time(meta.get('duration', 0))
            
            # Card frame
            card = tk.Frame(self.scrollable_frame, bg=self.BG_CARD, relief=tk.RIDGE, bd=0)
            card.grid(row=row, column=col, padx=10, pady=10, sticky="nsew")
            
            # Art placeholder
            art_label = tk.Label(card, text="🎼", font=("Arial", 40), fg=self.GREEN_ACCENT, bg=self.BG_CARD)
            art_label.pack(pady=10)
            
            # Title
            t_label = tk.Label(card, text=title[:25] + "..." if len(title) > 25 else title, font=("Segoe UI", 11, "bold"), 
                               fg=self.TEXT_WHITE, bg=self.BG_CARD, wraplength=120)
            t_label.pack(pady=(0, 5))
            
            # Artist + Duration
            info_frame = tk.Frame(card, bg=self.BG_CARD)
            info_frame.pack()
            a_label = tk.Label(info_frame, text=artist[:20] + "..." if len(artist) > 20 else artist, font=("Segoe UI", 9), 
                               fg=self.TEXT_GRAY, bg=self.BG_CARD)
            a_label.pack(anchor="w")
            d_label = tk.Label(info_frame, text=duration, font=("Segoe UI", 9), fg=self.TEXT_GRAY, bg=self.BG_CARD)
            d_label.pack(anchor="w")
            # store widget refs for fast updates from background thread
            self.card_widgets[path] = {
                'card': card,
                't_label': t_label,
                'a_label': a_label,
                'd_label': d_label,
                'art_label': art_label,
                'art_loaded': False
            }
            
            # Hover effect
            def on_enter(e, c=card, idx=real_idx):
                c.configure(bg=self.BG_HOVER)
            def on_leave(e, c=card):
                c.configure(bg=self.BG_CARD if idx != self.current_index else self.BG_SELECTED)
            def play_this(idx=real_idx):
                self.play_song(idx)
            
            card.bind("<Enter>", on_enter)
            card.bind("<Leave>", on_leave)
            card.bind("<Button-1>", lambda e: play_this())
            
            if real_idx == self.current_index:
                card.configure(bg=self.BG_SELECTED)
            
            col += 1
            if col >= cols:
                col = 0
                row += 1
        
        # Configure grid weights
        for i in range(cols):
            self.scrollable_frame.grid_columnconfigure(i, weight=1)
    
    def filter_songs(self):
        query = self.search_var.get().lower()
        if not query:
            self.filtered_playlist = []
        else:
            # Use cached metadata where possible to avoid blocking
            self.filtered_playlist = [p for p in self.playlist if query in (self.song_metadata.get(p, {}).get('title','').lower() or '') or query in (self.song_metadata.get(p, {}).get('artist','').lower() or '')]
        self.update_playlist_grid()
        self.status_label.config(text=f"Found {len(self.filtered_playlist)} tracks")

    def _populate_metadata_background(self):
        """Background worker to populate metadata for each song and update UI via main thread."""
        for p in list(self.playlist):
            try:
                meta = self.get_metadata(p)
                # Store metadata
                self.song_metadata[p] = meta

                # Schedule UI update for this card
                self.root.after(0, lambda path=p: self._update_card_from_metadata(path))
            except Exception:
                continue

    def _update_card_from_metadata(self, path):
        """Update a single card's labels with metadata (runs on main thread)."""
        refs = self.card_widgets.get(path)
        meta = self.song_metadata.get(path)
        if not refs or not meta:
            return

        title = meta.get('title', os.path.splitext(os.path.basename(path))[0])
        artist = meta.get('artist', 'Unknown Artist')
        dur = self.format_time(meta.get('duration', 0))

        try:
            refs['t_label'].config(text=title[:25] + "..." if len(title) > 25 else title)
            refs['a_label'].config(text=artist[:20] + "..." if len(artist) > 20 else artist)
            refs['d_label'].config(text=dur)
        except Exception:
            pass

    def _show_compact_list(self, display_list):
        """Switch to a compact Treeview list for large libraries."""
        # Clear main content except now_playing_header
        for widget in self.main_content.winfo_children():
            if widget != self.now_playing_header:
                widget.destroy()

        tree_frame = tk.Frame(self.main_content, bg=self.BG_BLACK)
        tree_frame.pack(fill=tk.BOTH, expand=True, pady=20)

        cols = ("Title", "Artist", "Duration")
        if self.compact_tree and self.compact_tree.winfo_exists():
            self.compact_tree.destroy()

        self.compact_tree = ttk.Treeview(tree_frame, columns=cols, show='headings')
        for c in cols:
            self.compact_tree.heading(c, text=c)
            if c == 'Title':
                self.compact_tree.column(c, width=400, anchor='w')
            else:
                self.compact_tree.column(c, width=120, anchor='center')

        vsb = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.compact_tree.yview)
        self.compact_tree.configure(yscrollcommand=vsb.set)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        self.compact_tree.pack(fill=tk.BOTH, expand=True)

        # populate
        for idx, path in enumerate(display_list):
            real_idx = self.playlist.index(path) if path in self.playlist else idx
            meta = self.song_metadata.get(path, {})
            title = meta.get('title', os.path.splitext(os.path.basename(path))[0])
            artist = meta.get('artist', 'Unknown')
            dur = self.format_time(meta.get('duration', 0))
            try:
                self.compact_tree.insert('', tk.END, iid=str(real_idx), values=(title, artist, dur))
            except Exception:
                pass

        self.compact_tree.bind('<Double-1>', lambda e: self._compact_double_click())

    def _compact_double_click(self):
        if not self.compact_tree or not self.compact_tree.winfo_exists():
            return
        sel = self.compact_tree.selection()
        if sel:
            try:
                idx = int(sel[0])
                self.play_song(idx)
            except Exception:
                pass

    def _populate_art_background(self):
        """Load album art lazily for card widgets in background."""
        for path in list(self.card_widgets.keys()):
            refs = self.card_widgets.get(path)
            if not refs or refs.get('art_loaded'):
                continue
            try:
                art_res = self.get_album_art(path)
                if not art_res:
                    continue
                art, shadow = art_res
                if art is None:
                    continue
                thumb = art.resize((80, 80), Image.Resampling.LANCZOS)

                def _upd(p=path, t=thumb):
                    refs = self.card_widgets.get(p)
                    if not refs:
                        return
                    try:
                        photo = ImageTk.PhotoImage(t)
                        refs['art_label'].config(image=photo, text='')
                        refs['art_label'].image = photo
                        refs['art_loaded'] = True
                    except Exception:
                        pass

                self.root.after(0, _upd)
            except Exception:
                continue

    # ------------------ HOME ANIMATIONS ------------------
    def create_home_carousel(self):
        # Remove existing carousel if present
        if hasattr(self, 'home_carousel_frame') and self.home_carousel_frame.winfo_exists():
            self.home_carousel_frame.destroy()

        self.home_carousel_frame = tk.Frame(self.main_content, bg=self.BG_BLACK)
        self.home_carousel_frame.pack(fill=tk.X, padx=20, pady=(0, 20))

        self.carousel_canvas = tk.Canvas(self.home_carousel_frame, height=140, bg=self.BG_BLACK, highlightthickness=0)
        self.carousel_canvas.pack(fill=tk.X, expand=True, side=tk.LEFT)

        self.carousel_items = []
        self.carousel_photos = []

        # Try to load images from ./assets folder first
        assets_dir = os.path.join(os.getcwd(), 'assets')
        image_files = []
        if os.path.isdir(assets_dir):
            for ext in ('.png', '.jpg', '.jpeg', '.gif'):
                for fn in os.listdir(assets_dir):
                    if fn.lower().endswith(ext):
                        image_files.append(os.path.join(assets_dir, fn))

        # If no assets found, generate placeholder images
        if not image_files:
            featured = [f"Featured {i+1}" for i in range(6)]
            images = []
            for i, txt in enumerate(featured):
                img = Image.new('RGBA', (220, 120), (30 + i*20, 40 + i*15, 60 + i*10))
                draw = ImageDraw.Draw(img)
                try:
                    fnt = ImageFont.truetype("arial.ttf", 18)
                except Exception:
                    fnt = ImageFont.load_default()
                bbox = draw.textbbox((0, 0), txt, font=fnt)
                w = bbox[2] - bbox[0]
                h = bbox[3] - bbox[1]
                draw.text(((220-w)/2, (120-h)/2), txt, font=fnt, fill=(255,255,255))
                images.append(img)
        else:
            images = []
            for fp in image_files:
                try:
                    img = Image.open(fp).convert('RGBA')
                    img.thumbnail((220, 120), Image.Resampling.LANCZOS)
                    images.append(img)
                except Exception:
                    continue

        x = 10
        for i, img in enumerate(images):
            item_frame = tk.Frame(self.carousel_canvas, bg=self.BG_CARD, width=220, height=120)
            # convert to PhotoImage and keep reference
            try:
                photo = ImageTk.PhotoImage(img)
                self.carousel_photos.append(photo)
                img_label = tk.Label(item_frame, image=photo, bg=self.BG_CARD)
            except Exception:
                img_label = tk.Label(item_frame, text=f"Item {i+1}", fg=self.TEXT_WHITE, bg=self.BG_CARD)
            img_label.place(relx=0.5, rely=0.5, anchor='center')
            window = self.carousel_canvas.create_window(x, 10, anchor='nw', window=item_frame)
            self.carousel_items.append((window, item_frame))
            x += 230

        # ensure scrollregion
        self.carousel_canvas.configure(scrollregion=self.carousel_canvas.bbox('all'))

        # start animation
        self.carousel_pos = 0
        self.carousel_direction = -1
        if hasattr(self, 'carousel_after_id'):
            try:
                self.root.after_cancel(self.carousel_after_id)
            except Exception:
                pass
        self.carousel_after_id = self.root.after(50, self._animate_carousel_step)

    def _animate_carousel_step(self):
        # Move canvas by small amount for smooth scrolling
        step = 4 * self.carousel_direction
        self.carousel_canvas.xview_scroll(step, 'units')
        # reverse direction at edges
        x0, y0, x1, y1 = self.carousel_canvas.bbox('all')
        view_left = self.carousel_canvas.canvasx(0)
        view_right = view_left + self.carousel_canvas.winfo_width()
        if view_right >= x1 - 10:
            self.carousel_direction = -1
        if view_left <= 0:
            self.carousel_direction = 1

        self.carousel_after_id = self.root.after(40, self._animate_carousel_step)

    def start_header_pulse(self):
        # pulse the now_playing_header bg between two colors
        if hasattr(self, 'pulse_after_id'):
            try:
                self.root.after_cancel(self.pulse_after_id)
            except Exception:
                pass
        self._pulse_state = 0
        self._pulse_step = 0.05
        self._pulse_color_a = self.BG_CARD
        self._pulse_color_b = self.BG_SELECTED
        self._pulse_duration = 20
        self._do_pulse()

    def _do_pulse(self):
        # interpolate between two hex colors
        def lerp(a, b, t):
            return int(a + (b - a) * t)

        def hex_to_rgb(h):
            h = h.lstrip('#')
            return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

        a = hex_to_rgb(self._pulse_color_a[1:]) if self._pulse_color_a.startswith('#') else hex_to_rgb(self.BG_CARD[1:])
        b = hex_to_rgb(self._pulse_color_b[1:]) if self._pulse_color_b.startswith('#') else hex_to_rgb(self.BG_SELECTED[1:])
        t = (1 + math.sin(self._pulse_state)) / 2
        rgb = (lerp(a[0], b[0], t), lerp(a[1], b[1], t), lerp(a[2], b[2], t))
        color = '#%02x%02x%02x' % rgb
        try:
            self.now_playing_header.config(bg=color)
        except Exception:
            pass
        self._pulse_state += self._pulse_step
        self.pulse_after_id = self.root.after(80, self._do_pulse)
    
    def play_song(self, index):
        if index < 0 or index >= len(self.playlist):
            return
        self.current_index = index
        path = self.playlist[index]
        # Validate file exists
        if not os.path.exists(path):
            msg = f"File not found: {path}"
            print(msg)
            self.status_label.config(text=msg)
            return

        try:
            # Ensure mixer initialized
            if not pygame.mixer.get_init():
                try:
                    pygame.mixer.init()
                except Exception as ie:
                    print("Could not init mixer:", ie)

            pygame.mixer.music.load(path)
            pygame.mixer.music.play()
            self.is_playing = True
            self.is_paused = False
            self.play_small.config(text="⏸")
            self.current_position = 0
            self.progress_var.set(0)

            meta = self.get_metadata(path)
            title, artist = meta.get('title', os.path.splitext(os.path.basename(path))[0]), meta.get('artist','')

            # Update all displays
            try:
                self.header_title.config(text=title)
                self.header_artist.config(text=artist)
                self.player_title.config(text=title)
                self.player_artist.config(text=artist)
            except Exception:
                pass

            # Art updates (best-effort)
            try:
                album_art = self.get_album_art(path)
                if album_art and album_art[0] is not None:
                    art, shadow = album_art
                    if art is not None:
                        big_art = art.resize((80, 80), Image.Resampling.LANCZOS)
                        self.current_art_photo = ImageTk.PhotoImage(big_art)
                        self.mini_art.config(image=self.current_art_photo, text="")
                        self.header_art.config(image=self.current_art_photo, text="")
                    else:
                        self.mini_art.config(image="", text="♪")
                        self.header_art.config(image="", text="🎵 Select a track")
                else:
                    self.mini_art.config(image="", text="♪")
                    self.header_art.config(image="", text="🎵 Select a track")
            except Exception:
                pass

            self.current_song_length = meta.get('duration', 0)
            try:
                self.prog_duration.config(text=self.format_time(self.current_song_length))
            except Exception:
                pass

            self.update_playlist_grid()
            self.played_indices.append(index)
            self.status_label.config(text=f"Playing: {title}")

        except Exception as e:
            tb = traceback.format_exc()
            print(tb)
            try:
                self.status_label.config(text=f"Playback error: {e}")
            except Exception:
                pass
            messagebox.showerror("Playback Error", f"Could not play {path}: {e}\nSee console for details")
    
    def play_pause(self):
        if not self.playlist:
            return
        if self.current_index < 0:
            self.play_song(0)
            return
        if self.is_paused:
            pygame.mixer.music.unpause()
            self.is_paused = False
            self.play_small.config(text="⏸")
        elif self.is_playing:
            pygame.mixer.music.pause()
            self.is_paused = True
            self.play_small.config(text="▶")
        else:
            self.play_song(self.current_index)
    
    def next_song(self):
        if self.shuffle_mode:
            next_idx = random.choice([i for i in range(len(self.playlist)) if i not in self.played_indices[-10:]])
        else:
            next_idx = (self.current_index + 1) % len(self.playlist)
        self.play_song(next_idx)
    
    def prev_song(self):
        if self.current_position > 3:
            pygame.mixer.music.rewind()
        else:
            prev_idx = (self.current_index - 1) % len(self.playlist)
            self.play_song(prev_idx)
    
    def toggle_shuffle(self):
        self.shuffle_mode = not self.shuffle_mode
        self.shuffle_icon.config(fg=self.GREEN_ACCENT if self.shuffle_mode else self.TEXT_GRAY)
    
    def toggle_repeat(self):
        self.repeat_mode = (self.repeat_mode + 1) % 3
        icons = ["🔁", "🔂", "∞"]
        self.repeat_icon.config(text=icons[self.repeat_mode], fg=self.GREEN_ACCENT if self.repeat_mode > 0 else self.TEXT_GRAY)
    
    def update_volume(self, val):
        pygame.mixer.music.set_volume(float(val)/100)
    
    def seek_progress(self, val):
        # Limited seek
        if self.current_song_length:
            seek = (float(val)/100) * self.current_song_length
            # Pygame seek approx
            pygame.mixer.music.play(loops=0, start=seek)
    
    def format_time(self, secs):
        if secs <= 0: return "—:—"
        m, s = divmod(int(secs), 60)
        return f"{m}:{s:02d}"
    
    def start_update_thread(self):
        def loop():
            while True:
                if self.is_playing and not self.is_paused:
                    pos = pygame.mixer.music.get_pos() / 1000
                    if self.current_song_length:
                        prog = (pos / self.current_song_length) * 100
                        self.progress_var.set(prog)
                        self.prog_time.config(text=self.format_time(pos))
                threading.Event().wait(0.2)
        threading.Thread(target=loop, daemon=True).start()
    
    def check_music_end(self):
        if self.is_playing and not pygame.mixer.music.get_busy():
            if self.repeat_mode == 2:
                self.play_song(self.current_index)
            else:
                self.next_song()
        self.root.after(300, self.check_music_end)

if __name__ == "__main__":
    root = tk.Tk()
    app = SpotifyClonePlayer(root)
    root.mainloop()