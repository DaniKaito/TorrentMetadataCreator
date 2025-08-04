# Torrent Metadata Creator with ClearJAV API Uploads

A user-friendly graphical interface (GUI) for generating metadata files for video content and automatically uploading to ClearJAV with intelligent content detection and API integration.

This application streamlines the process of creating a `.torrent` file, generating a `mediainfo` text file, creating a contact sheet (thumbnail grid), and extracting a gallery of screenshots from video files. It can process a single video file or an entire folder containing multiple videos in bulk now with specialized support for ClearJAV API integration.

## Features

### Core Functionality
- **Modern GUI Interface:** Clean, intuitive interface built with CustomTkinter
- **Drag & Drop Support:** Simply drag video files or folders onto the application
- **Batch Processing:** Process single files or entire directories efficiently
- **Auto-Dependency Detection:** Automatically checks and guides installation of required tools

### Metadata Generation
- **Torrent File Creation:** Generates optimized `.torrent` files with custom announce URLs
- **MediaInfo Reports:** Creates detailed technical specification files
- **Contact Sheets:** Generates professional thumbnail grid previews
- **Screenshot Galleries:** Extracts high-quality screenshots with customizable counts
- **Smart File Naming:** Intelligent naming based on content detection

### API Integration & Auto-Upload
- **ClearJAV API Integration:** Full API support with automatic torrent uploads
- **R18.dev Content Validation:** Cross-references content against R18.dev database
- **Duplicate Detection:** Automatically checks for existing content before upload
- **API Key Validation:** Real-time validation of API credentials
- **Anonymous Upload Support:** Optional anonymous posting capabilities

### Content Intelligence
- **JAV Content Recognition:** Automatic detection and parsing of JAV content IDs
- **Metadata Enrichment:** Fetches additional content data from external APIs  
- **Resolution Detection:** Automatically determines and maps video resolutions

### Advanced Options
- **Configuration Persistence:** Saves all settings between sessions
- **Progress Tracking:** Real-time progress monitoring with detailed logs
- **Error Handling:** Comprehensive error reporting and recovery
- **Cross-Platform:** Windows, macOS, and Linux support

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
   - **Drag and Drop:** Drag a single video file (`.mp4`, `.mkv`, `.wmv`) or a folder containing video files directly onto the application window.
   - **Browse:** Click the "Browse..." button to select a file or folder manually.
5. **Set Options:**
   - Enter your tracker's **Announce URL**. This is required to create the `.torrent` file.
   - Check or uncheck the "Generate 15 Screenshots" box (needed for manual uploads or when the gallery images are missing from r18.dev)
   - Insert API Key and press Validate button(you can generate an API Key from your Profile > Settings > API Keys)
   - *Optional* Select the video file title you prefer (from Content ID - DVD ID - Torrent Title)
   - *Optional* Check Anonymous (if you don't want to display your name in the release)
   - *Optional* Check Personal Release (if you ripped the video yourself and want to add a custom -TAG name at the end of the torrent title)
   - *Optional* Insert a Tag Name, usually your username or release group.
   - Internal and Bypass Mod. Queue are reserved to Intrnal/Mod members.
6. **r18.dev Validation:** Before the script starts generating files, if you choose to upload them automatically, it will first verify if the content id exist on r18.dev check the DVD-ID and Release date (if any of them are missing you need to insert them manually in a dialoge window that will appear).
7. **Generate Files:** Click the "Generate Files" button.
8. **Monitor Progress:** The application will display the current status and a log of its actions. The progress bar will show the overall progress.
9. **Duplicate Detection:** In case the DVD-ID already exist on the website the script will open a pop up asking if you want to proceed uploading that file or skip it, usually you can upload a "duplicate" when yours have a better quality.
10. **Automatic Upload:** After all the checks are passed and the files have been generated, it will proceed to send an API Request to automatic upload the torrent to the website, you will need to download the .torrent generated by the website and seed that torrent.

## Windows executable

I've compiled the script into a portable .exe file for all Windows users, you can find it on the Releases tab on the Github.
Alternatively you can compile it yourself:
To compile your own executable:
```bash
# Install PyInstaller
pip install pyinstaller

# Create executable  
pyinstaller --onefile --windowed --name "Torrent Metadata Creator" --icon="cj.ico" --add-data "cj.ico;." torrent-metadata-creator.py
```

## Python Dependencies

The script requires the following Python libraries:

- `customtkinter`: For the modern user interface elements.
- `tkinterdnd2`: To enable drag-and-drop functionality.
- `requests` - API communications

You can install them using the provided `requirements.txt` file.
