import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox
import subprocess
import threading
import os
import shutil
import webbrowser
import traceback
import configparser
import sys
import requests
import json
import re
from tkinterdnd2 import DND_FILES, TkinterDnD

# Configuration constants
CONFIG_FILE = "settings.ini"
VIDEO_EXTENSIONS = ('.mp4', '.mkv', '.wmv')
INTERMODAL_EXE = "imdl" if os.name == 'nt' else "intermodal"
REQUIRED_TOOLS = {
    "ffmpeg": "https://ffmpeg.org/download.html",
    "ffprobe": "https://ffmpeg.org/download.html",
    "mtn": "https://www.videohelp.com/software/movie-thumbnailer",
    "mediainfo": "https://mediaarea.net/en/MediaInfo/Download",
    INTERMODAL_EXE: "https://github.com/casey/intermodal/releases/"
}
SCREENSHOT_COUNT = 15
SCREENSHOT_QUALITY = 2

# API endpoints
CLEARJAV_API_BASE = "https://clearjav.com/api"
R18_API_BASE = "https://r18.dev/videos/vod/movies/detail/-"

# ClearJAV resolution ID mappings
RESOLUTION_MAPPINGS = {
    "8K VR": 14,
    "VR": 13,
    "2160p": 2,
    "1080p": 3,
    "720p": 5,
    "576p": 6,
    "480p": 8,
    "404p": 11,
    "lower": 15
}

def resource_path(relative_path):
    """Get absolute path to resource, works for development and PyInstaller."""
    try:
        base_path = getattr(sys, '_MEIPASS', None)
        if base_path is None:
            base_path = os.path.abspath(".")
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

