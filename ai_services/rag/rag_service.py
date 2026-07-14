# ai_services/rag/rag_service.py
import os
import re
from typing import List, Dict
from groq import Groq

# Import singleton managers
from ai_services.model_loader.loader import get_embedding_model
from ai_services.vector_db.chroma_service import get_chroma_client

class RAGService:
    def __init__(self):
        """Initialize with LAZY LOADING for multilingual model"""
        print("🌍 Initializing RAG Service (Multilingual: English + Hindi)...")
        
        # LAZY LOADING - model loads ONLY when first used
        self.embedding_model = None
        self.model_loaded = False
        
        # Initialize ChromaDB from singleton manager
        print("💾 Getting global vector database client...")
        self.chroma_client = get_chroma_client()
        
        # Initialize Groq LLM (fast)
        print("🤖 Connecting to Groq LLM...")
        self.groq_api_key = self._get_groq_key()
        
        if not self.groq_api_key:
            raise ValueError("❌ GROQ_API_KEY not found in .env file")
        
        self.groq_client = Groq(api_key=self.groq_api_key)
        self.model_name = "llama-3.3-70b-versatile"
        
        # Language support info
        self.supported_languages = {
            'hi': 'Hindi', 'en': 'English', 'es': 'Spanish', 'fr': 'French',
            'de': 'German', 'zh': 'Chinese', 'ja': 'Japanese', 'ko': 'Korean',
            'ar': 'Arabic', 'ru': 'Russian', 'pt': 'Portuguese'
        }
        
        print("✅ RAG Service ready (Model loads on first question)")
    
    def _load_embedding_model(self):
        """Load multilingual model from cache/loader - called only when needed"""
        if self.model_loaded:
            return
        self.embedding_model = get_embedding_model()
        self.model_loaded = True
    
    def _get_groq_key(self):
        """Get Groq API key from .env"""
        try:
            with open('.env', 'r') as f:
                for line in f:
                    if 'GROQ_API_KEY' in line:
                        return line.split('=')[1].strip().strip('"\'')
        except Exception as e:
            print(f"⚠️ Error reading .env: {e}")
        return None
    
    def process_transcript(self, transcript_text: str, video_id: str, video_duration_minutes=60):
        """
        Process transcript: chunk, embed, store in vector DB
        Returns: Number of chunks created
        """
        safe_collection_name = "vid_" + video_id.replace('-', '_').replace('.', '_')
        
        # Caching optimization: Check if collection already exists and has documents
        try:
            collection = self.chroma_client.get_collection(name=safe_collection_name)
            count = collection.count()
            if count > 0:
                print(f"✅ Transcript already processed and stored in vector DB ({count} chunks)")
                return count
        except Exception:
            # Collection does not exist
            pass

        # LAZY LOAD: Model loads here (first time only)
        self._load_embedding_model()
        
        print(f"📝 Processing transcript for video: {video_id[:10]}...")
        print(f"🔍 DEBUG: Transcript length: {len(transcript_text)} characters")
        print(f"🔍 DEBUG: First 200 chars: {transcript_text[:200]}")
        
        # Delete existing collection if any (in case it was empty or broken)
        try:
            self.chroma_client.delete_collection(safe_collection_name)
            print(f"♻️ Cleared old empty vector store for this video")
        except:
            pass
        
        # Create new collection
        collection = self.chroma_client.create_collection(
            name=safe_collection_name,
            metadata={"video_id": video_id}
        )
        
        # Chunk the transcript
        chunks = self._chunk_transcript(transcript_text, video_duration_minutes)
        print(f"✂️ Created {len(chunks)} chunks from transcript")
        
        # Batch encode all chunks for high speed!
        print("⚡ Batch encoding transcript chunks...")
        texts = [chunk['text'] for chunk in chunks]
        embeddings = self.embedding_model.encode(texts, batch_size=64, show_progress_bar=False).tolist()
        print("✅ Batch encoding complete.")
        
        # Add chunks to vector DB in a single batch operation
        collection.add(
            embeddings=embeddings,
            documents=texts,
            metadatas=[{
                'chunk_id': i,
                'timestamp': chunk['timestamp'],
                'word_count': len(chunk['text'].split()),
                'video_id': video_id
            } for i, chunk in enumerate(chunks)],
            ids=[f"chunk_{i}" for i in range(len(chunks))]
        )
        
        print(f"💿 Stored {len(chunks)} chunks in vector database")
        return len(chunks)
    
    def _chunk_transcript(self, transcript_text: str, video_duration_minutes=60):
        """Split transcript by WORD COUNT since there's no punctuation"""
        if not transcript_text or len(transcript_text.strip()) < 50:
            print("⚠️ WARNING: Transcript too short or empty")
            return []

        print(f"🔍 DEBUG: Original transcript length: {len(transcript_text)} chars")

        # Split into words
        words = transcript_text.split()
        print(f"🔍 DEBUG: Total words: {len(words)}")

        # Create chunks of 100 words each
        chunk_size = 100
        chunks = []

        for i in range(0, len(words), chunk_size):
            chunk_words = words[i:i + chunk_size]
            chunk_text = ' '.join(chunk_words)

            timestamp = self._estimate_timestamp(i, len(words), video_duration_minutes)

            chunks.append({
                'text': chunk_text,
                'timestamp': timestamp,
                'word_count': len(chunk_words)
            })

        print(f"✅ Created {len(chunks)} chunks from {len(words)} words")
        return chunks
    
    def _estimate_timestamp(self, position: int, total_items: int, video_duration_minutes=60):
        """Convert position to timestamp"""
        if video_duration_minutes <= 0:
            video_duration_minutes = 60

        total_seconds = int(video_duration_minutes * 60)
        percentage = (position / max(total_items, 1)) * 100
        approx_seconds = int((percentage / 100) * total_seconds)

        range_seconds = 22
        start_seconds = max(0, approx_seconds - range_seconds)
        end_seconds = min(total_seconds, approx_seconds + (range_seconds + 1))

        def format_to_mm_ss(seconds):
            mins = seconds // 60
            secs = seconds % 60
            return f"{mins:02d}:{secs:02d}"

        return f"{format_to_mm_ss(start_seconds)}-{format_to_mm_ss(end_seconds)}"
    
    def ask_question(self, question: str, video_id: str, video_title: str, video_duration_minutes=60):
        """Main Q&A with duration for better timestamps"""
        print(f"🤔 Question: {question[:50]}...")
        
        try:
            relevant_chunks = self._search_chunks(question, video_id)
            
            if not relevant_chunks:
                return self._get_fallback_answer(question, video_title)
            
            print(f"🔍 Found {len(relevant_chunks)} relevant chunks")
            
            answer_data = self._generate_groq_answer(question, relevant_chunks, video_title)
            return answer_data
            
        except Exception as e:
            print(f"❌ RAG Error: {e}")
            return self._get_fallback_answer(question, video_title)
    
    def _search_chunks(self, question: str, video_id: str):
        """Multilingual search in vector DB"""
        self._load_embedding_model()
        
        try:
            safe_collection_name = "vid_" + video_id.replace('-', '_').replace('.', '_')
            collection = self.chroma_client.get_collection(name=safe_collection_name)
            
            question_embedding = self.embedding_model.encode(question).tolist()
            
            results = collection.query(
                query_embeddings=[question_embedding],
                n_results=6,
                include=['documents', 'metadatas', 'distances']
            )
            
            chunks = []
            for i, doc in enumerate(results['documents'][0]):
                chunks.append({
                    'text': doc,
                    'timestamp': results['metadatas'][0][i]['timestamp'],
                    'relevance_score': 1 - results['distances'][0][i],
                })
            
            chunks.sort(key=lambda x: x['relevance_score'], reverse=True)
            return chunks
            
        except Exception as e:
            print(f"⚠️ Search error: {e}")
            return []
    
    def _generate_groq_answer(self, question: str, chunks: List[Dict], video_title: str):
        """Generate perfectly formatted ChatGPT-like answer"""
        transcript_context = "\n\n".join([
            f"[{chunk['timestamp']}]: {chunk['text'][:300]}"
            for chunk in chunks[:3]
        ]) if chunks else "No specific content found."
        
        prompt = f"""You are explaining a YouTube video to a student.

VIDEO: "{video_title}"
QUESTION: "{question}"

TRANSCRIPT EXCERPTS:
{transcript_context}

CREATE ANSWER WITH THIS EXACT STRUCTURE:

🎯 **Nice! This is a fundamental concept!** 
[Start with encouragement, 1 sentence]

📘 **Quick Answer:**
[1-2 line simple answer]

📚 **From the Video:**
• The instructor says: [quote from video]
• Key point: [another point]
• Important: [third point]

🧠 **Simple Explanation:**
[Explain in beginner-friendly way, 2 sentences max]

🚀 **Key Points to Remember:**
1. [Point 1]
2. [Point 2] 
3. [Point 3]

💡 **Pro Tip:** [One practical advice]

IMPORTANT FORMATTING RULES:
1. Use EXACT emojis and headers above
2. Use • for video points
3. Use 1. 2. 3. for key points
4. Keep each section SHORT
5. Be encouraging and clear

Now create the answer:"""

        try:
            response = self.groq_client.chat.completions.create(
                messages=[
                    {
                        "role": "system",
                        "content": "You are a friendly, expert tutor. Always start with encouragement. Follow the exact format with emojis and clear sections."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                model=self.model_name,
                temperature=0.1,
                max_tokens=600
            )
            
            answer_text = response.choices[0].message.content
            
            # Clean formatting
            answer_text = self._clean_formatting(answer_text)
            
            return {
                'answer': answer_text,
                'chunks_used': [ch['timestamp'] for ch in chunks[:2]] if chunks else [],
                'confidence': 'high',
                'source': 'groq_rag',
                'model': self.model_name,
                'has_transcript_context': bool(chunks)
            }
            
        except Exception as e:
            print(f"⚠️ Groq API error: {e}")
            return self._get_local_answer(question, chunks, video_title)
    
    def _clean_formatting(self, answer_text):
        """Simple clean formatting - NO MARKDOWN MESS"""
        if not answer_text:
            return answer_text
        
        # 1. Fix common formatting issues
        answer_text = answer_text.replace('** **', '**')
        answer_text = answer_text.replace('***', '**')
        
        # 2. Ensure proper line breaks
        lines = answer_text.split('\n')
        cleaned_lines = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Add proper spacing for sections
            if line.startswith(('🎯', '📘', '📚', '🧠', '🚀', '💡')):
                if cleaned_lines:
                    cleaned_lines.append("")  # Empty line before section
                cleaned_lines.append(line)
            elif line.startswith(('•', '1.', '2.', '3.', '4.', '5.')):
                cleaned_lines.append(f"  {line}")
            else:
                cleaned_lines.append(line)
        
        result = '\n'.join(cleaned_lines)
        result = re.sub(r'\n{3,}', '\n\n', result)
        
        return result
    
    def _get_local_answer(self, question: str, chunks: List[Dict], video_title: str):
        """Fallback answer without LLM - structured cleanly to display beautifully in templates"""
        if chunks:
            best_chunk = chunks[0]
            text_excerpt = best_chunk['text'].strip()
            if len(text_excerpt) > 400:
                text_excerpt = text_excerpt[:400] + "..."
            
            # Format using elements that the template parses into structured CSS/HTML blocks
            answer = "🎯 **Local Search Results (AI Offline Fallback)**\n"
            answer += f"We found relevant information matching your question in the transcript of '{video_title}'.\n\n"
            
            answer += "📘 **Key Excerpt from Video:**\n"
            answer += f"\"{text_excerpt}\"\n\n"
            
            answer += "🚀 **Context & Timeline:**\n"
            answer += f"• This section appears around **{best_chunk['timestamp']}** in the video.\n"
            answer += "• You can skip to this timestamp in the video player above for full details.\n\n"
            
            answer += "💡 **Note:** The AI tutor is currently in offline fallback mode because your GROQ_API_KEY has expired or is invalid. Please update the API key in your .env file to restore complete, conversational tutor generation."
            
            return {
                'answer': answer,
                'chunks_used': [best_chunk['timestamp']],
                'confidence': 'medium',
                'source': 'vector_search',
                'model': 'sentence_transformer',
                'has_transcript_context': True
            }
        else:
            return self._get_fallback_answer(question, video_title)
    
    def _get_fallback_answer(self, question: str, video_title: str):
        """When no relevant content found"""
        return {
            'answer': f"I searched the transcript of '{video_title}' but couldn't find specific information about '{question}'. Try asking about general concepts covered in the video.",
            'chunks_used': [],
            'confidence': 'low',
            'source': 'no_match',
            'model': 'none',
            'has_transcript_context': False
        }
    
    def format_for_display(self, rag_result):
        """Format for HTML display"""
        lines = []
        
        lines.append(f"🤖 **AI Tutor Answer**")
        lines.append("")
        for line in rag_result['answer'].split('\n'):
            lines.append(line)
        lines.append("")
        
        if rag_result.get('chunks_used'):
            timestamp_str = ", ".join(rag_result['chunks_used'])
            lines.append(f"📍 **Video sections:** {timestamp_str}")
        
        lines.append("")
        lines.append("💡 *Powered by video transcript analysis*")
        
        return lines
    
    def detect_language(self, text):
        """Detect language of text"""
        text_lower = text.lower()[:1000]
        
        language_indicators = {
            'hi': ['है', 'और', 'के', 'में', 'की'],
            'en': ['the', 'and', 'is', 'in', 'to'],
            'es': ['el', 'la', 'que', 'en', 'y'],
            'fr': ['le', 'la', 'et', 'en', 'de'],
        }
        
        scores = {}
        for lang_code, indicators in language_indicators.items():
            score = sum(1 for word in indicators if word in text_lower)
            if score > 0:
                scores[lang_code] = score
        
        if scores:
            return max(scores.items(), key=lambda x: x[1])[0]
        
        return 'en'

class QAService:
    """Simple fallback Q&A service when RAG fails"""
    
    def find_answer_in_transcript(self, question, transcript_text, video_title):
        """Simple keyword matching fallback"""
        return {
            'answer': f"RAG system is initializing... Try again in a moment.\n\nFor '{video_title}', try asking about main concepts mentioned in the video.",
            'timestamp': None,
            'confidence': 'low',
            'source': 'fallback',
            'method': 'minimal'
        }
    
    def format_answer_for_display(self, qa_result):
        """Format fallback answer"""
        return [
            "⚠️ **RAG System Initializing**",
            "",
            qa_result['answer'],
            "",
            "🔄 Please try again in a moment..."
        ]
