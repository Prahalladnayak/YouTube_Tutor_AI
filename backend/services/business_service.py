# backend/services/business_service.py
import re
from collections import Counter
from googleapiclient.discovery import build
from ai_services.ml.analysis_service import TopicDetector

class ChapterExtractor:
    def extract_chapters_from_description(self, description):
        """Extract timestamps and chapters from video description"""
        if not description:
            return []
        
        chapters = []
        
        # Multiple patterns for timestamps
        patterns = [
            r'(\d{1,3}:\d{2})\s*[-–]\s*(.+)',  # 00:00 - Topic
            r'(\d{1,3}:\d{2}:\d{2})\s*[-–]\s*(.+)',  # 00:00:00 - Topic
            r'(\d{1,3})\s*[:.]\s*(\d{2})\s*[-–]\s*(.+)',  # 0:00 - Topic
            r'^(\d{1,3}:\d{2})\s+(.+)',  # 00:00 Topic (no dash)
        ]
        
        for line in description.split('\n'):
            line = line.strip()
            if not line:
                continue
            
            for pattern in patterns:
                match = re.search(pattern, line)
                if match:
                    if len(match.groups()) == 2:
                        time, topic = match.groups()
                    else:
                        time = f"{match.group(1)}:{match.group(2)}"
                        topic = match.group(3)
                    
                    # Clean up topic
                    topic = self._clean_topic(topic)
                    
                    # Only add if meaningful topic (not just "Intro" etc.)
                    if len(topic) > 3 and not self._is_generic_topic(topic):
                        chapters.append({
                            'time': time.strip(),
                            'topic': topic,
                            'full_line': line
                        })
                    break
        
        return chapters
    
    def _clean_topic(self, topic):
        """Clean and format topic title"""
        # Remove extra symbols
        topic = re.sub(r'[\[\](){}|]', '', topic)
        
        # Capitalize first letter of each word (for short topics)
        if len(topic.split()) <= 5:
            topic = ' '.join(word.capitalize() for word in topic.split())
        
        return topic.strip()
    
    def _is_generic_topic(self, topic):
        """Check if topic is too generic"""
        generic_terms = {'intro', 'introduction', 'outro', 'conclusion', 
                        'summary', 'recap', 'welcome', 'thanks', 'thank you',
                        'end', 'start', 'beginning', 'closing'}
        
        return topic.lower() in generic_terms
    
    def generate_learning_summary_from_chapters(self, chapters, video_title):
        """Generate 'What You'll Learn' from actual chapters"""
        if not chapters:
            return self._generate_fallback_summary(video_title)
        
        summary = []
        
        # Add header
        summary.append("📋 **What You'll Learn (Video Chapters):**")
        
        # Add top 5-7 most important chapters (skip intro/outro)
        meaningful_chapters = [c for c in chapters 
                             if not self._is_generic_topic(c['topic'])]
        
        for i, chapter in enumerate(meaningful_chapters[:7]):
            summary.append(f"⏱️ **{chapter['time']}** - {chapter['topic']}")
        
        # If we have chapters, we can infer prerequisites
        if meaningful_chapters:
            tech_terms = self._extract_tech_terms([c['topic'] for c in meaningful_chapters])
            if tech_terms:
                summary.append(f"🔧 **Covers:** {', '.join(tech_terms[:3])}")
        
        # Estimate prerequisites based on content
        if any(term in video_title.lower() for term in ['advanced', 'expert', 'master']):
            summary.append("📝 **Prerequisites:** Solid foundational knowledge required")
        elif any(term in video_title.lower() for term in ['beginner', 'basics', 'introduction']):
            summary.append("📝 **Prerequisites:** No prior experience needed")
        else:
            summary.append("📝 **Prerequisites:** Basic understanding helpful")
        
        return summary
    
    def _extract_tech_terms(self, topics):
        """Extract technical terms from chapter topics"""
        common_tech_terms = {
            'python', 'javascript', 'react', 'django', 'flask', 'html', 'css',
            'machine learning', 'ai', 'data science', 'analysis', 'visualization',
            'langchain', 'llm', 'vector', 'database', 'api', 'web', 'mobile',
            'design', 'ui', 'ux', 'photoshop', 'figma', 'excel', 'powerpoint'
        }
        
        found_terms = []
        for topic in topics:
            topic_lower = topic.lower()
            for term in common_tech_terms:
                if term in topic_lower:
                    found_terms.append(term)
        
        return list(set(found_terms))
    
    def _generate_fallback_summary(self, video_title):
        """Fallback if no chapters found"""
        summary = []
        summary.append("📋 **Course Content Overview**")
        
        # Generic based on title keywords
        title_lower = video_title.lower()
        
        if 'python' in title_lower:
            summary.append("🐍 **Python programming concepts**")
            summary.append("💻 **Hands-on coding examples**")
        elif 'data' in title_lower or 'analysis' in title_lower:
            summary.append("📊 **Data analysis techniques**")
            summary.append("📈 **Practical data applications**")
        elif 'web' in title_lower:
            summary.append("🌐 **Web development fundamentals**")
            summary.append("🖥️ **Building functional websites**")
        elif 'design' in title_lower:
            summary.append("🎨 **Design principles and techniques**")
            summary.append("🖌️ **Creative project work**")
        else:
            summary.append("📚 **Core concepts and practical skills**")
            summary.append("🔧 **Step-by-step implementation**")
        
        summary.append("📝 **Prerequisites:** Willingness to learn and practice")
        
        return summary