class VideoProcessorApp(TkinterDnD.Tk):
    def __init__(self):
        super().__init__()

        # Main window setup
        self.withdraw()

        # Configure theme
        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("blue")
        self.config(bg=ctk.ThemeManager.theme["CTk"]["fg_color"][1])

        self.title("Torrent Metadata Creator")
        self.geometry("800x1000")
        
        # Set application icon
        try:
            icon_path = resource_path("cj.ico")
            self.iconbitmap(icon_path)
        except tk.TclError:
            print("Warning: cj.ico not found. Using default icon.")

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)

        # Initialize variables
        self.input_path = tk.StringVar()
        self.tracker_url = tk.StringVar()
        self.api_key = tk.StringVar()
        self.generate_screenshots = tk.BooleanVar()
        self.auto_upload = tk.BooleanVar()
        self.anonymous_upload = tk.BooleanVar()
        self.personal_release = tk.BooleanVar()
        self.internal_release = tk.BooleanVar()
        self.bypass_mod_queue = tk.BooleanVar()
        self.custom_tag = tk.StringVar()
        self.filename_mode = tk.StringVar(value="content_id")
        self.tool_paths = {}
        
        # API validation state
        self.user_data = None
        self.is_internal_user = False

        self.load_config()

        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.after(100, self.check_dependencies)


    def center_window(self, win):
        """Centers a tkinter window on the screen without flashing."""
        win.update_idletasks()
        width = win.winfo_width()
        height = win.winfo_height()
        x = (win.winfo_screenwidth() // 2) - (width // 2)
        y = (win.winfo_screenheight() // 2) - (height // 2)
        win.geometry(f'{width}x{height}+{x}+{y}')
        win.focus_force()

    def on_closing(self):
        """Save config on exit and destroy the window."""
        self.save_config()
        self.destroy()

    def load_config(self):
        """Load settings from the .ini file."""
        config = configparser.ConfigParser()
        if os.path.exists(CONFIG_FILE):
            config.read(CONFIG_FILE)
            self.tracker_url.set(config.get('Settings', 'TrackerURL', fallback=''))
            self.api_key.set(config.get('Settings', 'ApiKey', fallback=''))
            self.generate_screenshots.set(config.getboolean('Settings', 'GenerateScreenshots', fallback=False))
            self.auto_upload.set(config.getboolean('Settings', 'AutoUpload', fallback=False))
            self.anonymous_upload.set(config.getboolean('Settings', 'AnonymousUpload', fallback=False))
            self.personal_release.set(config.getboolean('Settings', 'PersonalRelease', fallback=False))
            self.internal_release.set(config.getboolean('Settings', 'InternalRelease', fallback=False))
            self.bypass_mod_queue.set(config.getboolean('Settings', 'BypassModQueue', fallback=False))
            self.custom_tag.set(config.get('Settings', 'CustomTag', fallback=''))
            self.filename_mode.set(config.get('Settings', 'FilenameMode', fallback='content_id'))

    def save_config(self):
        """Save current settings to the .ini file."""
        config = configparser.ConfigParser()
        config['Settings'] = {
            'TrackerURL': self.tracker_url.get(),
            'ApiKey': self.api_key.get(),
            'GenerateScreenshots': str(self.generate_screenshots.get()),
            'AutoUpload': str(self.auto_upload.get()),
            'AnonymousUpload': str(self.anonymous_upload.get()),
            'PersonalRelease': str(self.personal_release.get()),
            'InternalRelease': str(self.internal_release.get()),
            'BypassModQueue': str(self.bypass_mod_queue.get()),
            'CustomTag': self.custom_tag.get(),
            'FilenameMode': self.filename_mode.get()
        }
        with open(CONFIG_FILE, 'w') as configfile:
            config.write(configfile)

    def check_dependencies(self):
        """Check for required command-line tools and display results in a popup."""
        check_window = ctk.CTkToplevel(self)
        check_window.title("Dependency Check")
        check_window.geometry("450x280")
        check_window.resizable(False, False)
        check_window.transient(self)
        check_window.grab_set()
        check_window.grid_columnconfigure(0, weight=1)
        
        title_label = ctk.CTkLabel(check_window, text="Checking for Required Tools...", font=ctk.CTkFont(size=16, weight="bold"))
        title_label.grid(row=0, column=0, columnspan=3, pady=10, padx=10)

        all_found = True
        base_path = resource_path(".")

        for i, (tool, url) in enumerate(REQUIRED_TOOLS.items()):
            label = ctk.CTkLabel(check_window, text=f"{tool}:", anchor="w")
            label.grid(row=i+1, column=0, padx=20, pady=5, sticky="w")
            
            found_path = None
            if os.name == 'nt':
                local_path_exe = os.path.join(base_path, f"{tool}.exe")
                if os.path.exists(local_path_exe):
                    found_path = local_path_exe
            
            if not found_path:
                local_path = os.path.join(base_path, tool)
                if os.path.exists(local_path):
                    found_path = local_path

            # Fall back to system PATH
            if not found_path:
                found_path = shutil.which(tool)

            if found_path:
                self.tool_paths[tool] = found_path
                status_label = ctk.CTkLabel(check_window, text="✓ Found", text_color="green")
                status_label.grid(row=i+1, column=1, padx=10, pady=5, sticky="w")
            else:
                all_found = False
                status_label = ctk.CTkLabel(check_window, text="✗ Not Found", text_color="red")
                status_label.grid(row=i+1, column=1, padx=10, pady=5, sticky="w")
                link_button = ctk.CTkButton(check_window, text="Get", width=50, command=lambda u=url: webbrowser.open_new_tab(u))
                link_button.grid(row=i+1, column=2, padx=10, pady=5)

        ok_button = ctk.CTkButton(check_window, text="Continue")
        ok_button.grid(row=len(REQUIRED_TOOLS)+1, column=0, columnspan=3, pady=(10,0))
        countdown_label = ctk.CTkLabel(check_window, text="", font=ctk.CTkFont(size=12))
        countdown_label.grid(row=len(REQUIRED_TOOLS)+2, column=0, columnspan=3, pady=5)
        
        self.center_window(check_window)

        def close_and_launch():
            check_window.destroy()
            self.create_main_widgets()
            self.center_window(self)
            self.deiconify()

        if all_found:
            ok_button.grid_forget()
            check_window.protocol("WM_DELETE_WINDOW", close_and_launch)
            
            def countdown(seconds_left):
                if seconds_left > 0:
                    countdown_label.configure(text=f"Success! Launching in {seconds_left}...")
                    self.after(1000, countdown, seconds_left - 1)
                else:
                    close_and_launch()
            countdown(3)
        else:
            ok_button.configure(text="Exit", command=self.destroy)
            check_window.protocol("WM_DELETE_WINDOW", self.destroy)

    def create_main_widgets(self):
        """Create the main UI components."""
        # Input area with drag & drop support
        input_container_frame = ctk.CTkFrame(self)
        input_container_frame.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        input_container_frame.grid_columnconfigure(0, weight=1)
        
        self.drop_zone = ctk.CTkFrame(input_container_frame, height=100, border_width=2, border_color="gray50")
        self.drop_zone.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        self.drop_zone.grid_columnconfigure(0, weight=1)
        self.drop_zone.grid_rowconfigure(0, weight=1)

        self.path_display_label = ctk.CTkLabel(self.drop_zone, textvariable=self.input_path, text_color="gray60")
        self.path_display_label.grid(row=0, column=0, padx=10, pady=10)

        self.browse_button = ctk.CTkButton(self.drop_zone, text="Browse...", command=self.browse_path, width=120)
        self.browse_button.grid(row=1, column=0, pady=(0, 10))
        
        # Register drag and drop targets
        self.drop_zone.drop_target_register(DND_FILES)  # type: ignore
        self.path_display_label.drop_target_register(DND_FILES)  # type: ignore
        self.drop_zone.dnd_bind('<<Drop>>', self.handle_drop)  # type: ignore
        self.path_display_label.dnd_bind('<<Drop>>', self.handle_drop)  # type: ignore
        
        self.input_path.set("Drop File/Folder Here or Click Browse")

        # Options frame
        options_frame = ctk.CTkFrame(self)
        options_frame.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="ew")
        options_frame.grid_columnconfigure(1, weight=1)

        self.screenshots_checkbox = ctk.CTkCheckBox(options_frame, text="Generate 15 Screenshots for the Gallery", variable=self.generate_screenshots)
        self.screenshots_checkbox.grid(row=0, column=0, columnspan=3, padx=10, pady=5)
        
        ctk.CTkLabel(options_frame, text="Announce URL:").grid(row=1, column=0, padx=10, pady=5)
        self.tracker_entry = ctk.CTkEntry(options_frame, textvariable=self.tracker_url, placeholder_text="Required for .torrent creation")
        self.tracker_entry.grid(row=1, column=1, columnspan=2, padx=10, pady=5, sticky="ew")

        # API configuration frame
        api_frame = ctk.CTkFrame(self)
        api_frame.grid(row=2, column=0, padx=10, pady=(0, 10), sticky="ew")
        api_frame.grid_columnconfigure(1, weight=1)
        
        ctk.CTkLabel(api_frame, text="API Configuration", font=ctk.CTkFont(size=14, weight="bold")).grid(row=0, column=0, columnspan=3, padx=10, pady=5)
        
        # API Key
        ctk.CTkLabel(api_frame, text="ClearJAV API Key:").grid(row=1, column=0, padx=10, pady=5)
        self.api_key_entry = ctk.CTkEntry(api_frame, textvariable=self.api_key, placeholder_text="Enter your API key", show="*")
        self.api_key_entry.grid(row=1, column=1, padx=10, pady=5, sticky="ew")
        self.validate_api_button = ctk.CTkButton(api_frame, text="Validate", command=self.validate_api_key_ui, width=80)
        self.validate_api_button.grid(row=1, column=2, padx=10, pady=5)
        
        # API Status
        self.api_status_label = ctk.CTkLabel(api_frame, text="API Key not validated", text_color="orange")
        self.api_status_label.grid(row=2, column=0, columnspan=3, padx=10, pady=5)
        
        # Auto Upload
        self.auto_upload_checkbox = ctk.CTkCheckBox(api_frame, text="Enable Automatic Upload after generation", 
                                                   variable=self.auto_upload, command=self.on_auto_upload_changed,
                                                   state="disabled")  # Start disabled until API key is validated
        self.auto_upload_checkbox.grid(row=3, column=0, columnspan=3, padx=10, pady=5)
        
        # Filename Mode Selector
        filename_frame = ctk.CTkFrame(api_frame)
        filename_frame.grid(row=4, column=0, columnspan=3, padx=10, pady=5, sticky="ew")
        filename_frame.grid_columnconfigure(1, weight=1)
        
        ctk.CTkLabel(filename_frame, text="Rename files to:").grid(row=0, column=0, padx=10, pady=5, sticky="w")
        self.filename_mode_menu = ctk.CTkOptionMenu(filename_frame, values=["Content ID", "DVD ID", "Torrent Title"], 
                                                   command=self.on_filename_mode_changed)
        self.filename_mode_menu.grid(row=0, column=1, padx=10, pady=5, sticky="w")
        
        # Upload Options Frame - improved layout
        self.upload_options_frame = ctk.CTkFrame(api_frame)
        self.upload_options_frame.grid(row=5, column=0, columnspan=3, padx=10, pady=5, sticky="ew")
        self.upload_options_frame.grid_columnconfigure(0, weight=1)
        self.upload_options_frame.grid_columnconfigure(1, weight=1)
        
        # Row 0: Anonymous and Personal Release
        self.anonymous_checkbox = ctk.CTkCheckBox(self.upload_options_frame, text="Anonymous Upload", variable=self.anonymous_upload)
        self.anonymous_checkbox.grid(row=0, column=0, padx=10, pady=5, sticky="w")
        
        self.personal_release_checkbox = ctk.CTkCheckBox(self.upload_options_frame, text="Personal Release", 
                                                        variable=self.personal_release, command=self.on_personal_release_changed)
        self.personal_release_checkbox.grid(row=0, column=1, padx=10, pady=5, sticky="w")
        
        # Row 1: Internal Release and Bypass Mod Queue
        self.internal_release_checkbox = ctk.CTkCheckBox(self.upload_options_frame, text="Internal Release", 
                                                        variable=self.internal_release, command=self.on_internal_release_changed)
        self.internal_release_checkbox.grid(row=1, column=0, padx=10, pady=5, sticky="w")
        
        self.bypass_mod_queue_checkbox = ctk.CTkCheckBox(self.upload_options_frame, text="Bypass Mod. Queue", 
                                                        variable=self.bypass_mod_queue, command=self.on_bypass_mod_queue_changed)
        self.bypass_mod_queue_checkbox.grid(row=1, column=1, padx=10, pady=5, sticky="w")
        
        # Row 2: Custom Tag with help button
        tag_frame = ctk.CTkFrame(self.upload_options_frame)
        tag_frame.grid(row=2, column=0, columnspan=2, padx=10, pady=5, sticky="ew")
        tag_frame.grid_columnconfigure(2, weight=1)
        
        ctk.CTkLabel(tag_frame, text="Tag Name:").grid(row=0, column=0, padx=(10,5), pady=5, sticky="w")
        
        # Help button
        self.help_button = ctk.CTkButton(tag_frame, text="?", width=25, height=25, 
                                        command=lambda: self.open_help_link("https://clearjav.com/wikis/2#tn-tag"))
        self.help_button.grid(row=0, column=1, padx=(0,5), pady=5)
        
        self.custom_tag_entry = ctk.CTkEntry(tag_frame, textvariable=self.custom_tag, placeholder_text="Optional")
        self.custom_tag_entry.grid(row=0, column=2, padx=(5,10), pady=5, sticky="ew")
        
        # Initially disable upload options
        self.toggle_upload_options(False)
        self.toggle_internal_options(False)
        self.toggle_custom_tag(False)
        
        # Set initial filename mode from config
        mode_display_map = {"content_id": "Content ID", "dvd_id": "DVD ID", "torrent_title": "Torrent Title"}
        display_value = mode_display_map.get(self.filename_mode.get(), "Content ID")
        self.filename_mode_menu.set(display_value)

        # Log output frame
        log_frame = ctk.CTkFrame(self)
        log_frame.grid(row=3, column=0, padx=10, pady=(0, 10), sticky="nsew")
        log_frame.grid_rowconfigure(1, weight=1)
        log_frame.grid_columnconfigure(0, weight=1)
        
        ctk.CTkLabel(log_frame, text="Processing Log", font=ctk.CTkFont(size=14, weight="bold")).grid(row=0, column=0, padx=10, pady=10)
        self.log_textbox = ctk.CTkTextbox(log_frame, wrap="word")
        self.log_textbox.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="nsew")
        self.log_textbox.configure(state="disabled")

        # Action and progress frame
        action_frame = ctk.CTkFrame(self)
        action_frame.grid(row=4, column=0, padx=10, pady=10, sticky="ew")
        action_frame.grid_columnconfigure(0, weight=1)

        self.generate_button = ctk.CTkButton(action_frame, text="Generate Files", command=self.start_generation_thread, font=ctk.CTkFont(size=14, weight="bold"))
        self.generate_button.grid(row=0, column=0, columnspan=3, padx=10, pady=10, sticky="ew")
        
        self.status_label = ctk.CTkLabel(action_frame, text="Ready. Drop a file/folder or browse to begin.")
        self.status_label.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="w")
        
        self.progress_bar = ctk.CTkProgressBar(action_frame)
        self.progress_bar.set(0)
        self.progress_bar.grid(row=1, column=1, padx=10, pady=(0, 10), sticky="ew")
        
        self.progress_label = ctk.CTkLabel(action_frame, text="0%")
        self.progress_label.grid(row=1, column=2, padx=10, pady=(0, 10), sticky="e")

    def toggle_upload_options(self, enabled):
        """Enable/disable upload option controls."""
        state = "normal" if enabled else "disabled"
        self.anonymous_checkbox.configure(state=state)
        self.personal_release_checkbox.configure(state=state)
        
        if hasattr(self, 'filename_mode_menu'):
            self.filename_mode_menu.configure(state=state)
        
        if hasattr(self, 'custom_tag_entry'):
            tag_enabled = enabled and self.personal_release.get()
            self.toggle_custom_tag(tag_enabled)
        
        if hasattr(self, 'internal_release_checkbox'):
            if not self.is_internal_user:
                self.internal_release_checkbox.configure(state="disabled")
            else:
                self.internal_release_checkbox.configure(state=state)
        
        if hasattr(self, 'bypass_mod_queue_checkbox'):
            if not self.is_internal_user:
                self.bypass_mod_queue_checkbox.configure(state="disabled")
            else:
                self.bypass_mod_queue_checkbox.configure(state=state)

    def toggle_internal_options(self, enabled):
        """Enable/disable internal user options."""
        if hasattr(self, 'internal_release_checkbox'):
            state = "normal" if (enabled and self.is_internal_user) else "disabled"
            self.internal_release_checkbox.configure(state=state)
        
        if hasattr(self, 'bypass_mod_queue_checkbox'):
            state = "normal" if (enabled and self.is_internal_user) else "disabled"
            self.bypass_mod_queue_checkbox.configure(state=state)
            
    def toggle_custom_tag(self, enabled):
        """Enable/disable custom tag field based on personal release selection."""
        if hasattr(self, 'custom_tag_entry'):
            if self.internal_release.get():
                self.custom_tag_entry.configure(state="disabled")
            else:
                state = "normal" if enabled else "disabled"
                self.custom_tag_entry.configure(state=state)
                
            # Gray out the text if disabled
            if enabled and not self.internal_release.get():
                self.custom_tag_entry.configure(text_color="white")
            else:
                self.custom_tag_entry.configure(text_color="gray")
            
    def on_auto_upload_changed(self):
        """Called when auto upload checkbox is changed."""
        enabled = self.auto_upload.get()
        self.toggle_upload_options(enabled and self.user_data is not None)
        
    def on_personal_release_changed(self):
        """Called when personal release checkbox is changed."""
        enabled = self.auto_upload.get() and self.user_data is not None
        tag_enabled = enabled and self.personal_release.get()
        self.toggle_custom_tag(tag_enabled)
        
        if not self.personal_release.get() and self.internal_release.get():
            self.personal_release.set(True)
        
    def on_internal_release_changed(self):
        """Called when internal release checkbox is changed."""
        if self.internal_release.get():
            self.personal_release.set(True)
            self.custom_tag.set("ClearJAV")
            self.custom_tag_entry.configure(state="disabled")
        else:
            enabled = self.auto_upload.get() and self.user_data is not None
            tag_enabled = enabled and self.personal_release.get()
            self.toggle_custom_tag(tag_enabled)
            if self.custom_tag.get() == "ClearJAV":
                self.custom_tag.set("")
    
    def on_bypass_mod_queue_changed(self):
        """Called when bypass mod queue checkbox is changed."""
        pass
        
    def on_filename_mode_changed(self, value):
        """Called when filename mode is changed."""
        # Convert display value to internal value
        mode_map = {"Content ID": "content_id", "DVD ID": "dvd_id", "Torrent Title": "torrent_title"}
        self.filename_mode.set(mode_map.get(value, "content_id"))
        
    def open_help_link(self, url):
        """Opens a help link in the default browser."""
        webbrowser.open(url)

    def validate_api_key_ui(self):
        """UI wrapper for API key validation."""
        api_key = self.api_key.get().strip()
        if not api_key:
            self.api_status_label.configure(text="Please enter an API key", text_color="red")
            return

        self.api_status_label.configure(text="Validating...", text_color="orange")
        self.validate_api_button.configure(state="disabled")
        
        def validate_in_thread():
            success, user_data = self.validate_api_key(api_key)
            
            def update_ui():
                self.validate_api_button.configure(state="normal")
                if success and user_data:
                    username = user_data.get('username', 'Unknown')
                    group = user_data.get('group', 'Unknown')
                    self.api_status_label.configure(text=f"✓ Valid - {username} ({group})", text_color="green")
                    
                    if not self.is_internal_user and self.internal_release.get():
                        self.internal_release.set(False)
                        self.log_message("Internal Release deselected - insufficient privileges")
                    
                    if not self.is_internal_user and self.bypass_mod_queue.get():
                        self.bypass_mod_queue.set(False)
                        self.log_message("Bypass Mod. Queue deselected - insufficient privileges")
                    
                    self.auto_upload_checkbox.configure(state="normal")
                    
                    self.toggle_upload_options(self.auto_upload.get())
                    self.toggle_internal_options(True)
                    self.save_config()
                else:
                    self.api_status_label.configure(text="✗ Invalid API key", text_color="red")
                    self.auto_upload.set(False)
                    self.auto_upload_checkbox.configure(state="disabled")
                    self.toggle_upload_options(False)
                    self.toggle_internal_options(False)
            
            self.after(0, update_ui)
        
        thread = threading.Thread(target=validate_in_thread)
        thread.daemon = True
        thread.start()
        
    def handle_drop(self, event):
        """Handle file/folder drop events."""
        path = self.tk.splitlist(event.data)[0]
        if os.path.isdir(path) or (os.path.isfile(path) and path.lower().endswith(VIDEO_EXTENSIONS)):
            self.input_path.set(path)
            self.path_display_label.configure(text_color="white")
        else:
            self.status_label.configure(text="Error: Dropped item is not a valid video file or folder.", text_color="red")
            self.input_path.set("Drop File/Folder Here or Click Browse")
            self.path_display_label.configure(text_color="gray60")

    def show_error_window(self, title, message):
        """Display detailed error messages in a popup window."""
        error_window = ctk.CTkToplevel(self)
        error_window.title(title)
        error_window.geometry("700x450")
        error_window.transient(self)
        error_window.grab_set()
        error_window.grid_columnconfigure(0, weight=1)
        error_window.grid_rowconfigure(0, weight=1)
        
        textbox = ctk.CTkTextbox(error_window, wrap="word", font=ctk.CTkFont(family="monospace"))
        textbox.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        textbox.insert("1.0", message)
        textbox.configure(state="disabled")
        ok_button = ctk.CTkButton(error_window, text="OK", command=error_window.destroy, width=100)
        ok_button.grid(row=1, column=0, padx=10, pady=(0, 10))

        self.center_window(error_window)

    def log_message(self, message):
        """Append a message to the log textbox."""
        self.log_textbox.configure(state="normal")
        self.log_textbox.insert("end", message + "\n")
        self.log_textbox.see("end")
        self.log_textbox.configure(state="disabled")

    def browse_path(self):
        """Open a selection dialog to choose between file or folder."""
        selection_window = ctk.CTkToplevel(self)
        selection_window.title("Select Input Type")
        selection_window.geometry("300x150")
        selection_window.transient(self)
        selection_window.grab_set()
        selection_window.grid_columnconfigure(0, weight=1)
        selection_window.grid_rowconfigure(0, weight=1)
        selection_window.grid_rowconfigure(1, weight=1)

        def select_file():
            selection_window.grab_release()
            selection_window.destroy()
            path = filedialog.askopenfilename(
                title="Select a Video File",
                filetypes=(("Video Files", "*.mp4 *.mkv *.wmv"), ("All files", "*.*"))
            )
            if path:
                self.input_path.set(path)
                self.path_display_label.configure(text_color="white")

        def select_folder():
            selection_window.grab_release()
            selection_window.destroy()
            path = filedialog.askdirectory(title="Select a Folder Containing Videos")
            if path:
                self.input_path.set(path)
                self.path_display_label.configure(text_color="white")

        file_button = ctk.CTkButton(selection_window, text="Select a Single File", command=select_file)
        file_button.grid(row=0, column=0, padx=20, pady=10, sticky="ew")

        folder_button = ctk.CTkButton(selection_window, text="Select a Folder (Bulk)", command=select_folder)
        folder_button.grid(row=1, column=0, padx=20, pady=10, sticky="ew")
        
        self.center_window(selection_window)

    def validate_api_key(self, api_key):
        """Validate the API key by checking user information."""
        try:
            response = requests.get(f"{CLEARJAV_API_BASE}/user", params={"api_token": api_key}, timeout=10)
            if response.status_code == 200:
                user_data = response.json()
                self.user_data = user_data
                user_group = user_data.get('group', '').lower()
                self.is_internal_user = user_group in ['internal', 'moderator', 'owner', 'mod']
                self.log_message(f"API Key validated. User: {user_data.get('username')}, Group: {user_data.get('group')}")
                return True, user_data
            else:
                return False, None
        except requests.RequestException as e:
            self.log_message(f"API validation failed: {str(e)}")
            return False, None
    
    def check_for_duplicates(self, dvd_id):
        """Check if torrents with the same DVD ID already exist on ClearJAV."""
        try:
            api_url = f"{CLEARJAV_API_BASE}/torrents/filter"
            search_methods = [
                {'name': dvd_id},
                {'description': dvd_id},
                {'keywords': dvd_id}
            ]
            
            all_duplicates = []
            
            for search_params in search_methods:
                search_params['api_token'] = self.api_key.get()
                
                response = requests.get(api_url, params=search_params, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    
                    torrents = []
                    if isinstance(data, dict):
                        torrents = data.get('data', [])
                    elif isinstance(data, list):
                        torrents = data
                    
                    for torrent in torrents:
                        torrent_name = ''
                        if 'attributes' in torrent:
                            torrent_name = torrent['attributes'].get('name', '').upper()
                        else:
                            torrent_name = torrent.get('name', '').upper()
                            
                        if dvd_id.upper() in torrent_name:
                            if not any(t.get('id') == torrent.get('id') for t in all_duplicates):
                                all_duplicates.append(torrent)
            
            return all_duplicates
            
        except requests.RequestException as e:
            self.log_message(f"Error checking for duplicates: {str(e)}")
            return []
        except json.JSONDecodeError as e:
            self.log_message(f"Error parsing duplicate check response: {str(e)}")
            return []
    
    def show_duplicate_confirmation_dialog(self, dvd_id, duplicates):
        """Show dialog asking user if they want to proceed despite duplicates."""
        dialog = ctk.CTkToplevel(self)
        dialog.title("Duplicate Content Found")
        dialog.geometry("600x400")
        dialog.transient(self)
        dialog.grab_set()
        dialog.grid_columnconfigure(0, weight=1)
        dialog.grid_rowconfigure(2, weight=1)
        
        result = {'proceed': False}
        
        # Warning message
        warning_text = f"⚠️ Found {len(duplicates)} existing torrent(s) with DVD ID: {dvd_id}\n\nThis content may already be available on ClearJAV."
        warning_label = ctk.CTkLabel(dialog, text=warning_text, font=ctk.CTkFont(size=14, weight="bold"), 
                                   text_color="orange", justify="left")
        warning_label.grid(row=0, column=0, padx=20, pady=20, sticky="ew")
        
        # Information text
        info_text = "Existing torrents found:"
        info_label = ctk.CTkLabel(dialog, text=info_text, font=ctk.CTkFont(size=12), justify="left")
        info_label.grid(row=1, column=0, padx=20, pady=(0, 10), sticky="w")
        
        # Scrollable list of existing torrents
        scrollable_frame = ctk.CTkScrollableFrame(dialog, height=150)
        scrollable_frame.grid(row=2, column=0, padx=20, pady=(0, 20), sticky="nsew")
        scrollable_frame.grid_columnconfigure(0, weight=1)
        
        for i, torrent in enumerate(duplicates[:10]):  # Show max 10
            if 'attributes' in torrent:
                attrs = torrent['attributes']
                name = attrs.get('name', 'Unknown')
                size = attrs.get('size', 'Unknown')
                seeders = attrs.get('seeders', 'Unknown')
                leechers = attrs.get('leechers', 'Unknown')
            else:
                name = torrent.get('name', 'Unknown')
                size = torrent.get('size', 'Unknown')
                seeders = torrent.get('seeders', 'Unknown')
                leechers = torrent.get('leechers', 'Unknown')
            
            torrent_info = f"• {name}\n  Size: {size} | Seeders: {seeders} | Leechers: {leechers}"
            torrent_label = ctk.CTkLabel(scrollable_frame, text=torrent_info, justify="left", anchor="w")
            torrent_label.grid(row=i, column=0, padx=10, pady=5, sticky="ew")
        
        if len(duplicates) > 10:
            more_label = ctk.CTkLabel(scrollable_frame, text=f"... and {len(duplicates) - 10} more", 
                                    font=ctk.CTkFont(size=11), text_color="gray")
            more_label.grid(row=10, column=0, padx=10, pady=5, sticky="ew")
        
        # Question text
        question_text = "Do you want to proceed anyway?\n(Only proceed if you have a better quality version or different encode)"
        question_label = ctk.CTkLabel(dialog, text=question_text, font=ctk.CTkFont(size=12), justify="center")
        question_label.grid(row=3, column=0, padx=20, pady=20)
        
        def on_proceed():
            result['proceed'] = True
            dialog.destroy()
        
        def on_cancel():
            result['proceed'] = False
            dialog.destroy()
        
        # Buttons
        button_frame = ctk.CTkFrame(dialog)
        button_frame.grid(row=4, column=0, padx=20, pady=(0, 20), sticky="ew")
        button_frame.grid_columnconfigure(0, weight=1)
        button_frame.grid_columnconfigure(1, weight=1)
        
        cancel_button = ctk.CTkButton(button_frame, text="Cancel Upload", command=on_cancel, 
                                    fg_color="gray", hover_color="dark gray")
        cancel_button.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        
        proceed_button = ctk.CTkButton(button_frame, text="Proceed Anyway", command=on_proceed,
                                     fg_color="orange", hover_color="dark orange")
        proceed_button.grid(row=0, column=1, padx=10, pady=10, sticky="ew")
        
        self.center_window(dialog)
        self.wait_window(dialog)
        return result['proceed']
    
    def fetch_r18_data(self, jav_id):
        """Fetch data from R18.dev API and validate content exists."""
        def try_api_call(content_id):
            try:
                api_url = f"{R18_API_BASE}/combined={content_id}/json"
                
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                    'Accept': 'application/json, text/plain, */*',
                    'Accept-Language': 'en-US,en;q=0.9',
                    'Accept-Encoding': 'gzip, deflate',  # Avoid brotli to prevent decompression issues
                    'Connection': 'keep-alive',
                    'Referer': f'https://r18.dev/videos/vod/movies/detail/-/id={content_id}/',
                }
                
                response = requests.get(api_url, headers=headers, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    
                    if not data or data.get('error'):
                        return None, None, False
                    
                    dvd_id = data.get('dvd_id')
                    if dvd_id:
                        dvd_id = dvd_id.strip()
                    
                    release_date = (data.get('release_date') or '').strip()
                    
                    self.log_message(f"  - R18.dev API response for {content_id}: DVD ID='{dvd_id or 'MISSING'}', Release Date='{release_date or 'MISSING'}'")
                    return dvd_id, release_date, True
                elif response.status_code == 404:
                    return None, None, False
                else:
                    return None, None, False
            except (requests.RequestException, json.JSONDecodeError):
                return None, None, False
        
        dvd_id, release_date, exists = try_api_call(jav_id)
        if exists:
            return dvd_id, release_date, True
        
        match = re.match(r'^([a-zA-Z]+)(\d+)$', jav_id.lower())
        if match:
            letters, numbers = match.groups()
            
            # Try different padding options
            for padding in [5, 3]:  # Try 5-digit padding first, then 3-digit
                if len(numbers) < padding:
                    padded_numbers = numbers.zfill(padding)
                    padded_id = f"{letters}{padded_numbers}"
                    
                    if padded_id != jav_id.lower():
                        self.log_message(f"  - Trying padded version: {padded_id}")
                        dvd_id, release_date, exists = try_api_call(padded_id)
                        if exists:
                            return dvd_id, release_date, True
        
        match = re.match(r'^([a-zA-Z]+)0+(\d+)$', jav_id.lower())
        if match:
            letters, numbers = match.groups()
            unpadded_id = f"{letters}{numbers}"
            
            if unpadded_id != jav_id.lower():
                self.log_message(f"  - Trying unpadded version: {unpadded_id}")
                dvd_id, release_date, exists = try_api_call(unpadded_id)
                if exists:
                    return dvd_id, release_date, True
        
        self.log_message(f"  - Content ID {jav_id} not found on R18.dev")
        return None, None, False
    
    def get_resolution_from_mediainfo(self, mediainfo_path):
        """Extract resolution from MediaInfo file."""
        try:
            with open(mediainfo_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            width_match = re.search(r'Width\s*:\s*([0-9,\s]+)', content)
            height_match = re.search(r'Height\s*:\s*([0-9,\s]+)', content)
            
            if width_match and height_match:
                width = int(width_match.group(1).replace(',', '').replace(' ', ''))
                height = int(height_match.group(1).replace(',', '').replace(' ', ''))
                
                # Determine resolution label
                if height >= 2160:
                    return "2160p"
                elif height >= 1080:
                    return "1080p"
                elif height >= 720:
                    return "720p"
                elif height >= 576:
                    return "576p"
                elif height >= 480:
                    return "480p"
                elif height >= 404:
                    return "404p"
                else:
                    return "lower"
            return "1080p"
        except Exception as e:
            self.log_message(f"Error reading MediaInfo: {str(e)}")
            return "1080p"
    
    def get_video_codec_from_mediainfo(self, mediainfo_path):
        """Extract video codec from MediaInfo file and convert to simplified naming."""
        try:
            with open(mediainfo_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            video_section = re.search(r'Video[\s\S]*?(?=\n\n|\nAudio|\Z)', content)
            if video_section:
                video_content = video_section.group(0)
                
                format_match = re.search(r'Format\s*:\s*([^\n]+)', video_content)
                if format_match:
                    format_name = format_match.group(1).strip()
                    
                    if 'AVC' in format_name or 'H.264' in format_name:
                        return "H.264"
                    elif 'HEVC' in format_name or 'H.265' in format_name:
                        return "H.265"
                    elif 'VP9' in format_name:
                        return "VP9"
                    elif 'MPEG-2' in format_name:
                        return "MPEG-2"
                    elif 'VC-1' in format_name:
                        return "VC-1"
                
                codec_match = re.search(r'Codec ID\s*:\s*([^\n]+)', video_content)
                if codec_match:
                    codec = codec_match.group(1).strip().upper()
                    
                    if 'AVC' in codec or 'H264' in codec or 'MPEG4/ISO/AVC' in codec:
                        return "H.264"
                    elif 'HEVC' in codec or 'H265' in codec:
                        return "H.265"
                    elif 'VP9' in codec:
                        return "VP9"
                    elif 'MPEG-2' in codec:
                        return "MPEG-2"
                    elif 'VC-1' in codec:
                        return "VC-1"
            
            return "H.264"
        except Exception as e:
            self.log_message(f"Error reading video codec: {str(e)}")
            return "H.264"  # Default fallback
    
    def get_audio_codec_from_mediainfo(self, mediainfo_path):
        """Extract audio codec from MediaInfo file and convert to simplified naming."""
        try:
            with open(mediainfo_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            audio_section = re.search(r'Audio[\s\S]*?(?=\n\n|\Z)', content)
            if audio_section:
                audio_content = audio_section.group(0)
                format_match = re.search(r'Format\s*:\s*([^\n]+)', audio_content)
                if format_match:
                    format_name = format_match.group(1).strip()
                    
                    if 'AAC' in format_name:
                        return "AAC"
                    elif 'AC-3' in format_name or 'AC3' in format_name:
                        return "DD"
                    elif 'E-AC-3' in format_name or 'EAC3' in format_name:
                        return "DD+"
                    elif 'TrueHD' in format_name:
                        return "TrueHD"
                    elif 'DTS-HD MA' in format_name or 'DTS-HD Master Audio' in format_name:
                        return "DTS-HD MA"
                    elif 'DTS-HD HRA' in format_name or 'DTS-HD High Resolution' in format_name:
                        return "DTS-HD HRA"
                    elif 'DTS:X' in format_name:
                        return "DTS:X"
                    elif 'DTS-ES' in format_name:
                        return "DTS-ES"
                    elif 'DTS' in format_name:
                        return "DTS"
                    elif 'FLAC' in format_name:
                        return "FLAC"
                    elif 'ALAC' in format_name:
                        return "ALAC"
                    elif 'PCM' in format_name or 'LPCM' in format_name:
                        return "LPCM"
                    elif 'Opus' in format_name:
                        return "Opus"
                    
                    return format_name
            
            return "AAC"
        except Exception as e:
            self.log_message(f"Error reading audio codec: {str(e)}")
            return "AAC"
    
    def construct_torrent_title(self, dvd_id, release_date, resolution, video_codec, audio_codec, is_internal=False, is_personal=False, custom_tag=""):
        """Construct the torrent title according to the specified format."""
        source = "DMM"
        type_name = "WEB-DL"
        
        title_parts = [dvd_id, release_date, resolution, source, type_name, video_codec, audio_codec]
        title = " ".join(title_parts)
        
        if is_internal:
            title += "-ClearJAV"
        elif is_personal and custom_tag:
            title += f"-{custom_tag}"
            
        return title
    
    def upload_torrent_to_api(self, torrent_data):
        """Upload torrent to ClearJAV API."""
        try:
            files = {}
            data = {}
            
            with open(torrent_data['torrent_path'], 'rb') as f:
                files['torrent'] = (os.path.basename(torrent_data['torrent_path']), f.read(), 'application/x-bittorrent')
            
            if 'contact_sheet_path' in torrent_data and os.path.exists(torrent_data['contact_sheet_path']):
                with open(torrent_data['contact_sheet_path'], 'rb') as f:
                    files['thumb_sheets[]'] = (os.path.basename(torrent_data['contact_sheet_path']), f.read(), 'image/jpeg')
            
            data.update({
                'api_token': self.api_key.get(),
                'jav_id': torrent_data['jav_id'],
                'dvd_id': torrent_data['dvd_id'],
                'name': torrent_data['title'],
                'description': torrent_data['description'],
                'mediainfo': torrent_data['mediainfo'],
                'category_id': 1,
                'type_id': 4,
                'resolution_id': torrent_data['resolution_id'],
                'anonymous': 1 if self.anonymous_upload.get() else 0,
                'personal_release': 1 if self.personal_release.get() else 0,
                'mod_queue_opt_in': 0 if self.bypass_mod_queue.get() else 1
            })
            
            if self.is_internal_user:
                data['internal'] = 1 if self.internal_release.get() else 0
            
            response = requests.post(f"{CLEARJAV_API_BASE}/torrents/upload", data=data, files=files, timeout=30)
            
            if response.status_code in [200, 201]:
                self.log_message("✓ Torrent uploaded successfully!")
                return True
            else:
                self.log_message(f"✗ Upload failed. Status: {response.status_code}")
                self.log_message(f"Response: {response.text}")
                return False
                
        except requests.RequestException as e:
            self.log_message(f"✗ Upload error: {str(e)}")
            return False

    def show_manual_input_dialog(self, jav_id, dvd_id=None, release_date=None, content_exists=True):
        """Show dialog for manual input of missing data."""
        dialog = ctk.CTkToplevel(self)
        dialog.title("Manual Data Input Required")
        dialog.geometry("400x320")
        dialog.transient(self)
        dialog.grab_set()
        dialog.grid_columnconfigure(1, weight=1)
        
        dvd_var = tk.StringVar(value=dvd_id or "")
        date_var = tk.StringVar(value=release_date or "")
        result = {'dvd_id': None, 'release_date': None, 'cancelled': True}
        
        if content_exists:
            info_text = f"JAV ID: {jav_id}\nFound on R18.dev but missing some data.\nPlease provide the missing information:"
        else:
            info_text = f"JAV ID: {jav_id}\nNot found on R18.dev automatically.\nPlease provide the required information manually:"
        
        info_label = ctk.CTkLabel(dialog, text=info_text, justify="left")
        info_label.grid(row=0, column=0, columnspan=2, padx=20, pady=20, sticky="w")
        
        ctk.CTkLabel(dialog, text="DVD ID:").grid(row=1, column=0, padx=20, pady=10, sticky="w")
        dvd_entry = ctk.CTkEntry(dialog, textvariable=dvd_var, placeholder_text="e.g., SDDE-300")
        dvd_entry.grid(row=1, column=1, padx=20, pady=10, sticky="ew")
        
        ctk.CTkLabel(dialog, text="Release Date:").grid(row=2, column=0, padx=20, pady=10, sticky="w")
        date_entry = ctk.CTkEntry(dialog, textvariable=date_var, placeholder_text="YYYY-MM-DD")
        date_entry.grid(row=2, column=1, padx=20, pady=10, sticky="ew")
        
        def on_ok():
            if dvd_var.get().strip() and date_var.get().strip():
                result['dvd_id'] = dvd_var.get().strip()
                result['release_date'] = date_var.get().strip()
                result['cancelled'] = False
                dialog.destroy()
            else:
                messagebox.showwarning("Missing Data", "Both DVD ID and Release Date are required.")
        
        def on_cancel():
            dialog.destroy()
        
        # Buttons
        button_frame = ctk.CTkFrame(dialog)
        button_frame.grid(row=3, column=0, columnspan=2, pady=20, sticky="ew")
        button_frame.grid_columnconfigure(0, weight=1)
        button_frame.grid_columnconfigure(1, weight=1)
        
        ctk.CTkButton(button_frame, text="OK", command=on_ok).grid(row=0, column=0, padx=10, pady=10)
        ctk.CTkButton(button_frame, text="Cancel", command=on_cancel).grid(row=0, column=1, padx=10, pady=10)
        
        self.center_window(dialog)
        self.wait_window(dialog)
        return result

    def start_generation_thread(self):
        """Starts the file generation process in a separate thread."""
        path = self.input_path.get()
        if not path or path == "Drop File/Folder Here or Click Browse":
            self.status_label.configure(text="Error: Please select a file or folder first.", text_color="red")
            return
        if not self.tracker_url.get():
            self.status_label.configure(text="Error: Announce URL is required.", text_color="red")
            return
        
        # Check API key if auto upload is enabled
        if self.auto_upload.get():
            if not self.api_key.get().strip():
                self.status_label.configure(text="Error: API key required for auto upload.", text_color="red")
                return
            if not self.user_data:
                self.status_label.configure(text="Error: Please validate API key first.", text_color="red")
                return

        self.save_config()
        self.lock_ui_during_processing(True)
        
        self.status_label.configure(text="Processing... Please wait.", text_color="orange")
        
        self.set_progress(0)
        self.log_textbox.configure(state="normal")
        self.log_textbox.delete("1.0", "end")
        self.log_textbox.configure(state="disabled")
        
        if os.path.isdir(path):
            thread = threading.Thread(target=self.run_bulk_generation)
        else:
            thread = threading.Thread(target=self.run_single_generation)
        thread.daemon = True
        thread.start()

    def lock_ui_during_processing(self, lock):
        """Lock/unlock UI elements during processing to prevent changes."""
        state = "disabled" if lock else "normal"
        
        self.generate_button.configure(state=state)
        self.browse_button.configure(state=state)
        self.tracker_entry.configure(state=state)
        self.screenshots_checkbox.configure(state=state)
        self.api_key_entry.configure(state=state)
        self.validate_api_button.configure(state=state)
        
        # Lock filename mode
        if hasattr(self, 'filename_mode_menu'):
            self.filename_mode_menu.configure(state=state)
        
        if lock:
            self.auto_upload_checkbox.configure(state="disabled")
            self.anonymous_checkbox.configure(state="disabled")
            self.personal_release_checkbox.configure(state="disabled")
            self.internal_release_checkbox.configure(state="disabled")
            self.bypass_mod_queue_checkbox.configure(state="disabled")
            self.custom_tag_entry.configure(state="disabled")
        else:
            if self.user_data:
                self.auto_upload_checkbox.configure(state="normal")
                self.toggle_upload_options(self.auto_upload.get())
                self.toggle_internal_options(True)
            else:
                self.auto_upload_checkbox.configure(state="disabled")
                self.toggle_upload_options(False)
                self.toggle_internal_options(False)

    def set_progress(self, value):
        """Updates the progress bar and percentage label."""
        self.progress_bar.set(value)
        self.progress_label.configure(text=f"{int(value * 100)}%")
        self.update_idletasks() # Force UI update

    def finalize_processing(self, success_message="Ready."):
        """Re-enables UI elements after processing is complete."""
        self.lock_ui_during_processing(False)
        self.status_label.configure(text=success_message, text_color="white" if success_message == "Ready." else "green")
        self.input_path.set("Drop File/Folder Here or Click Browse")
        self.path_display_label.configure(text_color="gray60")

    def run_single_generation(self):
        """Wrapper for running generation on a single file."""
        try:
            video_file = self.input_path.get()
            self.log_message(f"Starting processing for: {os.path.basename(video_file)}")
            success = self.process_video_file(video_file, is_bulk=False)
            if success:
                self.log_message("\nProcessing finished successfully.")
                self.finalize_processing(success_message="Success! All files generated.")
            else:
                self.finalize_processing(success_message="Finished with errors.")
        except Exception:
            self.finalize_processing(success_message="An unexpected error occurred.")

    def run_bulk_generation(self):
        """Runs the generation process for all videos in a folder."""
        try:
            folder_path = self.input_path.get()
            video_files = [os.path.join(folder_path, f) for f in os.listdir(folder_path) if f.lower().endswith(VIDEO_EXTENSIONS)]
            
            if not video_files:
                self.status_label.configure(text="No video files found in the selected folder.", text_color="orange")
                self.finalize_processing()
                return

            total_files = len(video_files)
            self.log_message(f"Found {total_files} video files. Starting bulk processing...")
            
            for i, video_file in enumerate(video_files):
                self.status_label.configure(text=f"Processing {i+1}/{total_files}: {os.path.basename(video_file)}", text_color="orange")
                self.log_message(f"\n[{i+1}/{total_files}] Processing: {os.path.basename(video_file)}")
                
                success = self.process_video_file(video_file, is_bulk=True)
                if not success:
                    self.log_message(f"--> SKIPPED: {os.path.basename(video_file)} due to an error.")
                
                self.set_progress((i + 1) / total_files)

            self.log_message("\nBulk processing finished.")
            self.finalize_processing(success_message="Bulk processing complete.")
        except Exception:
            self.finalize_processing(success_message="An unexpected error occurred.")
    
    # --- Processing Methods ---
    
    def get_quick_mediainfo(self, video_file):
        """Gets essential MediaInfo data for torrent title construction."""
        try:
            command = [self.tool_paths['mediainfo'], video_file]
            result = subprocess.run(command, check=True, capture_output=True, text=True, 
                                  encoding='utf-8', errors='ignore', 
                                  creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
            return result.stdout
        except subprocess.CalledProcessError as e:
            raise Exception(f"Failed to get MediaInfo data: {str(e)}")
    
    def extract_resolution_from_text(self, mediainfo_text):
        """Extracts resolution from MediaInfo text."""
        try:
            width_match = re.search(r'Width\s*:\s*([0-9,\s]+)', mediainfo_text)
            height_match = re.search(r'Height\s*:\s*([0-9,\s]+)', mediainfo_text)
            
            if width_match and height_match:
                width = int(width_match.group(1).replace(',', '').replace(' ', ''))
                height = int(height_match.group(1).replace(',', '').replace(' ', ''))
                
                if height >= 2160:
                    return "2160p"
                elif height >= 1080:
                    return "1080p"
                elif height >= 720:
                    return "720p"
                elif height >= 576:
                    return "576p"
                elif height >= 480:
                    return "480p"
                elif height >= 404:
                    return "404p"
                else:
                    return "lower"
            return "1080p"
        except Exception:
            return "1080p"
    
    def extract_video_codec_from_text(self, mediainfo_text):
        """Extracts video codec from MediaInfo text."""
        try:
            video_section = re.search(r'Video[\s\S]*?(?=\n\n|\nAudio|\Z)', mediainfo_text)
            if video_section:
                video_content = video_section.group(0)
                
                # First, check 'Format'
                format_match = re.search(r'Format\s*:\s*([^\n]+)', video_content)
                if format_match:
                    format_name = format_match.group(1).strip()
                    if 'AVC' in format_name or 'H.264' in format_name:
                        return "H.264"
                    elif 'HEVC' in format_name or 'H.265' in format_name:
                        return "H.265"
                    elif 'VP9' in format_name:
                        return "VP9"
                    elif 'MPEG-2' in format_name:
                        return "MPEG-2"
                    elif 'VC-1' in format_name:
                        return "VC-1"
                
                # If 'Format' doesn't give a clear answer, check 'Codec ID'
                codec_match = re.search(r'Codec ID\s*:\s*([^\n]+)', video_content)
                if codec_match:
                    codec = codec_match.group(1).strip().upper()
                    
                    if 'AVC' in codec or 'H264' in codec or 'MPEG4/ISO/AVC' in codec:
                        return "H.264"
                    elif 'HEVC' in codec or 'H265' in codec:
                        return "H.265"
                    elif 'VP9' in codec or 'V_VP9' in codec: # Check for both
                        return "VP9"
                    elif 'MPEG-2' in codec:
                        return "MPEG-2"
                    elif 'VC-1' in codec:
                        return "VC-1"
                        
            # If nothing is found, then fall back
            return "H.264"
        except Exception:
            return "H.264"
    
    def extract_audio_codec_from_text(self, mediainfo_text):
        """Extracts audio codec from MediaInfo text."""
        try:
            audio_section = re.search(r'Audio[\s\S]*?(?=\n\n|\Z)', mediainfo_text)
            if audio_section:
                audio_content = audio_section.group(0)
                format_match = re.search(r'Format\s*:\s*([^\n]+)', audio_content)
                if format_match:
                    format_name = format_match.group(1).strip()
                    if 'AAC' in format_name:
                        return "AAC"
                    elif 'AC-3' in format_name or 'AC3' in format_name:
                        return "DD"
                    elif 'E-AC-3' in format_name or 'EAC3' in format_name:
                        return "DD+"
                    elif 'TrueHD' in format_name:
                        return "TrueHD"
                    elif 'DTS-HD MA' in format_name:
                        return "DTS-HD MA"
                    elif 'DTS' in format_name:
                        return "DTS"
                    elif 'FLAC' in format_name:
                        return "FLAC"
                    elif 'PCM' in format_name or 'LPCM' in format_name:
                        return "LPCM"
                    elif 'Opus' in format_name:
                        return "Opus"
            return "AAC"
        except Exception:
            return "AAC"

    def _get_video_duration(self, video_file):
        """Gets video duration in seconds using ffprobe."""
        try:
            duration_cmd = [self.tool_paths['ffprobe'], "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", video_file]
            duration_result = subprocess.run(duration_cmd, check=True, capture_output=True, text=True, encoding='utf-8', errors='ignore', creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
            return float(duration_result.stdout.strip())
        except (subprocess.CalledProcessError, FileNotFoundError, ValueError) as e:
            self.log_message(f"  - WARNING: Could not determine video duration. Using default settings. Error: {e}")
            return 0

    def _generate_mediainfo(self, video_file, output_path, video_filename):
        """Generates the MediaInfo .txt file."""
        if not os.path.exists(output_path):
            self.log_message("  - Generating MediaInfo file...")
            command = [self.tool_paths['mediainfo'], video_file]
            result = subprocess.run(command, check=True, capture_output=True, text=True, encoding='utf-8', errors='ignore', creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
            
            output_lines = [f"Complete name                            : {video_filename}" if line.startswith("Complete name") else line for line in result.stdout.strip().splitlines()]
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write("\n".join(output_lines))
        else:
            self.log_message("  - MediaInfo file already exists. Skipping.")

    def _generate_contact_sheet(self, video_file, output_path):
        """Generates the contact sheet using mtn, with custom settings for long videos."""
        if not os.path.exists(output_path):
            self.log_message("  - Generating contact sheet...")
            
            duration = self._get_video_duration(video_file)
            is_long_video = duration > 14400 

            if is_long_video:
                self.log_message("    - Long video detected (>4 hours). Using custom settings for contact sheet.")
                mtn_command = [self.tool_paths['mtn'], "-s", "300", "-w", "1024", "-c", "3", "-P", video_file]
            else:
                mtn_command = [self.tool_paths['mtn'], "-P", video_file]
            
            subprocess.run(mtn_command, check=True, capture_output=True, text=True, encoding='utf-8', errors='ignore', creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
        else:
            self.log_message("  - Contact sheet already exists. Skipping.")

    def _generate_screenshots(self, video_file, output_dir):
        """Generates screenshots using ffmpeg."""
        if self.generate_screenshots.get():
            if not os.path.exists(output_dir):
                self.log_message("  - Generating screenshots...")
                os.makedirs(output_dir, exist_ok=True)
                
                duration = self._get_video_duration(video_file)
                if duration == 0:
                    self.log_message("    - Skipping screenshots due to inability to get video duration.")
                    return

                interval = duration / (SCREENSHOT_COUNT + 1)
                for i in range(SCREENSHOT_COUNT):
                    timestamp = interval * (i + 1)
                    output_path = os.path.join(output_dir, f"{i+1}.jpg")
                    ffmpeg_cmd = [self.tool_paths['ffmpeg'], "-ss", str(timestamp), "-i", video_file, "-vf", "scale=-1:1080", "-vframes", "1", "-q:v", str(SCREENSHOT_QUALITY), "-y", output_path]
                    subprocess.run(ffmpeg_cmd, check=True, capture_output=True, text=True, encoding='utf-8', errors='ignore', creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
            else:
                self.log_message("  - Screenshot folder already exists. Skipping.")

    def _create_torrent(self, video_file, output_path):
        """Creates the .torrent file using intermodal."""
        if not os.path.exists(output_path):
            self.log_message("  - Creating .torrent file...")
            tracker = self.tracker_url.get()
            intermodal_cmd = [self.tool_paths[INTERMODAL_EXE], "torrent", "create", "--input", video_file, "--announce", tracker, "--output", output_path, "--private"]
            subprocess.run(intermodal_cmd, check=True, capture_output=True, text=True, encoding='utf-8', errors='ignore', creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
        else:
            self.log_message("  - .torrent file already exists. Skipping.")

    def process_video_file(self, video_file, is_bulk):
        """Core logic for processing a single video file."""
        base_dir = os.path.dirname(video_file)
        video_filename = os.path.basename(video_file)
        video_name_no_ext = os.path.splitext(video_filename)[0]

        try:
            jav_id = video_name_no_ext
            self.log_message(f"  - Content ID: {jav_id}")
            
            dvd_id = None
            release_date = None
            torrent_title = None
            final_video_file = video_file
            
            if self.auto_upload.get() and self.user_data:
                self.log_message("  - Fetching R18.dev data...")
                
                dvd_id, release_date, exists = self.fetch_r18_data(jav_id)
                
                if not exists:
                    if is_bulk:
                        self.log_message(f"  - ❌ SKIPPED: Content ID {jav_id} not available on R18.dev")
                        return False
                    else:
                        self.show_error_window("Content Not Found", 
                                             f"Content ID '{jav_id}' is not available on R18.dev.\n\n"
                                             f"This content cannot be uploaded to ClearJAV as it requires R18.dev metadata.\n"
                                             f"Please verify the content ID is correct.")
                        return False
                
                if not dvd_id or not release_date:
                    missing_fields = []
                    if not dvd_id:
                        missing_fields.append("DVD ID")
                    if not release_date:
                        missing_fields.append("Release Date")
                    
                    self.log_message(f"  - Missing {', '.join(missing_fields)} from R18.dev, requesting manual input...")
                    result = self.show_manual_input_dialog(jav_id, dvd_id, release_date, content_exists=True)
                    if result['cancelled']:
                        self.log_message("  - Processing cancelled by user")
                        return False
                    dvd_id = result['dvd_id']
                    release_date = result['release_date']
                
                self.log_message(f"  - DVD ID: {dvd_id}")
                self.log_message(f"  - Release Date: {release_date}")
                
                self.log_message(f"  - Checking for existing torrents with DVD ID: {dvd_id}")
                duplicates = self.check_for_duplicates(dvd_id)
                
                if duplicates:
                    self.log_message(f"  - Found {len(duplicates)} existing torrent(s) with same DVD ID")
                    
                    if not self.show_duplicate_confirmation_dialog(dvd_id, duplicates):
                        self.log_message("  - Upload cancelled due to duplicates")
                        return False
                    else:
                        self.log_message("  - User chose to proceed despite duplicates")
                else:
                    self.log_message("  - No duplicates found, safe to proceed")
                
                self.log_message("  - Scanning MediaInfo for torrent title...")
                try:
                    mediainfo_text = self.get_quick_mediainfo(video_file)
                    resolution = self.extract_resolution_from_text(mediainfo_text)
                    video_codec = self.extract_video_codec_from_text(mediainfo_text)
                    audio_codec = self.extract_audio_codec_from_text(mediainfo_text)
                    
                    is_internal = self.internal_release.get() if self.is_internal_user else False
                    is_personal = self.personal_release.get()
                    custom_tag = self.custom_tag.get().strip() if is_personal else ""
                    
                    torrent_title = self.construct_torrent_title(
                        dvd_id, release_date, resolution, video_codec, audio_codec,
                        is_internal, is_personal, custom_tag
                    )
                    
                    self.log_message(f"  - Generated Torrent Title: {torrent_title}")
                    
                except Exception as e:
                    self.log_message(f"  - Error getting MediaInfo for title: {str(e)}")
                    return False
                
                # Handle file renaming based on filename mode
                filename_mode = self.filename_mode.get()
                if filename_mode != "content_id":
                    self.log_message(f"  - Renaming file based on mode: {filename_mode}")
                    
                    if filename_mode == "dvd_id":
                        new_name = dvd_id
                    elif filename_mode == "torrent_title":
                        new_name = torrent_title
                    else:
                        new_name = jav_id
                    
                    file_ext = os.path.splitext(video_file)[1]
                    new_video_path = os.path.join(base_dir, f"{new_name}{file_ext}")
                    
                    if new_video_path != video_file:
                        try:
                            os.rename(video_file, new_video_path)
                            final_video_file = new_video_path
                            self.log_message(f"  - Renamed file to: {os.path.basename(new_video_path)}")
                            
                            video_filename = os.path.basename(final_video_file)
                            video_name_no_ext = os.path.splitext(video_filename)[0]
                        except OSError as e:
                            self.log_message(f"  - Warning: Could not rename file: {str(e)}")
            
            mediainfo_txt_path = os.path.join(base_dir, f"{video_name_no_ext}.txt")
            contact_sheet_path = os.path.join(base_dir, f"{video_name_no_ext}_s.jpg")
            screenshot_dir = os.path.join(base_dir, video_name_no_ext)
            torrent_path = os.path.join(base_dir, f"{video_name_no_ext}.torrent")

            self._generate_mediainfo(final_video_file, mediainfo_txt_path, video_filename)
            if not is_bulk: self.set_progress(0.2)

            self._generate_contact_sheet(final_video_file, contact_sheet_path)
            if not is_bulk: self.set_progress(0.4)

            self._generate_screenshots(final_video_file, screenshot_dir)
            if not is_bulk: self.set_progress(0.6)

            self._create_torrent(final_video_file, torrent_path)
            if not is_bulk: self.set_progress(0.8)

            if self.auto_upload.get() and self.user_data:
                self.log_message("  - Starting automatic upload...")
                with open(mediainfo_txt_path, 'r', encoding='utf-8') as f:
                    mediainfo_content = f.read()
                
                # Prepare upload data
                torrent_data = {
                    'jav_id': jav_id,
                    'dvd_id': dvd_id,
                    'title': torrent_title,
                    'description': f"https://r18.dev/videos/vod/movies/detail/-/id={jav_id}/",
                    'mediainfo': mediainfo_content,
                    'resolution_id': RESOLUTION_MAPPINGS.get(resolution, 3),  # Default to 1080p
                    'torrent_path': torrent_path,
                    'contact_sheet_path': contact_sheet_path if os.path.exists(contact_sheet_path) else None
                }
                
                upload_success = self.upload_torrent_to_api(torrent_data)
                if upload_success:
                    self.log_message(f"--> SUCCESS: {video_filename} (uploaded)")
                else:
                    self.log_message(f"--> SUCCESS: {video_filename} (metadata only - upload failed)")

            else:
                self.log_message(f"--> SUCCESS: {video_filename}")
            
            if not is_bulk: self.set_progress(1.0)
            return True

        except (FileNotFoundError, subprocess.CalledProcessError, Exception) as e:
            error_title = "Processing Error"
            error_details = ""
            if isinstance(e, FileNotFoundError):
                error_title = "Tool Not Found"
                error_details = f"The command '{e.filename}' was not found."
            elif isinstance(e, subprocess.CalledProcessError):
                error_details = (
                    f"Command:\n{' '.join(e.cmd)}\n\n"
                    f"Return Code: {e.returncode}\n\n"
                    f"--- STDOUT ---\n{e.stdout or 'No output'}\n\n"
                    f"--- STDERR ---\n{e.stderr or 'No output'}"
                )
            else:
                error_title = "Unexpected Error"
                error_details = f"An unexpected error occurred.\n\n--- Traceback ---\n{traceback.format_exc()}"
            
            self.show_error_window(error_title, error_details)
            if not is_bulk: self.set_progress(0)
            return False

if __name__ == "__main__":
    app = VideoProcessorApp()
    app.mainloop()
