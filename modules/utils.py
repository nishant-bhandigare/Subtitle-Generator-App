import os
import subprocess
import streamlit as st
import time

# Define available Vosk models with their sizes and download URLs
VOSK_MODELS = {
    "small-en": {
        "name": "Small English Model (40MB)",
        "url": "https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip",
        "folder": "vosk-model-small-en-us-0.15",
        "size": "40MB",
        "description": "Lightweight wideband model for Android and RPi"
    },
    "medium-en": {
        "name": "Medium English Model (1.8GB)",
        "url": "https://alphacephei.com/vosk/models/vosk-model-en-us-0.22.zip",
        "folder": "vosk-model-en-us-0.22",
        "size": "1.8GB",
        "description": "Accurate generic US English model"
    },
    "large-en": {
        "name": "Large English Model (2.3GB)",
        "url": "https://alphacephei.com/vosk/models/vosk-model-en-us-0.42-gigaspeech.zip",
        "folder": "vosk-model-en-us-0.42",
        "size": "2.3GB",
        "description": "Accurate generic US English model trained by Kaldi on Gigaspeech. Mostly for podcasts, not for telephony"
    },
    "small-in": {
        "name": "Small Indian English Model (36GB)",
        "url": "https://alphacephei.com/vosk/models/vosk-model-small-en-in-0.4.zip",
        "folder": "vosk-model-small-en-in-0.4",
        "size": "36B",
        "description": "Lightweight Indian English model for mobile applications"
    },
    "medium-in": {
        "name": "Medium Indian English Model (1GB)",
        "url": "https://alphacephei.com/vosk/models/vosk-model-en-in-0.5.zip",
        "folder": "vosk-model-en-in-0.5",
        "size": "1GB",
        "description": "Generic Indian English model for telecom and broadcast"
    }
}

