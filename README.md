# Torrent Metadata Creator

A user-friendly graphical interface (GUI) for generating metadata files for video content, preparing it for sharing as a torrent.

This application streamlines the process of creating a `.torrent` file, generating a `mediainfo` text file, creating a contact sheet (thumbnail grid), and extracting a gallery of screenshots from video files. It can process a single video file or an entire folder containing multiple videos in bulk.

## Features

- **Graphical User Interface:** Easy-to-use interface built with CustomTkinter.
- **Drag and Drop:** Simply drag your video file or folder onto the application window.
- **Single or Bulk Processing:** Process one video file or a whole directory at once.
- **Dependency Checker:** Automatically checks for required command-line tools on startup and provides download links if they are missing.
- **Torrent File Creation:** Generates a `.torrent` file with your specified announcer URL.
- **MediaInfo Generation:** Creates a detailed text file with the video's technical specifications.
- **Contact Sheet:** Generates a single image file with a grid of thumbnails from the video.
- **Screenshot Gallery:** Extracts a configurable number of high-quality screenshots and saves them in a dedicated folder.
- **Configuration Saving:** Remembers your tracker URL and screenshot preference between sessions.
- **Cross-Platform:** Should work on Windows, macOS, and Linux (provided the dependencies are installed).

## Prerequisites

This application relies on several external command-line tools that must be installed and accessible in your system's PATH, or placed in the same directory as the script. The application will check for these on launch.

- **FFmpeg & FFprobe:** For processing video files and generating screenshots.
  - [Download FFmpeg](https://ffmpeg.org/download.html)
- **MediaInfo:** For generating technical information about the video file.
  - [Download MediaInfo](https://mediaarea.net/en/MediaInfo/Download)
- **mtn (Movie Thumbnailer):** For creating the contact sheet.
  - [Download mtn](https://www.videohelp.com/software/movie-thumbnailer)
- **Intermodal:** For creating the `.torrent` file.
  - [Download Intermodal](https://github.com/casey/intermodal/releases/)

## How to Use

1. **Install Dependencies:** Make sure you have all the prerequisite tools listed above installed. Then, install the required Python libraries:
   ```bash
   pip install -r requirements.txt
   ```
2. **Run the Application:** Execute the Python script.
   ```bash
   python torrent-metadata-creator.py
   ```
3. **Dependency Check:** The application will first check if all required tools are found. If any are missing, it will provide links to download them.
4. **Select Input:**
   - **Drag and Drop:** Drag a single video file (`.mp4`, `.mkv`, etc.) or a folder containing video files directly onto the application window.
   - **Browse:** Click the "Browse..." button to select a file or folder manually.
5. **Set Options:**
   - Enter your tracker's **Announce URL**. This is required to create the `.torrent` file.
   - Check or uncheck the "Generate 15 Screenshots" box as needed.
6. **Generate Files:** Click the "Generate Files" button.
7. **Monitor Progress:** The application will display the current status and a log of its actions. The progress bar will show the overall progress.
8. **Find Your Files:** The generated files (`.torrent`, `.txt`, contact sheet, and screenshot folder) will be saved in the same directory as the original video file(s).

## Windows executable

I've compiled the script into a portable .exe file for all Windows users, you can find it on the Releases tab on the Github.

## Python Dependencies

The script requires the following Python libraries:

- `customtkinter`: For the modern user interface elements.
- `tkinterdnd2`: To enable drag-and-drop functionality.

You can install them using the provided `requirements.txt` file.
