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
        # Support cookies.txt to bypass YouTube datacenter bot detection on Render
        cookies_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'cookies.txt')
        cookies_status = "No cookies.txt found"
        
        if os.path.exists(cookies_path):
            cookies_status = "cookies.txt found"
            import requests
            import http.cookiejar
            try:
                session = requests.Session()
                # Set realistic browser headers to bypass bot-detection
                session.headers.update({
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Accept-Language': 'en-US,en;q=0.9',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                    'Referer': 'https://www.google.com/'
                })
                cookie_jar = http.cookiejar.MozillaCookieJar(cookies_path)
                cookie_jar.load(ignore_discard=True, ignore_expires=True)
                session.cookies = cookie_jar
                api = YouTubeTranscriptApi(http_client=session)
                cookies_status = "cookies.txt loaded successfully"
            except Exception as e:
                cookies_status = f"Failed to load cookies: {str(e)}"
                api = YouTubeTranscriptApi()
        else:
            api = YouTubeTranscriptApi()
            
        try:
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
            
        except Exception as e:
            # Fallback to yt-dlp to bypass YouTube's datacenter blocks
            print(f"⚠️ youtube-transcript-api failed: {e}. Falling back to yt-dlp...")
            try:
                return YouTubeService._fetch_transcript_ytdl(video_id)
            except Exception as ytdl_err:
                raise Exception(f"YouTube block detected. Regular fetch failed: {str(e)}. Fallback yt-dlp failed: {str(ytdl_err)} (Cookies status: {cookies_status})")

    @staticmethod
    def _fetch_transcript_ytdl(video_id):
        """Fallback to fetch transcripts via yt-dlp to bypass YouTube scraper blocks"""
        import yt_dlp
        import requests
        
        # A mock class to match youtube_transcript_api's FetchedTranscriptSnippet
        class FetchedTranscriptSnippet:
            def __init__(self, text, start, duration):
                self.text = text
                self.start = start
                self.duration = duration
            def __repr__(self):
                return f"FetchedTranscriptSnippet(text='{self.text}', start={self.start}, duration={self.duration})"

        url = f"https://www.youtube.com/watch?v={video_id}"
        ydl_opts = {
            'writeautomaticsub': True,
            'writesubtitles': True,
            'skip_download': True,
            'quiet': True,
            'no_warnings': True,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            subtitles = info.get('subtitles', {})
            auto_subtitles = info.get('automatic_captions', {})
            
            target_lang = None
            subtitle_formats = None
            
            # Try English first, then Hindi
            for lang in ['en', 'hi']:
                if lang in subtitles:
                    target_lang = lang
                    subtitle_formats = subtitles[lang]
                    break
                elif lang in auto_subtitles:
                    target_lang = lang
                    subtitle_formats = auto_subtitles[lang]
                    break
                    
            # Fallback to first available language if neither is found
            if not target_lang:
                if subtitles:
                    target_lang = list(subtitles.keys())[0]
                    subtitle_formats = subtitles[target_lang]
                elif auto_subtitles:
                    target_lang = list(auto_subtitles.keys())[0]
                    subtitle_formats = auto_subtitles[target_lang]
                    
            if not subtitle_formats:
                raise Exception("No subtitles found in video metadata")
                
            # Prefer JSON3 (clean JSON format), then VTT
            json3_url = None
            vtt_url = None
            for fmt in subtitle_formats:
                ext = fmt.get('ext')
                fmt_url = fmt.get('url')
                if ext == 'json3':
                    json3_url = fmt_url
                elif ext == 'vtt':
                    vtt_url = fmt_url
                    
            if json3_url:
                res = requests.get(json3_url, timeout=10)
                data = res.json()
                transcript_data = []
                for event in data.get('events', []):
                    if 'segs' in event:
                        text = ''.join([seg['utf8'] for seg in event['segs'] if 'utf8' in seg]).strip()
                        if text:
                            start = event.get('tStartMs', 0) / 1000.0
                            duration = event.get('dDurationMs', 0) / 1000.0
                            transcript_data.append(FetchedTranscriptSnippet(text, start, duration))
                
                transcript_text = ' '.join([s.text for s in transcript_data])
                return transcript_data, transcript_text
                
            elif vtt_url:
                res = requests.get(vtt_url, timeout=10)
                lines = res.text.split('\n')
                transcript_data = []
                for i in range(len(lines)):
                    if '-->' in lines[i]:
                        time_line = lines[i]
                        text_line = lines[i+1] if i+1 < len(lines) else ""
                        import re
                        text_line = re.sub(r'<[^>]*>', '', text_line).strip()
                        if not text_line:
                            continue
                            
                        parts = time_line.split('-->')
                        start_str = parts[0].strip()
                        t_parts = start_str.split(':')
                        try:
                            secs = float(t_parts[-1])
                            mins = int(t_parts[-2]) if len(t_parts) > 1 else 0
                            hrs = int(t_parts[-3]) if len(t_parts) > 2 else 0
                            start = hrs * 3600 + mins * 60 + secs
                        except:
                            start = 0.0
                        
                        transcript_data.append(FetchedTranscriptSnippet(text_line, start, 2.0))
                        
                transcript_text = ' '.join([s.text for s in transcript_data])
                return transcript_data, transcript_text
            else:
                raise Exception("No supported subtitle format found (JSON3 or VTT)")
