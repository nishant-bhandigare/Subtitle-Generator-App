import streamlit as st
import os
import tempfile
import time
from pathlib import Path
from modules.video_processor import process_video
from modules.utils import VOSK_MODELS, download_model, format_time

def render_sidebar():
    """Render the sidebar with all settings"""
    st.sidebar.title("Settings")
    
    # Model selection
    model_key = st.sidebar.selectbox(
        "Select Speech Recognition Model",
        options=list(VOSK_MODELS.keys()),
        format_func=lambda x: f"{VOSK_MODELS[x]['name']} ({VOSK_MODELS[x]['size']})",
        index=0
    )
    
    # Model download if needed
    model_dir = os.path.join("models", model_key)
    
    if not os.path.exists(model_dir):
        st.sidebar.warning(f"Model needs to be downloaded first ({VOSK_MODELS[model_key]['size']})")
        dl_button = st.sidebar.button("Download Selected Model")
        dl_progress = st.sidebar.empty()
        
        if dl_button:
            download_model(model_key, dl_progress)
    else:
        st.sidebar.success("Model is ready to use")
    
    # Advanced settings
    st.sidebar.markdown("### Advanced Settings")
    max_line_length = st.sidebar.slider("Maximum characters per line", 20, 80, 40)
    max_line_duration = st.sidebar.slider("Maximum seconds per line", 1.0, 6.0, 3.0)
    
    # Help section
    with st.sidebar.expander("Help & Information"):
        st.markdown("""
        ### How it works
        1. Upload your video
        2. Choose your model (bigger models are more accurate but take longer)
        3. Click "Generate Subtitles"
        4. Wait for processing (may take time for longer videos)
        5. Download the result or view the transcript
        
        ### Models
        - **Small**: Fast but less accurate (154MB)
        - **Medium**: Balanced speed and accuracy (1.1GB)
        - **Large**: Most accurate but slower (2.3GB)
        
        ### Tips
        - For better accuracy, use videos with clear speech and minimal background noise
        - Larger models give better results but take longer to download and process
        """)
    
    return model_key, max_line_length, max_line_duration

def render_main_area(model_key, max_line_length, max_line_duration):
    """Render the main area with file upload and processing"""
    uploaded_file = st.file_uploader("Upload your video", type=["mp4", "mov", "avi", "mkv"])
    
    if uploaded_file is not None:
        # Save uploaded file to disk
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=Path(uploaded_file.name).suffix)
        temp_file.write(uploaded_file.getvalue())
        video_path = temp_file.name
        temp_file.close()
        
        # Show uploaded video
        st.video(video_path)
        
        # Check if model exists
        model_dir = os.path.join("models", model_key)
        if not os.path.exists(model_dir):
            st.warning("Please download the selected model first from the sidebar.")
        else:
            # Process button
            if st.button("Generate Subtitles"):
                # Process the video
                with st.spinner("Processing video... This may take a while."):
                    try:
                        result = process_video(
                            video_path, model_key, max_line_length, max_line_duration
                        )
                    except Exception as e:
                        st.error(f"Error processing video: {str(e)}")
                        import traceback
                        st.error(f"Details: {traceback.format_exc()}")
                        result = None
                
                if result:
                    # Show results
                    st.success("Transcription completed successfully!")
                    
                    # Check for segments
                    has_segments = "segments" in result and result["segments"]
                    
                    if has_segments:
                        # Show transcript
                        with st.expander("Show Full Transcript", expanded=False):
                            segments = result["segments"]
                            for i, segment in enumerate(segments):
                                start_time = format_time(segment["start"]).replace(',', '.')
                                end_time = format_time(segment["end"]).replace(',', '.')
                                st.markdown(f"[{start_time} → {end_time}] {segment['text']}")
                        
                        # Display download options
                        display_download_options(result)
                    else:
                        st.error("No subtitle segments were generated. Check for speech in the video.")
                else:
                    st.error("Processing failed. Please check the logs for more details.")

def display_download_options(result):
    """Display download options for video and SRT file"""
    st.markdown("### Download Files")
    
    col1, col2 = st.columns(2)
    
    # Check that files exist before offering downloads
    with col1:
        if os.path.exists(result["output_video_path"]):
            with open(result["output_video_path"], "rb") as file:
                st.download_button(
                    label="Download Video with Subtitles",
                    data=file,
                    file_name=os.path.basename(result["output_video_path"]),
                    mime="video/mp4"
                )
        else:
            st.error("Output video file not found.")
    
    with col2:
        if os.path.exists(result["project_srt_path"]):
            with open(result["project_srt_path"], "rb") as file:
                st.download_button(
                    label="Download SRT File",
                    data=file,
                    file_name=os.path.basename(result["project_srt_path"]),
                    mime="text/plain"
                )
        else:
            st.error("SRT file not found.")