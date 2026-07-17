# backend/views/video_views.py
from django.shortcuts import render
from django.contrib.auth.decorators import login_required

from backend.utils.error_handler import ErrorHandler
from backend.services.youtube_service import YouTubeService
from ai_services.rag.rag_service import RAGService, QAService
from ai_services.ml.analysis_service import TranscriptAnalyzer

@login_required
def video_analyse_QA(request):
    """Video analysis page - requires login"""
    video_info = None
    question_asked = False
    question = ""
    answer_lines = []
    
    if request.method == 'POST':
        # Check if it's a Q&A question
        if 'question_mode' in request.POST:
            question_asked = True
            question = request.POST.get('question', '')
            video_id = request.POST.get('video_id', '')
            video_title = request.POST.get('video_title', '')
            transcript_text = request.POST.get('transcript_text', '')
            duration_minutes = request.POST.get('duration_minutes', 60)
            
            # Reconstruct video_info from POST data
            video_info = {
                'title': video_title,
                'video_id': video_id,
                'has_transcript': True,
                'transcript_text': transcript_text,
                'duration_minutes': float(duration_minutes),
                # Add minimal info needed for display
                'channel': 'Previous Analysis',
                'description': 'Video previously analyzed',
                'word_count': len(transcript_text.split()),
                'analysis': {'level_score': 'N/A'},
                'skill_level': 'Beginner'
            }
            
            # ========== USE RAG SERVICE ==========
            try:
                rag_service = RAGService()
                
                # Process transcript first (store in vector DB)
                print("🔄 Processing transcript for RAG...")
                chunks_count = rag_service.process_transcript(
                    transcript_text, 
                    video_id, 
                    video_info.get('duration_minutes', 60)
                )
                print(f"✅ Processed {chunks_count} chunks")
                
                # Ask question using RAG
                print(f"🤔 Asking: {question[:50]}...")
                rag_result = rag_service.ask_question(
                    question, 
                    video_id, 
                    video_title,
                    video_info.get('duration_minutes', 60)
                )
                
                # Format answer for display
                answer_lines = rag_service.format_for_display(rag_result)
                print("✅ RAG answer generated")
                
            except Exception as e:
                print(f"❌ RAG Error: {e}")
                # Fallback to simple Q&A if RAG fails
                qa_service = QAService()
                qa_result = qa_service.find_answer_in_transcript(
                    question, 
                    transcript_text, 
                    video_title
                )
                answer_lines = qa_service.format_answer_for_display(qa_result)
            # ========== END RAG ==========
            
        # Original video analysis code
        elif 'video_url' in request.POST:
            video_url = request.POST['video_url']
            
            # Extract video ID
            video_id = YouTubeService.extract_video_id(video_url)
            if video_id and len(video_id) == 11:
                # Fetch video info WITH DURATION
                try:
                    video = YouTubeService.fetch_video_details(video_id, parts="snippet,contentDetails")
                    
                    if video:
                        # Get video duration
                        duration_iso = video['contentDetails']['duration']  # PT1H15M30S
                        duration_minutes = YouTubeService.parse_duration(duration_iso)
                        
                        video_info = {
                            'title': video['snippet']['title'],
                            'channel': video['snippet']['channelTitle'],
                            'description': video['snippet']['description'],
                            'video_id': video_id,
                            'duration_minutes': duration_minutes,
                            'has_transcript': False,
                            'word_count': 0,
                            'transcript_text': ''
                        }
                        
                        # Try to get transcript
                        try:
                            transcript_data, transcript_full = YouTubeService.fetch_transcript(video_id)
                            
                            video_info['has_transcript'] = True
                            video_info['word_count'] = sum(len(snippet.text.split()) for snippet in transcript_data)
                            video_info['transcript_sample'] = ' '.join([snippet.text for snippet in transcript_data[:5]])
                            video_info['transcript_full'] = transcript_full
                            video_info['transcript_text'] = video_info['transcript_full']
                            
                        except Exception as e:
                            video_info['transcript_error'] = str(e)
                            # Graceful fallback: perform analysis using metadata instead of transcript
                            try:
                                analyzer = TranscriptAnalyzer()
                                analysis_results = analyzer.analyze_metadata(
                                    video_info['title'],
                                    video_info['description'],
                                    video_info['duration_minutes']
                                )
                                video_info['analysis'] = analysis_results
                                video_info['skill_level'] = analysis_results['skill_level']
                            except Exception as meta_err:
                                video_info['analysis_error'] = f"Metadata fallback failed: {str(meta_err)}"
                            
                except Exception as e:
                    ErrorHandler.log_error(e, "YouTube API")
                    video_info = {'error': ErrorHandler.get_user_friendly_error(e)}
            else:
                video_info = {'error': 'Invalid YouTube URL. Make sure it is a valid YouTube video link.'}
    
    return render(request, 'analyzer/video_analyse_QA.html', {
        'video_info': video_info,
        'question_asked': question_asked,
        'question': question,
        'answer_lines': answer_lines
    })
