import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog
import subprocess
import threading
import os
import shutil
import webbrowser
import traceback
import configparser
import sys
from tkinterdnd2 import DND_FILES, TkinterDnD

# --- Configuration ---
CONFIG_FILE = "settings.ini"
VIDEO_EXTENSIONS = ('.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv')
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

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

# The main application class now inherits from TkinterDnD.Tk to be the root window
# and have drag-and-drop capabilities from the start.
class VideoProcessorApp(TkinterDnD.Tk):
    def __init__(self):
        super().__init__()

        # --- Main Window Setup ---
        # Keep the root window hidden until it's fully configured and centered
        self.withdraw()

        # Apply CustomTkinter theme to the DnD-aware root window
        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("blue")
        # Manually set the background color of the root window to match the dark theme
        self.config(bg=ctk.ThemeManager.theme["CTk"]["fg_color"][1])

        self.title("Torrent Metadata Creator")
        self.geometry("800x800")
        
        # Set the application icon.
        try:
            icon_path = resource_path("cj.ico")
            self.iconbitmap(icon_path)
        except tk.TclError:
            print("Warning: cj.ico not found. Using default icon.")

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1) # Adjusted row configuration

        self.input_path = tk.StringVar()
        self.tracker_url = tk.StringVar()
        self.generate_screenshots = tk.BooleanVar()
        self.tool_paths = {} # To store the found paths of required tools

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
            self.generate_screenshots.set(config.getboolean('Settings', 'GenerateScreenshots', fallback=True))
        else:
            self.generate_screenshots.set(True)

    def save_config(self):
        """Save current settings to the .ini file."""
        config = configparser.ConfigParser()
        config['Settings'] = {
            'TrackerURL': self.tracker_url.get(),
            'GenerateScreenshots': str(self.generate_screenshots.get())
        }
        with open(CONFIG_FILE, 'w') as configfile:
            config.write(configfile)

    def check_dependencies(self):
        """Creates a popup window to check for required command-line tools.
        Prioritizes tools in the local script directory."""
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
            # --- Smarter Check: Prioritize local directory ---
            # On Windows, explicitly check for .exe
            if os.name == 'nt':
                local_path_exe = os.path.join(base_path, f"{tool}.exe")
                if os.path.exists(local_path_exe):
                    found_path = local_path_exe
            
            # Check for the tool without extension (for non-Windows or if no .exe on Win)
            if not found_path:
                local_path = os.path.join(base_path, tool)
                if os.path.exists(local_path):
                    found_path = local_path

            # If not found locally, fall back to system PATH
            if not found_path:
                found_path = shutil.which(tool)
            # --- End Smarter Check ---

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
        """Creates the main UI components."""
        # --- Frame 1: Unified Input Area (Drag & Drop, Click to Browse) ---
        input_container_frame = ctk.CTkFrame(self)
        input_container_frame.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        input_container_frame.grid_columnconfigure(0, weight=1)
        
        # Create a dedicated frame for the drop zone
        self.drop_zone = ctk.CTkFrame(input_container_frame, height=100, border_width=2, border_color="gray50")
        self.drop_zone.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        self.drop_zone.grid_columnconfigure(0, weight=1)
        self.drop_zone.grid_rowconfigure(0, weight=1)

        # Label to display instructions and the selected path
        self.path_display_label = ctk.CTkLabel(self.drop_zone, textvariable=self.input_path, text_color="gray60")
        self.path_display_label.grid(row=0, column=0, padx=10, pady=10)

        # Browse button, now smaller and inside the drop zone
        self.browse_button = ctk.CTkButton(self.drop_zone, text="Browse...", command=self.browse_path, width=120)
        self.browse_button.grid(row=1, column=0, pady=(0, 10))
        
        # Register the drop zone and its label as drop targets
        self.drop_zone.drop_target_register(DND_FILES)
        self.path_display_label.drop_target_register(DND_FILES)
        self.drop_zone.dnd_bind('<<Drop>>', self.handle_drop)
        self.path_display_label.dnd_bind('<<Drop>>', self.handle_drop)
        
        self.input_path.set("Drop File/Folder Here or Click Browse")

        # --- Frame 2: Options ---
        options_frame = ctk.CTkFrame(self)
        options_frame.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="ew")
        options_frame.grid_columnconfigure(1, weight=1)

        self.screenshots_checkbox = ctk.CTkCheckBox(options_frame, text="Generate 15 Screenshots for the Gallery", variable=self.generate_screenshots)
        self.screenshots_checkbox.grid(row=0, column=0, columnspan=3, padx=10, pady=10)
        ctk.CTkLabel(options_frame, text="Announce URL:").grid(row=1, column=0, padx=10, pady=10)
        self.tracker_entry = ctk.CTkEntry(options_frame, textvariable=self.tracker_url, placeholder_text="Required for .torrent creation")
        self.tracker_entry.grid(row=1, column=1, columnspan=2, padx=10, pady=10, sticky="ew")

        # --- Frame 3: Log Output ---
        log_frame = ctk.CTkFrame(self)
        log_frame.grid(row=2, column=0, padx=10, pady=(0, 10), sticky="nsew")
        log_frame.grid_rowconfigure(1, weight=1)
        log_frame.grid_columnconfigure(0, weight=1)
        
        ctk.CTkLabel(log_frame, text="Processing Log", font=ctk.CTkFont(size=14, weight="bold")).grid(row=0, column=0, padx=10, pady=10)
        self.log_textbox = ctk.CTkTextbox(log_frame, wrap="word")
        self.log_textbox.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="nsew")
        self.log_textbox.configure(state="disabled")

        # --- Frame 4: Action and Progress ---
        action_frame = ctk.CTkFrame(self)
        action_frame.grid(row=3, column=0, padx=10, pady=10, sticky="ew")
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
        
    def handle_drop(self, event):
        """Handles the file/folder drop event."""
        path = self.tk.splitlist(event.data)[0]
        if os.path.isdir(path) or (os.path.isfile(path) and path.lower().endswith(VIDEO_EXTENSIONS)):
            self.input_path.set(path)
            self.path_display_label.configure(text_color="white") # Restore text color on valid drop
        else:
            self.status_label.configure(text="Error: Dropped item is not a valid video file or folder.", text_color="red")
            self.input_path.set("Drop File/Folder Here or Click Browse")
            self.path_display_label.configure(text_color="gray60") # Reset to placeholder color

    def show_error_window(self, title, message):
        """Creates a popup window to display detailed error messages."""
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
        """Appends a message to the log textbox."""
        self.log_textbox.configure(state="normal")
        self.log_textbox.insert("end", message + "\n")
        self.log_textbox.see("end")
        self.log_textbox.configure(state="disabled")

    def browse_path(self):
        """Opens a selection dialog to choose between file or folder."""
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

    def start_generation_thread(self):
        """Starts the file generation process in a separate thread."""
        path = self.input_path.get()
        if not path or path == "Drop File/Folder Here or Click Browse":
            self.status_label.configure(text="Error: Please select a file or folder first.", text_color="red")
            return
        if not self.tracker_url.get():
            self.status_label.configure(text="Error: Announce URL is required.", text_color="red")
            return

        self.save_config()
        # Lock UI elements
        self.generate_button.configure(state="disabled")
        self.browse_button.configure(state="disabled")
        self.tracker_entry.configure(state="disabled")
        self.screenshots_checkbox.configure(state="disabled")
        
        # Update status message
        self.status_label.configure(text="Processing... Please wait.", text_color="orange")
        
        self.set_progress(0)
        self.log_textbox.configure(state="normal")
        self.log_textbox.delete("1.0", "end")
        self.log_textbox.configure(state="disabled")
        
        # Determine mode and start the appropriate processing function
        if os.path.isdir(path):
            thread = threading.Thread(target=self.run_bulk_generation)
        else:
            thread = threading.Thread(target=self.run_single_generation)
        thread.daemon = True
        thread.start()

    def set_progress(self, value):
        """Updates the progress bar and percentage label."""
        self.progress_bar.set(value)
        self.progress_label.configure(text=f"{int(value * 100)}%")
        self.update_idletasks() # Force UI update

    def finalize_processing(self, success_message="Ready."):
        """Re-enables UI elements after processing is complete."""
        self.generate_button.configure(state="normal")
        self.browse_button.configure(state="normal")
        self.tracker_entry.configure(state="normal")
        self.screenshots_checkbox.configure(state="normal")
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

    def _get_video_duration(self, video_file):
        """Gets video duration in seconds using ffprobe."""
        try:
            duration_cmd = [self.tool_paths['ffprobe'], "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", video_file]
            duration_result = subprocess.run(duration_cmd, check=True, capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
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
            
            # Replace the generic "Complete name" with the actual filename
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
            # 4 hours = 14400 seconds
            is_long_video = duration > 14400 

            if is_long_video:
                self.log_message("    - Long video detected (>4 hours). Using custom settings for contact sheet.")
                # For long videos, take a screenshot every 5 minutes (300s) to keep the sheet manageable.
                # -s 300: interval of 300 seconds
                # -w 1024: width of 1024px
                # -c 3: 3 columns
                # -P: automatically save output next to the input file
                mtn_command = [self.tool_paths['mtn'], "-s", "300", "-w", "1024", "-c", "3", "-P", video_file]
            else:
                # The -P flag automatically saves the output next to the input file using default settings.
                mtn_command = [self.tool_paths['mtn'], "-P", video_file]
            
            subprocess.run(mtn_command, check=True, capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
        else:
            self.log_message("  - Contact sheet already exists. Skipping.")

    def _generate_screenshots(self, video_file, output_dir):
        """Generates screenshots using ffmpeg."""
        if self.generate_screenshots.get():
            if not os.path.exists(output_dir):
                self.log_message("  - Generating screenshots...")
                os.makedirs(output_dir, exist_ok=True)
                
                # Get video duration to calculate screenshot intervals
                duration = self._get_video_duration(video_file)
                if duration == 0:
                    self.log_message("    - Skipping screenshots due to inability to get video duration.")
                    return

                # Use the fast, seek-based loop method.
                interval = duration / (SCREENSHOT_COUNT + 1)
                for i in range(SCREENSHOT_COUNT):
                    timestamp = interval * (i + 1)
                    output_path = os.path.join(output_dir, f"{i+1}.jpg")
                    ffmpeg_cmd = [self.tool_paths['ffmpeg'], "-ss", str(timestamp), "-i", video_file, "-vf", "scale=-1:1080", "-vframes", "1", "-q:v", str(SCREENSHOT_QUALITY), "-y", output_path]
                    subprocess.run(ffmpeg_cmd, check=True, capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
            else:
                self.log_message("  - Screenshot folder already exists. Skipping.")

    def _create_torrent(self, video_file, output_path):
        """Creates the .torrent file using intermodal."""
        if not os.path.exists(output_path):
            self.log_message("  - Creating .torrent file...")
            tracker = self.tracker_url.get()
            intermodal_cmd = [self.tool_paths[INTERMODAL_EXE], "torrent", "create", "--input", video_file, "--announce", tracker, "--output", output_path, "--private"]
            subprocess.run(intermodal_cmd, check=True, capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
        else:
            self.log_message("  - .torrent file already exists. Skipping.")

    def process_video_file(self, video_file, is_bulk):
        """The core logic for running external tools on a single video file."""
        base_dir = os.path.dirname(video_file)
        video_filename = os.path.basename(video_file)
        video_name_no_ext = os.path.splitext(video_filename)[0]

        # Define all output paths
        mediainfo_txt_path = os.path.join(base_dir, f"{video_name_no_ext}.txt")
        # BUG FIX: MTN appends "_s" to the filename for the contact sheet.
        contact_sheet_path = os.path.join(base_dir, f"{video_name_no_ext}_s.jpg")
        screenshot_dir = os.path.join(base_dir, video_name_no_ext)
        torrent_path = os.path.join(base_dir, f"{video_name_no_ext}.torrent")

        try:
            # Task 1: Generate MediaInfo
            self._generate_mediainfo(video_file, mediainfo_txt_path, video_filename)
            if not is_bulk: self.set_progress(0.25)

            # Task 2: Generate Contact Sheet
            self._generate_contact_sheet(video_file, contact_sheet_path)
            if not is_bulk: self.set_progress(0.5)

            # Task 3: Generate Screenshots
            self._generate_screenshots(video_file, screenshot_dir)
            if not is_bulk: self.set_progress(0.75)

            # Task 4: Create .torrent file
            self._create_torrent(video_file, torrent_path)
            if not is_bulk: self.set_progress(1.0)

            self.log_message(f"--> SUCCESS: {video_filename}")
            return True

        except (FileNotFoundError, subprocess.CalledProcessError, Exception) as e:
            error_title = "Processing Error"
            error_details = ""
            if isinstance(e, FileNotFoundError):
                error_title = "Tool Not Found"
                error_details = f"The command '{e.filename}' was not found."
            elif isinstance(e, subprocess.CalledProcessError):
                # IMPROVED ERROR HANDLING: Include both stdout and stderr for better debugging.
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
    # The main app instance is now the root window, which resolves the DnD issue.
    app = VideoProcessorApp()
    app.mainloop()