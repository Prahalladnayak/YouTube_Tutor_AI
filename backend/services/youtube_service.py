# backend/services/youtube_service.py
import re
import os
from googleapiclient.discovery import build
from youtube_transcript_api import YouTubeTranscriptApi
from backend.utils.error_handler import ErrorHandler

class YouTubeService:
    @staticmethod
    def get_api_key():
        """Get YouTube API key from system environment or .env file"""
        # 1. Check system environment (for production/Render)
        api_key = os.environ.get('YOUTUBE_API_KEY')
        if api_key:
            return api_key.strip().strip('"\'')
            
        # 2. Check local .env file (for local development)
        try:
            if os.path.exists('.env'):
                with open('.env', 'r') as f:
                    for line in f:
                        if 'YOUTUBE_API_KEY' in line:
                            return line.split('=')[1].strip().strip('"\'')
        except Exception as e:
            ErrorHandler.log_error(e, "Reading YouTube API Key")
        return None

    @classmethod
    def get_youtube_client(cls):
        """Get YouTube API build client"""
        api_key = cls.get_api_key()
        if not api_key:
            raise ValueError("YouTube API key not found in .env")
        return build('youtube', 'v3', developerKey=api_key)

    @staticmethod
    def extract_video_id(url):
        """Extract YouTube video ID from URL"""
        if 'v=' in url:
            return url.split('v=')[1][:11]
        elif 'youtu.be/' in url:
            return url.split('youtu.be/')[1][:11]
        return url[:11]

    @staticmethod
    def parse_duration(duration_iso):
        """Convert YouTube duration (PT1H15M30S) to minutes"""
        hours = re.search(r'(\d+)H', duration_iso)
        minutes = re.search(r'(\d+)M', duration_iso)
        seconds = re.search(r'(\d+)S', duration_iso)
        
        total_minutes = 0
        
        if hours:
            total_minutes += int(hours.group(1)) * 60
        if minutes:
            total_minutes += int(minutes.group(1))
        if seconds:
            total_minutes += int(seconds.group(1)) / 60
        
        return round(total_minutes, 1)

    @classmethod
    def fetch_video_details(cls, video_id, parts="snippet,contentDetails"):
        """Fetch video snippet and/or contentDetails from YouTube API"""
        youtube = cls.get_youtube_client()
        request_api = youtube.videos().list(
            part=parts,
            id=video_id
        )
        response = request_api.execute()
        if response.get('items'):
            return response['items'][0]
        return None

    @staticmethod
    def fetch_transcript(video_id):
        """Fetch transcript list data and raw transcript text"""
        api = YouTubeTranscriptApi()
        
        # Support cookies.txt to bypass YouTube datacenter bot detection on Render
        cookies_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'cookies.txt')
        if os.path.exists(cookies_path):
            print("🍪 Using cookies.txt to bypass YouTube datacenter block...")
            try:
                transcript_list = api.list(video_id, cookies=cookies_path)
            except Exception as e:
                print(f"⚠️ Error using cookies: {e}. Falling back to default list...")
                transcript_list = api.list(video_id)
        else:
            transcript_list = api.list(video_id)
        
        # Try English first, then Hindi, then any available transcript
        try:
            transcript_obj = transcript_list.find_transcript(['en'])
        except Exception:
            try:
                transcript_obj = transcript_list.find_transcript(['hi'])
            except Exception:
                transcript_obj = (
                    transcript_list._manually_created_transcripts[0]
                    if transcript_list._manually_created_transcripts
                    else transcript_list._generated_transcripts[0]
                )
        
        transcript_data = list(transcript_obj.fetch())
        transcript_text = ' '.join([snippet.text for snippet in transcript_data])
        
        return transcript_data, transcript_text
