import json
import wave
import re
import streamlit as st
from vosk import Model, KaldiRecognizer
import os
from modules.utils import format_time  # Import format_time from utils

def transcribe_audio(audio_path, model_dir, progress_placeholder):
    """Transcribe audio using Vosk"""
    try:
        model = Model(model_dir)
        
        raw_segments = []
        
        # Open the wave file
        wf = wave.open(audio_path, "rb")
        
        # Check if audio format is proper
        if wf.getnchannels() != 1 or wf.getsampwidth() != 2 or wf.getcomptype() != "NONE":
            st.error("Audio file must be WAV format mono PCM.")
            return []
        
        # Create recognizer
        rec = KaldiRecognizer(model, wf.getframerate())
        rec.SetWords(True)
        
        # Get total frames for progress tracking
        total_frames = wf.getnframes()
        chunk_size = 4000  # Process audio in chunks
        
        # Track progress for Streamlit
        progress_bar = progress_placeholder.progress(0)
        frames_processed = 0
        
        while True:
            data = wf.readframes(chunk_size)
            if len(data) == 0:
                break
            
            # Update progress
            frames_processed += min(chunk_size, total_frames - frames_processed)
            progress_percentage = min(frames_processed / total_frames, 1.0)
            progress_bar.progress(progress_percentage)
            
            # Process data
            if rec.AcceptWaveform(data):
                result = json.loads(rec.Result())
                if result.get("text", "").strip():
                    # Store raw word-level data
                    raw_segments.append(result)
        
        # Get final result
        result = json.loads(rec.FinalResult())
        if result.get("text", "").strip():
            raw_segments.append(result)
        
        progress_bar.progress(1.0)
        return raw_segments
    
    except Exception as e:
        st.error(f"Error during transcription: {str(e)}")
        import traceback
        st.error(f"Transcription error details: {traceback.format_exc()}")
        return []

def split_into_short_lines(raw_segments, max_line_length=40, max_line_duration=3.0):
    """Split transcription into shorter lines for better subtitle display"""
    segments = []
    
    for raw_segment in raw_segments:
        if not raw_segment.get("result"):
            continue
            
        words = raw_segment["result"]
        if not words:
            continue
            
        current_line = []
        current_text = ""
        line_start_time = words[0]["start"]
        
        for word in words:
            word_text = word["word"]
            
            # If adding this word would make the line too long, or if duration is too long
            if (len(current_text + word_text) > max_line_length or 
                (word["end"] - line_start_time) > max_line_duration):
                # Save the current line if it's not empty
                if current_line:
                    segments.append({
                        "text": current_text.strip(),
                        "start": line_start_time,
                        "end": current_line[-1]["end"]
                    })
                    
                # Start a new line
                current_line = [word]
                current_text = word_text + " "
                line_start_time = word["start"]
            else:
                # Add the word to the current line
                current_line.append(word)
                current_text += word_text + " "
        
        # Add the last line if it's not empty
        if current_line:
            segments.append({
                "text": current_text.strip(),
                "start": line_start_time,
                "end": current_line[-1]["end"]
            })
    
    return segments

def split_at_punctuation(segments):
    """Further split segments at sentence boundaries (periods, question marks, etc.)"""
    refined_segments = []
    
    for segment in segments:
        text = segment["text"]
        
        # If the segment doesn't contain punctuation that would indicate a natural break
        if not re.search(r'[.!?]', text):
            refined_segments.append(segment)
            continue
            
        # Split at punctuation and preserve the punctuation
        sentence_parts = re.split(r'([.!?])', text)
        
        # Group punctuation with preceding text
        sentences = []
        for i in range(0, len(sentence_parts) - 1, 2):
            if i + 1 < len(sentence_parts):
                sentences.append(sentence_parts[i] + sentence_parts[i + 1])
            else:
                sentences.append(sentence_parts[i])
        
        # If there's an odd number of parts, add the last part
        if len(sentence_parts) % 2 == 1:
            sentences[-1] += sentence_parts[-1]
        
        # Skip if we couldn't split into sentences properly
        if not sentences:
            refined_segments.append(segment)
            continue
            
        # Calculate time per character for proportional time distribution
        total_chars = sum(len(s) for s in sentences)
        if total_chars == 0:
            refined_segments.append(segment)
            continue
            
        time_span = segment["end"] - segment["start"]
        time_per_char = time_span / total_chars
        
        # Distribute time proportionally to text length
        current_time = segment["start"]
        for sentence in sentences:
            if not sentence.strip():
                continue
                
            duration = len(sentence) * time_per_char
            end_time = current_time + duration
            
            refined_segments.append({
                "text": sentence.strip(),
                "start": current_time,
                "end": end_time
            })
            
            current_time = end_time
    
    return refined_segments

def create_srt_file(segments, output_path):
    """Create SRT file from transcribed segments"""
    # Ensure output directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            for i, segment in enumerate(segments, start=1):
                # Skip empty segments
                if not segment["text"].strip():
                    continue
                    
                # Write segment number
                f.write(f"{i}\n")
                
                # Write timestamp
                start_time = format_time(segment["start"])
                end_time = format_time(segment["end"])
                f.write(f"{start_time} --> {end_time}\n")
                
                # Write text
                f.write(f"{segment['text'].strip()}\n\n")
        
        # Check if the file was created successfully
        if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
            raise FileNotFoundError(f"Failed to create SRT file: {output_path}")
        
        return output_path
    
    except Exception as e:
        st.error(f"Error creating SRT file: {str(e)}")
        import traceback
        st.error(f"SRT creation error details: {traceback.format_exc()}")
        raise