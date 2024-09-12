import os
import groq
import youtube_transcript_api
import streamlit as st
from urllib.parse import urlparse, parse_qs
from dotenv import load_dotenv
import time

# Load environment variables
load_dotenv()
groq_api_key = st.secrets["GROQ_API_KEY"]

# Initialize Groq client
client = groq.Groq(api_key=groq_api_key)

def get_transcript(video_url):
    """Retrieve the transcript for a YouTube video"""
    try:
        yt = youtube_transcript_api.YouTubeTranscriptApi
        parsed_url = urlparse(video_url)
        
        if 'youtu.be' in parsed_url.netloc:
            video_id = parsed_url.path.lstrip('/')
        elif 'youtube.com' in parsed_url.netloc:
            if '/shorts/' in parsed_url.path:
                video_id = parsed_url.path.split('/shorts/')[1]
            else:
                video_id = parse_qs(parsed_url.query).get('v', [None])[0]
        
        if not video_id:
            raise ValueError("Could not extract video ID from URL")
        
        transcript = yt.get_transcript(video_id)
        return " ".join([item["text"] for item in transcript])
    except Exception as e:
        st.error(f"Error retrieving transcript: {str(e)}")
        return None

def generate_post(transcript):
    """Generate a social media post from the video transcript using Groq's model"""
    if transcript:
        # Split the transcript into chunks of roughly 500 words
        words = transcript.split()
        chunk_size = 500
        chunks = [' '.join(words[i:i+chunk_size]) for i in range(0, len(words), chunk_size)]
        
        # Process each chunk
        chunk_summaries = []
        for i, chunk in enumerate(chunks):
            chunk_prompt = f"Summarize the key points from part {i+1} of a video transcript (30-50 words):\n\n{chunk}"
            try:
                chunk_completion = client.chat.completions.create(
                    messages=[
                        {"role": "system", "content": "You are a concise summarizer. Focus on the main ideas and key information."},
                        {"role": "user", "content": chunk_prompt}
                    ],
                    model="mixtral-8x7b-32768",
                    max_tokens=100,
                    temperature=0.7,
                )
                chunk_summaries.append(chunk_completion.choices[0].message.content.strip())
            except Exception as e:
                print(f"Error summarizing chunk {i+1}: {e}")
        
        # Combine chunk summaries and generate final post
        combined_summary = "\n\n".join([f"Part {i+1}:\n{summary}" for i, summary in enumerate(chunk_summaries)])
        final_prompt = f"Based on these summaries of different parts of a video transcript, create an engaging and complete social media post that captures the main ideas and essence of the entire video. Ensure the post is coherent and fully summarizes the content:\n\n{combined_summary}"
        
        try:
            chat_completion = client.chat.completions.create(
                messages=[
                    {"role": "system", "content": "You are a social media content creator skilled at synthesizing information from video summaries into engaging, complete posts. Ensure your post covers all main points and has a proper conclusion."},
                    {"role": "user", "content": final_prompt}
                ],
                model="mixtral-8x7b-32768",
                max_tokens=400,  # Increased from 200 to 400
                temperature=0.7,
            )
            return chat_completion.choices[0].message.content.strip()
        except Exception as e:
            print(f"Error generating final post: {e}")
            return None
    else:
        return "Transcript not available."

def main():
    st.title("YouTube Video Summarizer")
    
    # Input field for YouTube URL
    video_url = st.text_input("Enter the YouTube video URL:")
    
    # Submit button
    if st.button("Generate Summary"):
        if video_url:
            with st.spinner("Retrieving transcript and generating summary..."):
                time.sleep(2)  # Add a 2-second delay
                transcript = get_transcript(video_url)
                if transcript:
                    time.sleep(2)  # Add another 2-second delay
                    post_text = generate_post(transcript)
                    if post_text:
                        st.success("Summary generated successfully!")
                        st.text_area("Generated Summary:", value=post_text, height=300)
                    else:
                        st.error("Failed to generate summary.")
                else:
                    st.error("Failed to retrieve transcript.")
        else:
            st.warning("Please enter a YouTube video URL.")

if __name__ == "__main__":
    main()