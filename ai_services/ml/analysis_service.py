import re
from collections import Counter

class TranscriptAnalyzer:
    def __init__(self):
        self._stop_words = None
        self.technical_terms = self.load_technical_terms()

    @property
    def stop_words(self):
        if self._stop_words is None:
            # Lazy import to prevent heavy NLTK loading on startup
            from nltk.corpus import stopwords
            self._stop_words = set(stopwords.words('english'))
        return self._stop_words
    
    def load_technical_terms(self):
        # Basic programming terms - we can expand this later
        terms = [
            # Programming basics
            'algorithm', 'variable', 'function', 'class', 'object', 
            'loop', 'array', 'database', 'api', 'framework',
            'syntax', 'compiler', 'interpreter', 'debugging',
            
            # Python specific
            'python', 'django', 'flask', 'list', 'dictionary',
            'tuple', 'module', 'package', 'import', 'def', 'class',
            
            # Common technical terms
            'recursion', 'iteration', 'inheritance', 'polymorphism',
            'abstraction', 'encapsulation', 'algorithm', 'complexity'
        ]
        return set(terms)
    
    def detect_language(self, text):
        """Simple language detection"""
        # Check for common Hindi words/characters
        hindi_chars = ['़', 'ऽ', 'ा', 'ि', 'ी', 'ु', 'ू', 'े', 'ै', 'ो', 'ौ', 'ं', 'ः', 'ँ']
        english_chars = sum(1 for char in text if 'a' <= char.lower() <= 'z')
        
        hindi_count = sum(1 for char in text if char in hindi_chars)
        total_chars = len(text)
        
        if total_chars == 0:
            return 'en'
        
        hindi_ratio = hindi_count / total_chars
        
        if hindi_ratio > 0.1:  # More than 10% Hindi characters = Hindi
            return 'hi'
        elif english_chars / total_chars > 0.5:  # More than 50% English = English
            return 'en'
        elif hindi_count > 0:  # Any Hindi characters present = Hindi
            return 'hi'
        else:
            return 'en'  # Default to English
    
    def calculate_readability(self, text):
        """Calculate how easy the text is to read"""
        if not text or len(text.split()) < 10:
            return 0
        
        try:
            # Lazy import to prevent textstat loading on startup
            import textstat
            # Flesch Reading Ease: Higher = easier to read
            flesch_score = textstat.flesch_reading_ease(text)
            
            # Flesch-Kincaid Grade Level: US grade level needed
            fk_grade = textstat.flesch_kincaid_grade(text)
            
            # Convert to 0-100 scale (for our display)
            # Flesch score: 0-30 (college grad), 30-50 (college), 50-60 (high school), 60-70 (8th-9th), 70-80 (7th), 80-90 (6th), 90-100 (5th)
            normalized_score = max(0, min(100, flesch_score))
            
            return {
                'flesch_score': round(flesch_score, 1),
                'fk_grade': round(fk_grade, 1),
                'normalized': round(normalized_score, 1),
                'interpretation': self.interpret_readability(flesch_score)
            }
        except:
            return {'flesch_score': 0, 'fk_grade': 0, 'normalized': 0, 'interpretation': 'Not enough text'}
    
    def interpret_readability(self, score):
        if score >= 90:
            return "Very Easy (5th grade)"
        elif score >= 80:
            return "Easy (6th grade)"
        elif score >= 70:
            return "Fairly Easy (7th grade)"
        elif score >= 60:
            return "Standard (8th-9th grade)"
        elif score >= 50:
            return "Fairly Difficult (High School)"
        elif score >= 30:
            return "Difficult (College)"
        else:
            return "Very Difficult (College Graduate)"
    
    def analyze_jargon(self, text):
        """Analyze technical jargon density"""
        # Lazy import to prevent heavy NLTK loading on startup
        from nltk.tokenize import word_tokenize
        words = word_tokenize(text.lower())
        
        # Remove punctuation and stop words
        words_clean = [word for word in words if word.isalnum() and word not in self.stop_words]
        
        if not words_clean:
            return 0
        
        # Count technical terms
        technical_count = sum(1 for word in words_clean if word in self.technical_terms)
        jargon_percentage = (technical_count / len(words_clean)) * 100
        
        return {
            'technical_count': technical_count,
            'total_words': len(words_clean),
            'percentage': round(jargon_percentage, 1),
            'level': self.interpret_jargon(jargon_percentage)
        }
    
    def interpret_jargon(self, percentage):
        if percentage < 8:  # Increased from 5
            return "Low (Beginner-friendly)"
        elif percentage < 20:  # Increased from 15
            return "Moderate (Intermediate)"
        else:
            return "High (Advanced)"
    
    def analyze_pacing(self, transcript_data):
        """Analyze how fast concepts are introduced"""
        if not transcript_data or len(transcript_data) < 10:
            return {'words_per_minute': 0, 'pacing': 'Unknown'}
        
        # Calculate words per minute (approx)
        total_words = sum(len(snippet.text.split()) for snippet in transcript_data)
        total_minutes = transcript_data[-1].start / 60 if hasattr(transcript_data[-1], 'start') else 1
        
        if total_minutes == 0:
            total_minutes = 1
            
        words_per_minute = total_words / total_minutes
        
        return {
            'words_per_minute': round(words_per_minute),
            'pacing': self.interpret_pacing(words_per_minute)
        }
    
    def interpret_pacing(self, wpm):
        if wpm < 160:  # Increased from 120
            return "Slow (Good for beginners)"
        elif wpm < 200:  # Increased from 180
            return "Moderate (Average)"
        else:
            return "Fast (Challenging for beginners)"
    
    def determine_skill_level(self, analysis_results):
        """Determine if video is Beginner/Intermediate/Advanced"""
        readability = analysis_results.get('readability', {}).get('normalized', 0)
        jargon = analysis_results.get('jargon', {}).get('percentage', 0)
        pacing = analysis_results.get('pacing', {}).get('words_per_minute', 0)
        
        score = 0
        
        # SCORING SYSTEM - ADJUSTED FOR TUTORIAL VIDEOS
        # Readability: Tutorials can be slightly complex but still beginner-friendly
        if readability > 50:  # Lowered from 60
            score += 3
        elif readability > 30:  # Lowered from 40
            score += 2
        else:
            score += 1
        
        # Jargon: Programming tutorials NEED some technical terms
        if jargon < 8:  # Increased from 5 (tutorials need terms like "variable", "function")
            score += 3
        elif jargon < 20:  # Increased from 15
            score += 2
        else:
            score += 1
        
        # Pacing: Tutorials can be faster paced
        if pacing < 160:  # Increased from 150
            score += 2
        elif pacing < 200:  # Increased from 180
            score += 1
        else:
            score += 0
        
        # ADJUSTED THRESHOLDS
        if score >= 6:  # Lowered from 7
            return "Beginner", score, "Excellent for beginners"
        elif score >= 4:  # Lowered from 4 (same)
            return "Intermediate", score, "Suitable for intermediate learners"
        else:
            return "Advanced", score, "Best for advanced learners"
    
    def determine_hindi_skill_level(self, analysis_results):
        """Special skill level determination for Hindi videos"""
        # Hindi videos often have different characteristics
        jargon = analysis_results.get('jargon', {}).get('percentage', 0)
        pacing = analysis_results.get('pacing', {}).get('words_per_minute', 0)
        
        score = 0
        
        # Hindi teaching is often more beginner-friendly
        # Adjust scoring for Hindi patterns
        if pacing < 180:  # Hindi tutorials often slower
            score += 3
        elif pacing < 220:
            score += 2
        else:
            score += 1
        
        if jargon < 10:  # Hindi might use more explanatory language
            score += 3
        elif jargon < 25:
            score += 2
        else:
            score += 1
        
        # Always add some points for Hindi (assume beginner-friendly)
        score += 2
        
        if score >= 6:
            return "Beginner", score, "हिंदी ट्यूटोरियल - शुरुआती के लिए उपयुक्त"
        elif score >= 4:
            return "Intermediate", score, "हिंदी ट्यूटोरियल - मध्यम स्तर के लिए"
        else:
            return "Advanced", score, "हिंदी ट्यूटोरियल - उन्नत स्तर के लिए"
    
    def analyze_transcript(self, transcript_text, transcript_data):
        """Main analysis function"""
        results = {}
        
        # 0. Detect language
        language = self.detect_language(transcript_text)
        results['language'] = language
        
        # 1. Readability analysis (skip for non-English)
        if language == 'en':
            results['readability'] = self.calculate_readability(transcript_text)
        else:
            results['readability'] = {
                'flesch_score': 'N/A',
                'fk_grade': 'N/A', 
                'normalized': 50,  # Default middle score for non-English
                'interpretation': f'Language: {language.upper()} (analysis limited)'
            }
        
        # 2. Jargon analysis (adjust for non-English)
        jargon_results = self.analyze_jargon(transcript_text)
        if language != 'en':
            jargon_results['level'] = f"Language: {language.upper()}"
        results['jargon'] = jargon_results
        
        # 3. Pacing analysis
        results['pacing'] = self.analyze_pacing(transcript_data)
        
        # 4. Determine skill level (adjust for non-English)
        if language == 'hi':
            # Hindi-specific analysis
            level, score, explanation = self.determine_hindi_skill_level(results)
        else:
            level, score, explanation = self.determine_skill_level(results)
        
        results['skill_level'] = level
        results['level_score'] = score
        results['level_explanation'] = explanation
        
        return results

