import streamlit as st
import os
from modules.ui import render_sidebar, render_main_area
from modules.utils import check_dependencies

# Set page configuration
st.set_page_config(
    page_title="Video Subtitle Generator",
    page_icon="🎬",
    layout="wide",
)

def main():
    st.title("🎬 Video Subtitle Generator")
    st.markdown("""
    This app automatically generates subtitles for your videos using speech recognition.
    Upload a video, choose your settings, and get a video with embedded subtitles!
    """)
    
    # Check dependencies
    if not check_dependencies():
        st.stop()
    
    # Create output directories if they don't exist
    os.makedirs("output/subtitles", exist_ok=True)
    os.makedirs("output/videos", exist_ok=True)
    
    # Render sidebar with settings
    model_key, max_line_length, max_line_duration = render_sidebar()
    
    # Render main area with file upload and processing
    render_main_area(model_key, max_line_length, max_line_duration)

if __name__ == "__main__":
    # Create models directory if it doesn't exist
    os.makedirs("models", exist_ok=True)
    main()