class ExplanationService:
    def generate_why_this_video(self, video, target_level):
        """Generate detailed explanation of why this video is recommended"""
        
        level = video['skill_level']
        readability = video['analysis']['readability'].get('flesch_score', 0)
        jargon = video['analysis']['jargon'].get('percentage', 0)
        pacing = video['analysis']['pacing'].get('words_per_minute', 0)
        comments = video['analysis'].get('comments', {})
        
        # Get the recommendation score (8/8 from your table)
        score = video.get('recommendation_score', 0)
        score_percentage = min(int((score / 100) * 8), 8)  # Convert to 8/8 scale
        
        explanations = []
        
        # 1. Score-based explanation
        if score_percentage >= 7:
            explanations.append(f"🏆 **Top-rated choice** - Scored {score_percentage}/8, highest among compared videos")
        elif score_percentage >= 5:
            explanations.append(f"✅ **Solid pick** - Scored {score_percentage}/8 based on multiple factors")
        else:
            explanations.append(f"⚖️ **Balanced option** - Scored {score_percentage}/8, best available match")
            
        # 2. Level match explanation
        if level.lower() == target_level:
            explanations.append("🎯 **Perfect level match** - This video is exactly at your selected skill level")
        else:
            level_distance = self._get_level_distance(level.lower(), target_level)
            if level_distance == 1:
                explanations.append(f"🎯 **Good fit** - This {level} video is close to your requested {target_level} level")
            else:
                explanations.append(f"🎯 **Alternative option** - While you requested {target_level}, this {level} video is the closest match available")
        
        # 3. Readability explanation
        if readability != 'N/A':
            if readability > 70:
                explanations.append("📚 **Easy to understand** - Uses simple language and clear explanations")
            elif readability > 50:
                explanations.append("📚 **Moderate difficulty** - Balanced language suitable for learning")
            else:
                explanations.append("📚 **Challenging content** - Uses complex language, best for focused learners")
        
        # 4. Jargon explanation
        if jargon < 5:
            explanations.append("🔤 **Beginner-friendly terminology** - Minimal technical jargon, easy to follow")
        elif jargon < 15:
            explanations.append("🔤 **Moderate technical terms** - Introduces concepts with appropriate terminology")
        else:
            explanations.append("🔤 **Technical focus** - Uses specialized terms for in-depth learning")
        
        # 5. Pacing explanation
        if pacing < 140:
            explanations.append("⏱️ **Comfortable pace** - Speaks slowly enough for beginners to follow")
        elif pacing < 180:
            explanations.append("⏱️ **Balanced speed** - Good pace for most learners")
        else:
            explanations.append("⏱️ **Fast-paced** - Quick delivery, best for experienced learners")
        
        # 6. Comments explanation
        if comments.get('total_comments', 0) > 0:
            if comments.get('sentiment') == 'Positive':
                understanding = comments.get('understanding_score', 0)
                if understanding > 20:
                    explanations.append(f"💬 **Highly praised** - {understanding}% of viewers found it clear and helpful")
                else:
                    explanations.append("💬 **Positive feedback** - Viewers generally found it useful")
            elif comments.get('sentiment') == 'Confusing':
                confusion = comments.get('confusion_score', 0)
                explanations.append(f"💬 **Some confusion** - {confusion}% of viewers found parts difficult")
        
        # 7. Length explanation
        word_count = video.get('word_count', 0)
        if word_count > 30000:
            explanations.append("📏 **Comprehensive coverage** - Detailed, in-depth tutorial")
        elif word_count > 10000:
            explanations.append("📏 **Moderate length** - Balanced coverage of topics")
        else:
            explanations.append("📏 **Concise tutorial** - Quick overview of concepts")
        
        return explanations
    
    def _get_level_distance(self, video_level, target_level):
        """Calculate distance between levels"""
        levels = {'beginner': 0, 'intermediate': 1, 'advanced': 2}
        return abs(levels.get(video_level, 1) - levels.get(target_level, 1))
    
    def _get_domain_specific_tips(self, domain):
        """Get domain-specific learning tips"""
        tips = {
            'programming': [
                "💻 **Code along** - Type the code yourself as you watch",
                "🐛 **Debug actively** - Don't just copy, understand why things work",
                "🔁 **Practice variations** - Modify the code to try different approaches"
            ],
            'data_science': [
                "📊 **Use your own data** - Apply techniques to datasets you care about",
                "📈 **Visualize everything** - Create charts to understand patterns",
                "🔍 **Ask questions** - Formulate hypotheses before analyzing"
            ],
            'web_dev': [
                "🌐 **Build alongside** - Create a real project as you learn",
                "🛠️ **Inspect elements** - Use browser dev tools to see how things work",
                "📱 **Test responsiveness** - Check how sites work on different devices"
            ],
            'design': [
                "🎨 **Sketch first** - Plan your designs on paper before digital",
                "👁️ **Study references** - Analyze designs you admire to learn techniques",
                "🔄 **Iterate often** - Create multiple versions to find the best solution"
            ],
            'business': [
                "📈 **Apply immediately** - Use techniques on real business problems",
                "💼 **Case studies** - Analyze how successful companies use these methods",
                "📊 **Measure results** - Track the impact of what you implement"
            ]
        }
        
        return tips.get(domain, [
            "📝 **Take notes** - Write down key concepts and timestamps",
            "🔁 **Review regularly** - Revisit difficult sections multiple times",
            "💭 **Think critically** - Ask yourself why things work the way they do",
            "🔄 **Apply knowledge** - Use what you learn in practical situations"
        ])
    
    def generate_pre_watch_summary(self, video):
        """Generate what you'll learn from ACTUAL video chapters"""
        description = video.get('description', '')
        title = video['title']
        
        # Initialize chapter extractor
        chapter_extractor = ChapterExtractor()
        
        # Extract actual chapters from description
        chapters = chapter_extractor.extract_chapters_from_description(description)
        
        # Generate summary from REAL chapters
        if chapters:
            return chapter_extractor.generate_learning_summary_from_chapters(chapters, title)
        else:
            return self._generate_honest_summary(video)
    
    def _generate_honest_summary(self, video):
        """Return honest summary when we can't extract chapters"""
        summary = []
        summary.append("📋 **What You'll Learn:**")
        
        # Just show what we actually know from the title
        title_lower = video['title'].lower()
        
        if any(term in title_lower for term in ['python', 'programming', 'code']):
            summary.append("💻 **Programming concepts and examples**")
        elif any(term in title_lower for term in ['data', 'analysis', 'visualization']):
            summary.append("📊 **Data-related techniques**")
        elif any(term in title_lower for term in ['web', 'html', 'css', 'javascript']):
            summary.append("🌐 **Web development topics**")
        elif any(term in title_lower for term in ['langchain', 'llm', 'ai', 'machine learning']):
            summary.append("🤖 **AI and language model concepts**")
        else:
            summary.append("📚 **Content based on the video title**")
        
        summary.append("ℹ️ **Note:** Based on video title analysis")
        summary.append("📝 **Watch the video to see actual content**")
        
        return summary


