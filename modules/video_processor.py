import os
import tempfile
import streamlit as st
from modules.utils import extract_audio, burn_subtitles_into_video, format_time
from modules.transcriber import (
    transcribe_audio, 
    split_into_short_lines, 
    split_at_punctuation, 
    create_srt_file
)

def process_video(video_path, model_key, max_line_length, max_line_duration):
    """Process the video and generate subtitles"""
    # Create temp directory for processing
    temp_dir = tempfile.mkdtemp()
    
    # Get filenames
    video_filename = os.path.basename(video_path)
    base_name = os.path.splitext(video_filename)[0]
    
    # Define temp files
    audio_path = os.path.join(temp_dir, f"{base_name}_audio.wav")
    
    # Define output files - now storing in project directory
    srt_dir = os.path.join("output", "subtitles")
    os.makedirs(srt_dir, exist_ok=True)
    
    srt_path = os.path.join(temp_dir, f"{base_name}.srt")
    project_srt_path = os.path.join(srt_dir, f"{base_name}.srt")
    
    # Create output videos directory
    videos_dir = os.path.join("output", "videos")
    os.makedirs(videos_dir, exist_ok=True)
    
    # Output video with embedded subtitles
    output_video_path = os.path.join(videos_dir, f"{base_name}_with_subs.mp4")
    
    # Process video in steps with progress indicators
    try:
        # Step 1: Extract audio
        with st.spinner("Extracting audio from video..."):
            audio_path = extract_audio(video_path, audio_path)
        
        # Step 2: Transcribe audio
        st.markdown("### Transcribing audio")
        st.markdown("This may take a while depending on the video length and model size.")
        progress_placeholder = st.empty()
        model_dir = os.path.join("models", model_key)
        raw_segments = transcribe_audio(audio_path, model_dir, progress_placeholder)
        
        # Step 3: Process transcription
        with st.spinner("Processing transcription..."):
            # Make sure raw_segments is not empty
            if not raw_segments:
                st.error("No speech was detected in the video.")
                return None
                
            segments = split_into_short_lines(raw_segments, max_line_length, max_line_duration)
            segments = split_at_punctuation(segments)
            
            # Ensure segments are not empty
            if not segments:
                st.error("No valid segments were generated after processing.")
                return None
        
        # Step 4: Create SRT files
        with st.spinner("Creating subtitle files..."):
            # Create a module function for format_time if not imported
            srt_path = create_srt_file(segments, srt_path)
            create_srt_file(segments, project_srt_path)
            st.success(f"Subtitle file created: {project_srt_path}")
        
        # Step 5: Burn subtitles into video - wrap this in try/except to continue even if it fails
        subtitle_burned = False
        try:
            with st.spinner("Adding subtitles to video..."):
                # Check that the files exist before attempting to burn
                if not os.path.exists(video_path):
                    raise FileNotFoundError(f"Video file not found: {video_path}")
                    
                if not os.path.exists(srt_path):
                    raise FileNotFoundError(f"SRT file not found: {srt_path}")
                
                # Attempt to burn subtitles
                output_video_path = burn_subtitles_into_video(video_path, srt_path, output_video_path)
                subtitle_burned = True
                st.success("Subtitles burned into video successfully!")
        except Exception as e:
            st.error(f"Error burning subtitles: {str(e)}")
            st.warning("Continuing with dynamic subtitles only...")
            import traceback
            print(f"Subtitle burning error details: {traceback.format_exc()}")
        
        # Return results - if subtitle burning failed, set output_video_path to original video
        result = {
            "output_video_path": output_video_path if subtitle_burned else video_path,
            "srt_path": srt_path,
            "project_srt_path": project_srt_path,
            "segments": segments,
            "subtitle_burned": subtitle_burned
        }
        
        return result
    
    except Exception as e:
        st.error(f"An error occurred during processing: {str(e)}")
        import traceback
        st.error(f"Details: {traceback.format_exc()}")
        return None