class TopicDetector:
    def __init__(self):
        self.stop_words = set(stopwords.words('english'))
        # Common technical terms across domains
        self.technical_indicators = {
            'programming': ['code', 'function', 'variable', 'loop', 'algorithm', 'syntax', 'debug'],
            'data': ['data', 'analysis', 'dataset', 'visualization', 'statistic', 'chart', 'graph'],
            'design': ['design', 'layout', 'color', 'interface', 'ui', 'ux', 'prototype'],
            'business': ['business', 'marketing', 'finance', 'strategy', 'management', 'analysis'],
            'academic': ['theory', 'concept', 'principle', 'research', 'study', 'paper'],
            'practical': ['tutorial', 'guide', 'step', 'practice', 'exercise', 'project']
        }
    
    def detect_topics(self, transcript_text, title):
        """Dynamically detect topics from transcript"""
        # Combine title and transcript for better context
        full_text = f"{title} {transcript_text}".lower()
        
        # Extract key terms
        key_terms = self._extract_key_terms(full_text)
        
        # Categorize topics
        topics = self._categorize_topics(key_terms, full_text)
        
        # Determine domain
        domain = self._identify_domain(topics, full_text)
        
        return {
            'key_terms': key_terms,
            'topics': topics,
            'domain': domain,
            'is_technical': self._is_technical(full_text)
        }
    
    def _extract_key_terms(self, text, n=10):
        """Extract most frequent and meaningful terms"""
        # Lazy import to prevent heavy NLTK loading on startup
        from nltk.tokenize import word_tokenize
        # Tokenize and clean
        words = word_tokenize(text)
        words = [word.lower() for word in words if word.isalnum() and len(word) > 2]
        
        # Remove stopwords
        filtered = [word for word in words if word not in self.stop_words]
        
        # Count frequency
        word_freq = Counter(filtered)
        
        # Get most common (excluding generic terms)
        common_terms = word_freq.most_common(n + 20)
        
        # Filter out overly generic terms
        generic_terms = {'video', 'tutorial', 'learn', 'course', 'channel', 'like', 'subscribe'}
        meaningful = [(term, freq) for term, freq in common_terms 
                     if term not in generic_terms and freq > 1]
        
        return meaningful[:n]
    
    def _categorize_topics(self, key_terms, text):
        """Categorize into topic areas"""
        topics = set()
        
        # Check for programming/tech topics
        if any(term in text for term in ['python', 'javascript', 'java', 'code', 'program']):
            topics.add('programming')
        
        # Check for data topics
        if any(term in text for term in ['data', 'analysis', 'excel', 'spreadsheet', 'chart']):
            topics.add('data_analysis')
        
        # Check for creative topics
        if any(term in text for term in ['design', 'photoshop', 'edit', 'creative', 'art']):
            topics.add('creative')
        
        # Check for business topics
        if any(term in text for term in ['business', 'marketing', 'finance', 'excel', 'presentation']):
            topics.add('business')
        
        # Check difficulty level indicators
        if any(term in text for term in ['beginner', 'basic', 'introduction', 'start', 'first']):
            topics.add('beginner_level')
        elif any(term in text for term in ['advanced', 'expert', 'deep', 'complex', 'master']):
            topics.add('advanced_level')
        else:
            topics.add('intermediate_level')
        
        return list(topics)
    
    def _identify_domain(self, topics, text):
        """Identify the main domain/subject"""
        domain_indicators = {
            'programming': ['python', 'javascript', 'java', 'c++', 'html', 'css', 'react', 'django'],
            'data_science': ['data', 'machine learning', 'ai', 'analysis', 'excel', 'sql', 'statistics'],
            'web_dev': ['web', 'website', 'frontend', 'backend', 'html', 'css', 'javascript'],
            'design': ['photoshop', 'figma', 'ui', 'ux', 'design', 'graphic', 'illustrator'],
            'business': ['excel', 'marketing', 'finance', 'presentation', 'powerpoint', 'management'],
            'language': ['english', 'spanish', 'language', 'grammar', 'vocabulary', 'speaking']
        }
        
        for domain, indicators in domain_indicators.items():
            if any(indicator in text for indicator in indicators):
                return domain
        
        return 'general'
    
    def _is_technical(self, text):
        """Determine if content is technical"""
        technical_terms = ['code', 'function', 'variable', 'algorithm', 'syntax', 
                          'data', 'analysis', 'formula', 'equation', 'technical']
        return any(term in text for term in technical_terms)
    
    def generate_learning_summary(self, topics_info, skill_level, word_count):
        """Generate dynamic learning summary based on detected topics"""
        summary = []
        
        # Domain-specific summaries
        domain = topics_info['domain']
        if domain == 'programming':
            summary.append("💻 **Programming concepts and code examples**")
            summary.append("🔧 **Practical coding exercises and projects**")
        elif domain == 'data_science':
            summary.append("📊 **Data analysis techniques and tools**")
            summary.append("📈 **Visualization and interpretation methods**")
        elif domain == 'web_dev':
            summary.append("🌐 **Web development fundamentals**")
            summary.append("🖥️ **Building functional websites**")
        elif domain == 'design':
            summary.append("🎨 **Design principles and creative techniques**")
            summary.append("🖌️ **Practical design projects**")
        elif domain == 'business':
            summary.append("📈 **Business tools and analysis methods**")
            summary.append("💼 **Practical business applications**")
        else:
            summary.append("📚 **Core concepts and practical applications**")
        
        # Add key topics from detection
        if topics_info['key_terms']:
            key_topics = [term for term, freq in topics_info['key_terms'][:3]]
            summary.append(f"🎯 **Focus areas:** {', '.join(key_topics)}")
        
        # Prerequisites based on level and domain
        if skill_level == 'Beginner':
            summary.append("📝 **Prerequisites:** No prior experience needed")
        elif topics_info['is_technical']:
            if domain == 'programming':
                summary.append("📝 **Prerequisites:** Basic computer literacy, logical thinking")
            elif domain == 'data_science':
                summary.append("📝 **Prerequisites:** Basic math understanding, analytical mindset")
            else:
                summary.append("📝 **Prerequisites:** Foundational knowledge in the subject")
        else:
            summary.append("📝 **Prerequisites:** Interest and willingness to learn")
        
        # Length indicator
        if word_count > 30000:
            summary.append("⏳ **Comprehensive coverage** - In-depth exploration")
        elif word_count > 15000:
            summary.append("⏳ **Detailed tutorial** - Thorough explanation with examples")
        else:
            summary.append("⏳ **Quick overview** - Concise introduction to key concepts")
        
        return summary