class LearningPathService:
    def generate_learning_path(self, video_title, chapters, skill_level, word_count):
        """Generate universal learning path that works for ANY subject"""
        content_type = self._analyze_content_type(video_title, chapters, word_count)
        return self._generate_universal_guidance(video_title, content_type, skill_level)
    
    def _analyze_content_type(self, video_title, chapters, word_count):
        """Analyze what type of learning content this is"""
        title_lower = video_title.lower()
        
        # Check content depth
        if word_count > 20000:
            depth = 'comprehensive'
        elif word_count > 8000:
            depth = 'detailed'
        else:
            depth = 'overview'
        
        # Check content style
        if any(word in title_lower for word in ['project', 'build', 'create', 'make']):
            style = 'project-based'
        elif any(word in title_lower for word in ['tutorial', 'guide', 'how to']):
            style = 'tutorial'
        elif any(word in title_lower for word in ['theory', 'concept', 'fundamental']):
            style = 'theoretical'
        elif any(word in title_lower for word in ['crash course', 'fast', 'quick']):
            style = 'quick-start'
        else:
            style = 'general'
        
        has_structure = len(chapters) > 3
        
        return {
            'depth': depth,
            'style': style,
            'has_structure': has_structure,
            'chapter_count': len(chapters)
        }
    
    def _generate_universal_guidance(self, video_title, content_type, skill_level):
        """Generate guidance that works for ANY subject"""
        guidance = []
        
        # Header
        guidance.append("📚 **Your Learning Journey Guide**")
        guidance.append(f"🎯 **Video:** {video_title}")
        guidance.append("")
        
        # Part 1: How to study THIS video
        guidance.append("👨‍🏫 **How to Get the Most from This Video:**")
        guidance.append("")
        
        if content_type['depth'] == 'overview':
            guidance.append("• **This is an overview** - Don't expect mastery")
            guidance.append("• **Take notes on key concepts** - Focus on the big picture")
            guidance.append("• **Identify what interests you** - Note topics to explore deeper")
        elif content_type['depth'] == 'detailed':
            guidance.append("• **This is detailed content** - Set aside focused time")
            guidance.append("• **Practice as you watch** - Pause and implement")
            guidance.append("• **Bookmark complex sections** - Return to them later")
        else:  # comprehensive
            guidance.append("• **This is comprehensive** - Break into multiple sessions")
            guidance.append("• **Create a study schedule** - 30-60 minute chunks")
            guidance.append("• **Review previous sections** - Before starting new ones")
        
        if content_type['has_structure']:
            guidance.append("• **Use the chapter timestamps** - Jump to what you need")
            guidance.append("• **Focus on core chapters** - Skip intro/outro if needed")
        
        guidance.append("")
        
        # Part 2: What to do AFTER this video (Universal progression)
        guidance.append("🎯 **Your Next Learning Steps:**")
        guidance.append("")
        
        # Universal learning progression
        guidance.append("1. **Immediate Practice (Next 24 hours)**")
        guidance.append("   → Apply what you learned immediately")
        guidance.append("   → Even if it's small, make it complete")
        guidance.append("")
        
        guidance.append("2. **Deepen Understanding (This week)**")
        
        if skill_level.lower() == 'beginner':
            guidance.append("   → Find 2-3 more beginner videos on this topic")
            guidance.append("   → Different explanations help understanding")
        elif skill_level.lower() == 'intermediate':
            guidance.append("   → Find a project tutorial using these concepts")
            guidance.append("   → Build something real, not just follow along")
        else:  # advanced
            guidance.append("   → Read official documentation or research papers")
            guidance.append("   → Explore edge cases and limitations")
        
        guidance.append("")
        
        guidance.append("3. **Build Portfolio (This month)**")
        guidance.append("   → Create something showcase-worthy")
        guidance.append("   → Document your learning journey")
        guidance.append("   → Share with community for feedback")
        guidance.append("")
        
        # Part 3: Universal learning principles
        guidance.append("💡 **Universal Learning Principles:**")
        guidance.append("")
        guidance.append("• **Spaced Repetition:** Review after 1 day, 1 week, 1 month")
        guidance.append("• **Active Recall:** Test yourself without looking at notes")
        guidance.append("• **Interleaving:** Mix different but related topics")
        guidance.append("• **Deliberate Practice:** Focus on your weak areas")
        guidance.append("• **Teach Others:** The best way to learn is to teach")
        guidance.append("")
        
        # Part 4: Subject-specific if we can detect
        detected_subjects = self._detect_possible_subjects(video_title)
        if detected_subjects:
            main_subject = detected_subjects[0].upper()  # Get first detected subject
            guidance.append(f"🔍 **Detected Field:** {main_subject}")
            guidance.append(f"   → Search for: '{main_subject} projects for beginners'")
            guidance.append(f"   → Join: '{main_subject} learning communities'")
            guidance.append(f"   → Follow: Top {main_subject} educators on YouTube")
        
        guidance.append("")
        guidance.append("🌟 **Remember:** Learning is a marathon, not a sprint. Consistency > Intensity.")
        
        return guidance
    
    def _detect_possible_subjects(self, video_title):
        """Try to detect subject for slightly personalized tips"""
        title_lower = video_title.lower()
        subjects = []
        
        subject_keywords = {
            'programming': ['python', 'javascript', 'java', 'c++', 'coding', 'program'],
            'data': ['sql', 'excel', 'analysis', 'visualization', 'power bi'],
            'web': ['html', 'css', 'react', 'website', 'frontend'],
            'ai': ['machine learning', 'ai', 'neural', 'llm', 'langchain'],
            'design': ['photoshop', 'figma', 'ui', 'ux', 'design'],
            'business': ['excel', 'powerpoint', 'marketing', 'finance']
        }
        
        for subject, keywords in subject_keywords.items():
            for keyword in keywords:
                if keyword in title_lower:
                    subjects.append(subject)
                    break
        
        return list(set(subjects))


