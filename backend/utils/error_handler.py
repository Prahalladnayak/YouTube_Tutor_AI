import traceback

class ErrorHandler:
    @staticmethod
    def log_error(error, context=""):
        """Log errors with context"""
        error_msg = f"❌ ERROR ({context}): {str(error)}"
        print(error_msg)
        print(traceback.format_exc())
        return error_msg
    
    @staticmethod
    def get_user_friendly_error(error):
        """Convert technical errors to user-friendly messages"""
        error_str = str(error).lower()
        
        if "quota" in error_str:
            return "YouTube API quota exceeded. Try again tomorrow or use a different API key."
        elif "transcript" in error_str:
            return "No transcript available for this video. Try a different video with captions."
        elif "key" in error_str or "api" in error_str:
            return "API key error. Please check your YouTube API key configuration."
        elif "not found" in error_str or "404" in error_str:
            return "Video not found. Check the YouTube URL."
        elif "invalid" in error_str:
            return "Invalid YouTube URL. Make sure it's a valid YouTube video link."
        else:
            return "An error occurred. Please try again or try a different video."