def check_dependencies():
    """Check if required dependencies are installed"""
    try:
        import vosk
        # Check if FFmpeg is installed
        subprocess.run(["ffmpeg", "-version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return True
    except ImportError:
        st.error("Error: Vosk library not found. Please install it using 'pip install vosk'")
        return False
    except FileNotFoundError:
        st.error("Error: FFmpeg not found. Please install FFmpeg and make sure it's in your PATH.")
        return False

def download_model(model_key, progress_bar=None):
    """Download the selected Vosk model if it doesn't exist"""
    model_info = VOSK_MODELS[model_key]
    model_dir = os.path.join("models", model_key)
    
    if not os.path.exists(model_dir):
        import urllib.request
        import zipfile
        
        # Create model directory
        os.makedirs(model_dir, exist_ok=True)
        
        # Prepare for download
        model_url = model_info["url"]
        zip_path = f"{model_key}-model.zip"
        
        # Download with progress indicator
        with st.spinner(f"Downloading {model_info['name']}... This may take a while."):
            def report_progress(count, block_size, total_size):
                if progress_bar is not None:
                    progress_bar.progress(min(count * block_size / total_size, 1.0))
            
            urllib.request.urlretrieve(model_url, zip_path, reporthook=report_progress)
            
            # Extract the model
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(".")
            
            # Rename the extracted folder
            extracted_folder = model_info["folder"]
            if os.path.exists(extracted_folder):
                # If model directory already exists, remove it
                if os.path.exists(model_dir):
                    import shutil
                    shutil.rmtree(model_dir)
                # Rename the extracted folder
                os.rename(extracted_folder, model_dir)
            
            # Clean up
            if os.path.exists(zip_path):
                os.remove(zip_path)
            
            st.success(f"Model {model_info['name']} downloaded successfully!")
    
    return model_dir

def format_time(seconds):
    """Format time in SRT format (HH:MM:SS,mmm)"""
    hours = int(seconds / 3600)
    seconds %= 3600
    minutes = int(seconds / 60)
    seconds %= 60
    milliseconds = int((seconds - int(seconds)) * 1000)
    seconds = int(seconds)
    
    # Ensure we're using commas, not periods, for milliseconds (SRT standard)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"

def extract_audio(video_path, output_path):
    """Extract audio from video file"""
    # Define the FFmpeg command
    ffmpeg_cmd = [
        "ffmpeg",
        "-i", video_path,        # Input file
        "-ar", "16000",          # Sample rate (required by Vosk)
        "-ac", "1",              # Mono audio
        "-f", "wav",             # Output format
        output_path,             # Output file
        "-y"                     # Overwrite if exists
    ]
    
    # Run the command
    subprocess.run(ffmpeg_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    return output_path

def burn_subtitles_into_video(video_path, srt_path, output_path):
    """Burn the subtitles into the video file"""
    # Normalize paths to avoid issues with backslashes
    video_path = os.path.normpath(video_path)
    srt_path = os.path.normpath(srt_path)
    output_path = os.path.normpath(output_path)
    
    # Import platform here to avoid any module import issues
    import platform
    
    try:
        # First attempt: standard method with escaped path
        if platform.system() == 'Windows':
            # On Windows, need to handle path escaping differently
            # Fix: Use double backslashes for escaping in f-strings
            escaped_path = srt_path.replace(':', '\\\\:')
            ffmpeg_cmd = [
                "ffmpeg",
                "-i", video_path,
                "-vf", f"subtitles={escaped_path}",
                "-c:a", "copy",
                output_path,
                "-y"
            ]
        else:
            # On Unix-like systems
            ffmpeg_cmd = [
                "ffmpeg",
                "-i", video_path,
                "-vf", f"subtitles='{srt_path}'",
                "-c:a", "copy",
                output_path,
                "-y"
            ]
        
        # Print the command for debugging
        print(f"Running FFmpeg command: {' '.join(ffmpeg_cmd)}")
        
        subprocess.run(
            ffmpeg_cmd, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE,
            text=True,
            check=True
        )
        
        # Check if output file was created and has a non-zero size
        if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
            raise FileNotFoundError(f"Output file was not created properly: {output_path}")
        
        return output_path
    
    except Exception as e:
        print(f"First attempt failed: {str(e)}")
        
        try:
            # Second attempt: using a simpler method with movtext
            alt_cmd = [
                "ffmpeg",
                "-i", video_path,
                "-f", "srt",
                "-i", srt_path,
                "-map", "0:v",
                "-map", "0:a",
                "-map", "1",
                "-c:v", "copy",
                "-c:a", "copy",
                "-c:s", "mov_text",
                output_path,
                "-y"
            ]
            
            print(f"Running alternative FFmpeg command: {' '.join(alt_cmd)}")
            
            subprocess.run(alt_cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
                raise FileNotFoundError(f"Output file was not created properly: {output_path}")
            
            return output_path
        
        except Exception as e2:
            print(f"Second attempt failed: {str(e2)}")
            
            try:
                # Third attempt: hardcoded style without quotes in the path
                hardcode_cmd = [
                    "ffmpeg",
                    "-i", video_path,
                    "-vf", f"subtitles={srt_path}:force_style='FontSize=24,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BackColour=&H80000000,BorderStyle=4'",
                    "-c:a", "copy",
                    output_path,
                    "-y"
                ]
                
                print(f"Running hardcoded FFmpeg command: {' '.join(hardcode_cmd)}")
                
                subprocess.run(hardcode_cmd, check=True)
                
                if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
                    raise FileNotFoundError(f"Output file was not created properly: {output_path}")
                
                return output_path
            
            except Exception as e3:
                # If all attempts failed, return the original video path and log the errors
                print(f"All subtitle burning attempts failed. Errors: {str(e)}, {str(e2)}, {str(e3)}")
                raise RuntimeError(f"Failed to burn subtitles after multiple attempts. Check FFmpeg installation and file paths.")

def get_video_duration(video_path):
    """Get duration of a video file in seconds using FFmpeg"""
    cmd = [
        "ffprobe", 
        "-v", "error", 
        "-show_entries", "format=duration", 
        "-of", "default=noprint_wrappers=1:nokey=1", 
        video_path
    ]
    
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    
    try:
        duration = float(result.stdout.strip())
        return duration
    except (ValueError, TypeError):
        return 0

def display_dynamic_subtitles(result, original_video_path):
    """Display video with dynamic subtitles overlay - simplified approach"""
    # Make sure we have segments
    if "segments" not in result or not result["segments"]:
        st.warning("No subtitle segments found. Dynamic subtitles cannot be displayed.")
        return
    
    segments = result["segments"]
    
    # Display the original video
    st.video(original_video_path)
    
    # Add a section for viewing subtitles
    st.subheader("Dynamic Subtitles Viewer")
    st.info("Use the slider below to view subtitles at different points in the video.")
    
    # Get the maximum time from segments
    max_time = max(segment["end"] for segment in segments) + 1
    
    # Create a slider for navigating through the video
    current_time = st.slider("Video Position (seconds)", 0.0, max_time, 0.0, 0.1)
    
    # Find the current subtitle text based on time
    current_subtitle = "No subtitle at this time position."
    for segment in segments:
        if segment["start"] <= current_time <= segment["end"]:
            current_subtitle = segment["text"]
            break
    
    # Style options
    col1, col2, col3 = st.columns(3)
    with col1:
        font_size = st.select_slider("Font Size", options=[14, 16, 18, 20, 22, 24, 26, 28, 30], value=20)
    with col2:
        bg_opacity = st.select_slider("Background Opacity", options=[0.0, 0.3, 0.5, 0.7, 0.9, 1.0], value=0.7)
    with col3:
        text_color = st.selectbox("Text Color", options=["white", "yellow", "cyan"], index=0)
    
    # Display the current subtitle with styling
    st.markdown(
        f"""
        <div style="
            background-color: rgba(0,0,0,{bg_opacity}); 
            color: {text_color}; 
            padding: 15px; 
            border-radius: 5px; 
            text-align: center; 
            font-size: {font_size}px;
            margin-top: 10px;
            font-weight: 500;
        ">{current_subtitle}</div>
        """,
        unsafe_allow_html=True
    )
    
    # Add a section to display the full transcript
    with st.expander("Show Full Transcript"):
        for i, segment in enumerate(segments):
            start_time = format_time(segment["start"]).replace(',', '.')
            end_time = format_time(segment["end"]).replace(',', '.')
            
            # Highlight the current segment
            if segment["start"] <= current_time <= segment["end"]:
                st.markdown(f"**[{start_time} → {end_time}]** {segment['text']}")
            else:
                st.markdown(f"[{start_time} → {end_time}] {segment['text']}")