class CommentsAnalyzer:
    def __init__(self, api_key):
        self.youtube = build('youtube', 'v3', developerKey=api_key)
        
        # Keywords that indicate understanding
        self.understanding_keywords = [
            'thanks', 'thank you', 'helpful', 'understood', 'clear',
            'explained well', 'good explanation', 'easy to understand',
            'samajh aa gaya', 'achha hai', 'bahut badhiya', 'shukriya'
        ]
        
        # Keywords that indicate confusion
        self.confusion_keywords = [
            'confusing', 'not clear', 'difficult', 'hard to understand',
            'did not understand', 'can you explain', 'samajh nahi aaya',
            'mujhe samajh nahi aaya', 'confuse', 'complicated'
        ]
    
    def analyze_video_comments(self, video_id, max_comments=100):
        """Analyze comments for sentiment and understanding"""
        try:
            comments = []
            request = self.youtube.commentThreads().list(
                part="snippet",
                videoId=video_id,
                maxResults=max_comments,
                textFormat="plainText"
            )
            
            response = request.execute()
            
            for item in response.get('items', []):
                comment = item['snippet']['topLevelComment']['snippet']['textDisplay']
                comments.append(comment.lower())
            
            if not comments:
                return {
                    'total_comments': 0,
                    'understanding_score': 0,
                    'confusion_score': 0,
                    'sentiment': 'No comments'
                }
            
            understanding_count = 0
            confusion_count = 0
            
            for comment in comments:
                for keyword in self.understanding_keywords:
                    if keyword in comment:
                        understanding_count += 1
                        break
                
                for keyword in self.confusion_keywords:
                    if keyword in comment:
                        confusion_count += 1
                        break
            
            total_analyzed = len(comments)
            understanding_score = (understanding_count / total_analyzed) * 100
            confusion_score = (confusion_count / total_analyzed) * 100
            
            if understanding_score > confusion_score:
                sentiment = "Positive"
            elif confusion_score > understanding_score:
                sentiment = "Confusing"
            else:
                sentiment = "Mixed"
            
            return {
                'total_comments': total_analyzed,
                'understanding_score': round(understanding_score, 1),
                'confusion_score': round(confusion_score, 1),
                'sentiment': sentiment,
                'sample_comments': comments[:3]
            }
            
        except Exception as e:
            return {
                'error': str(e),
                'total_comments': 0,
                'understanding_score': 0,
                'confusion_score': 0,
                'sentiment': 'Error'
            }
