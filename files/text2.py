# corpus_from_unstructured.py - Without Mistral dependency
import os
import re
import string
import random
from collections import Counter, defaultdict
from math import log

class TextAnalyzer:
    """Simple NLP-based text analyzer to extract structured information from unstructured text"""
    
    def __init__(self):
        """Initialize with basic NLP tools"""
        self.stopwords = set([
            'a', 'an', 'the', 'and', 'or', 'but', 'if', 'because', 'as', 'what',
            'when', 'where', 'how', 'that', 'this', 'these', 'those', 'then',
            'so', 'than', 'such', 'both', 'through', 'about', 'for', 'is', 'of',
            'while', 'during', 'to', 'from', 'in', 'out', 'on', 'off', 'with',
            'by', 'at', 'up', 'down', 'be', 'been', 'being', 'have', 'has', 'had',
            'do', 'does', 'did', 'will', 'would', 'shall', 'should', 'can', 'could',
            'may', 'might', 'must', 'it', 'its', 'it\'s', 'they', 'them', 'their',
            'we', 'us', 'our', 'he', 'him', 'his', 'she', 'her', 'i', 'me', 'my',
            'was', 'were', 'am'
        ])
        
        # Common content types for categorization
        self.content_types = [
            "Documentation", "Guide", "Tutorial", "Reference", "Overview",
            "Best Practice", "Policy", "Standard", "Example", "Template",
            "Glossary", "Article", "Report", "Procedure", "Specification"
        ]
    
    def preprocess_text(self, text):
        """Clean and normalize text for analysis"""
        if not text:
            return ""
            
        # Convert to lowercase
        text = text.lower()
        
        # Remove punctuation
        text = text.translate(str.maketrans('', '', string.punctuation))
        
        # Remove extra whitespace
        text = ' '.join(text.split())
        
        return text
    
    def extract_keywords(self, text, top_n=10):
        """Extract important keywords using TF-IDF-like approach"""
        if not text:
            return []
            
        # Preprocess the text
        processed_text = self.preprocess_text(text)
        
        # Tokenize
        tokens = processed_text.split()
        
        # Remove stopwords
        filtered_tokens = [token for token in tokens if token not in self.stopwords and len(token) > 2]
        
        # Count term frequency
        term_freq = Counter(filtered_tokens)
        
        # Get document length for normalization
        doc_length = len(filtered_tokens) or 1  # Avoid division by zero
        
        # Calculate score based on term frequency and position
        keyword_scores = {}
        
        # Give higher weight to words appearing in the first third of the document
        first_third_tokens = set(filtered_tokens[:max(1, doc_length//3)])
        
        for token, count in term_freq.items():
            # Base score is frequency
            score = count / doc_length
            
            # Bonus for words in the beginning (likely more important)
            if token in first_third_tokens:
                score *= 1.5
                
            # Bonus for longer words (often more informative)
            if len(token) > 5:
                score *= 1.2
                
            keyword_scores[token] = score
        
        # Get top keywords
        top_keywords = sorted(keyword_scores.items(), key=lambda x: x[1], reverse=True)[:top_n]
        return [kw[0] for kw in top_keywords]
    
    def extract_categories(self, text, keywords=None):
        """Determine the main category of the text"""
        if not text:
            return "General"
            
        if keywords is None:
            keywords = self.extract_keywords(text, top_n=5)
            
        # Define some common category patterns
        category_patterns = {
            'data': ['data', 'database', 'analytics', 'information', 'dataset'],
            'machine learning': ['model', 'train', 'predict', 'ml', 'algorithm', 'machine learning'],
            'api': ['api', 'endpoint', 'request', 'response', 'rest', 'call'],
            'security': ['secure', 'auth', 'permission', 'access', 'protect'],
            'infrastructure': ['cloud', 'server', 'container', 'kubernetes', 'docker'],
            'guidelines': ['guide', 'best practice', 'recommend', 'should', 'policy'],
            'development': ['code', 'program', 'develop', 'software', 'app'],
            'documentation': ['document', 'manual', 'refer', 'instruct'],
            'testing': ['test', 'quality', 'validation', 'verify'],
            'integration': ['connect', 'integrate', 'pipeline', 'workflow'],
            'governance': ['governance', 'compliance', 'regulation', 'legal'],
        }
        
        # Score each category based on keyword matches
        category_scores = defaultdict(int)
        
        # Calculate overlaps between extracted keywords and category patterns
        for category, patterns in category_patterns.items():
            for keyword in keywords:
                for pattern in patterns:
                    if keyword in pattern or pattern in keyword:
                        category_scores[category] += 1
        
        # If we have a clear winner, return it
        if category_scores:
            best_category = max(category_scores.items(), key=lambda x: x[1])
            if best_category[1] > 0:
                return best_category[0].title()
        
        # Fallback to analyzing raw text for category names
        processed_text = self.preprocess_text(text)
        
        for category in category_patterns:
            if category in processed_text:
                return category.title()
        
        # Default category if no matches found
        return "General"
    
    def generate_title(self, text, keywords=None):
        """Generate a concise title from the text"""
        if not text:
            return "Untitled Document"
            
        if keywords is None:
            keywords = self.extract_keywords(text, top_n=5)
        
        # Split text into sentences more robustly
        sentences = re.split(r'(?<=[.!?])\s+', text)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        if not sentences:
            return " ".join(keywords[:3]).title() if keywords else "Untitled Document"
        
        first_sentence = sentences[0].strip()
        
        # If first sentence is too long, try to find a better one with keywords
        if len(first_sentence) > 60:
            for keyword in keywords[:3]:
                for sentence in sentences[:3]:  # Check first few sentences
                    if keyword in sentence.lower():
                        # Get a clean version of this sentence
                        clean_sentence = sentence.strip()
                        
                        # Remove common prefixes
                        clean_sentence = re.sub(r'^(This|The|In this|In the|Here|We|I|Our).*?(:|,|\s-)\s*', '', 
                                             clean_sentence, flags=re.IGNORECASE)
                        
                        # Truncate if still too long
                        if len(clean_sentence) > 60:
                            # Try to truncate at a word boundary
                            last_space = clean_sentence[:57].rfind(' ')
                            if last_space > 30:  # Don't cut too short
                                clean_sentence = clean_sentence[:last_space] + "..."
                            else:
                                clean_sentence = clean_sentence[:57] + "..."
                        
                        if clean_sentence:  # Make sure we have something
                            return clean_sentence
            
            # If no good sentence found with keywords, use truncated first sentence
            last_space = first_sentence[:57].rfind(' ')
            if last_space > 30:
                return first_sentence[:last_space] + "..."
            return first_sentence[:57] + "..."
        else:
            # Clean up the first sentence
            title = first_sentence
            # Remove common prefixes
            title = re.sub(r'^(This|The|In this|In the|Here|We|I|Our).*?(:|,|\s-)\s*', '', title, flags=re.IGNORECASE)
            
            # If cleaning made it empty, use original
            if not title.strip():
                title = first_sentence
                
            return title
    
    def generate_description(self, text, max_length=300):
        """Generate a short description summarizing the text"""
        if not text:
            return "No description available"
            
        # Split text into sentences more robustly
        sentences = re.split(r'(?<=[.!?])\s+', text)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        if not sentences:
            return "No description available"
        
        # Take first few sentences that form a reasonable description
        description = ""
        for sentence in sentences[:8]:  # Check first 8 sentences
            potential_desc = description + (" " if description else "") + sentence
            if len(potential_desc) <= max_length:
                description = potential_desc
            else:
                # Try to add a partial sentence if we have space
                remaining_space = max_length - len(description)
                if remaining_space > 30:  # Only add if we have reasonable space
                    # Find a good cut-off point
                    last_space = sentence[:remaining_space-3].rfind(' ')
                    if last_space > 0:
                        description += (" " if description else "") + sentence[:last_space] + "..."
                break
                
        if not description:  # If no sentences were short enough
            # Find a good cut-off point
            last_space = sentences[0][:max_length-3].rfind(' ')
            if last_space > max_length // 2:
                description = sentences[0][:last_space] + "..."
            else:
                description = sentences[0][:max_length-3] + "..."
        
        return description
    
    def infer_content_type(self, text, keywords=None):
        """Infer the type of content (documentation, guide, etc.)"""
        if not text:
            return "Documentation"  # Default
            
        if keywords is None:
            keywords = self.extract_keywords(text, top_n=7)
        
        processed_text = self.preprocess_text(text)
        
        # Look for content type indicators in the text
        for content_type in self.content_types:
            if content_type.lower() in processed_text:
                return content_type
        
        # Use heuristics based on text structure and keywords
        tutorial_indicators = ['step', 'tutorial', 'guide', 'how to', 'learn', 'example']
        doc_indicators = ['document', 'reference', 'manual', 'overview', 'introduction']
        policy_indicators = ['policy', 'rule', 'governance', 'standard', 'comply', 'regulation']
        report_indicators = ['report', 'analysis', 'finding', 'result', 'assessment', 'scan']
        
        # Check for content type indicators in keywords
        for keyword in keywords:
            for indicator in tutorial_indicators:
                if indicator in keyword:
                    return "Tutorial"
            for indicator in doc_indicators:
                if indicator in keyword:
                    return "Documentation"
            for indicator in policy_indicators:
                if indicator in keyword:
                    return "Policy"
            for indicator in report_indicators:
                if indicator in keyword:
                    return "Report"
        
        # Check for instructional language
        if re.search(r'(step|first|then|next|finally|follow|execute|run)', processed_text):
            return "Guide"
            
        # Check for reference patterns
        if re.search(r'(refer|consult|see|check|information about)', processed_text):
            return "Reference"
            
        return "Documentation"  # Default
    
    def analyze_text(self, text):
        """Full analysis of text to extract structured information"""
        if not text:
            return {
                "category_text": "General",
                "tags_list_text": [],
                "title_text": "Untitled Document",
                "description_text": "No description available",
                "tower_option_tower": "Documentation"
            }
            
        # Limit text size for processing, but use more content
        text = text[:20000]  # Increased from 10000
        
        # Extract keywords first as they're used in other functions
        keywords = self.extract_keywords(text, top_n=10)
        
        # Build the entity structure
        entity = {
            "category_text": self.extract_categories(text, keywords),
            "tags_list_text": keywords[:7],  # Use top 7 keywords as tags
            "title_text": self.generate_title(text, keywords),
            "description_text": self.generate_description(text),
            "tower_option_tower": self.infer_content_type(text, keywords)
        }
        
        return entity

def process_full_text(input_text, batch_size=10):
    """
    Process the entire text content in sections
    Returns a list of structured sections ready for database entries
    """
    print(" Analyzing full text content...")
    
    if not input_text:
        print(" Warning: Empty input text provided")
        return []
    
    # Split the text into meaningful sections - improved splitting logic
    sections = []
    
    # Try different splitting approaches based on document structure
    potential_sections = re.split(r'\n\s*\n', input_text)  # Split by double newlines
    
    # If we don't get reasonable sections, try splitting by headers
    if len(potential_sections) <= 2:
        potential_sections = re.split(r'\n\s*#+\s+', input_text)
        # Add back the headers that were removed in the split
        if len(potential_sections) > 1:
            for i in range(1, len(potential_sections)):
                potential_sections[i] = "# " + potential_sections[i]
    
    # Filter out sections that are too small
    for section in potential_sections:
        if len(section.strip()) > 100:
            sections.append(section.strip())
    
    # If we still don't have good sections, create some based on length
    if len(sections) <= 1 and len(input_text) > 1000:
        # Split into roughly equal chunks
        chunk_size = 1000
        for i in range(0, len(input_text), chunk_size):
            chunk = input_text[i:i+chunk_size]
            if len(chunk.strip()) > 100:
                sections.append(chunk.strip())
    
    print(f" Found {len(sections)} content sections to process")
    
    # Initialize text analyzer
    analyzer = TextAnalyzer()
    
    # Process each section
    structured_sections = []
    
    for idx, section in enumerate(sections):
        print(f" Processing section {idx + 1}/{len(sections)}")
        try:
            entities = analyzer.analyze_text(section)
            structured_sections.append(entities)
        except Exception as e:
            print(f"⚠️ Error processing section {idx + 1}: {str(e)}")
            # Create a basic entry for failed sections
            structured_sections.append({
                "category_text": "General",
                "tags_list_text": ["error", "processing", "failed"],
                "title_text": f"Section {idx + 1}",
                "description_text": "This section could not be processed due to an error.",
                "tower_option_tower": "Documentation"
            })
    
    return structured_sections

def escape_string_for_json(text):
    """
    Escape special characters in strings for JSON output
    """
    if not text:
        return ""
    
    # Replace single quotes with escaped single quotes
    text = text.replace("'", "\\'")
    
    # Replace other problematic characters
    text = text.replace("\n", " ")
    text = text.replace("\r", " ")
    text = text.replace("\t", " ")
    
    # Collapse multiple spaces
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text

def generate_corpus(input_text, output_file="repository3.txt", start_id=2000):
    """
    Process unstructured text into the required corpus format with numeric IDs
    """
    print(" Starting corpus generation...")
    
    if not input_text:
        print(" Error: Empty input text provided. Aborting.")
        return
    
    print(" Reading and processing full text content...")
    
    # Process the entire text
    structured_sections = process_full_text(input_text)
    
    if not structured_sections:
        print(" Error: No sections were extracted from the input text.")
        return
    
    print(f"\n Text analysis complete. Creating {len(structured_sections)} database entries...")
    
    # Create formatted entries for output
    entries = []
    for idx, entities in enumerate(structured_sections):
        try:
            # Format tags as duplicated values like in the example
            tag_strings = []
            for tag in entities["tags_list_text"]:
                # Escape the tag text
                escaped_tag = escape_string_for_json(tag)
                tag_strings.append(f'"{escaped_tag}", "{escaped_tag}"')
            
            tags_str = ", ".join(tag_strings)
            
            # Use sequential IDs starting from start_id
            entry_id = start_id + idx
            
            # Escape all text fields
            title = escape_string_for_json(entities['title_text'])
            description = escape_string_for_json(entities['description_text'])
            category = escape_string_for_json(entities['category_text'])
            tower = escape_string_for_json(entities['tower_option_tower'])
            
            # Format entry exactly like in repository2.txt
            entry = f"{entry_id}~~{{'title_text': '{title}', 'description_text': '{description}', 'tags_list_text': [{tags_str}], 'category_text': '{category}', 'tower_option_tower': '{tower}'}}"
            entries.append(entry)
        except Exception as e:
            print(f" Error formatting entry {idx + 1}: {str(e)}")
            # Create a basic entry for failed sections
            entry_id = start_id + idx
            entry = f"{entry_id}~~{{'title_text': 'Entry {entry_id}', 'description_text': 'This entry could not be formatted properly.', 'tags_list_text': [\"error\", \"error\"], 'category_text': 'General', 'tower_option_tower': 'Documentation'}}"
            entries.append(entry)

    try:
        with open(output_file, "w", encoding="utf-8") as f:
            f.write("\n".join(entries))
        print(f"\n Generated corpus with {len(entries)} entries in {output_file}")
        print(f" Output saved to {output_file}")
    except Exception as e:
        print(f" Error writing to output file: {str(e)}")
        print(" Attempting to save to backup file...")
        try:
            backup_file = output_file + ".backup"
            with open(backup_file, "w", encoding="utf-8") as f:
                f.write("\n".join(entries))
            print(f" Output saved to backup file: {backup_file}")
        except Exception as e2:
            print(f" Error writing to backup file: {str(e2)}")
            print(" Please check file permissions and disk space.")

# Example usage
if __name__ == "__main__":
    input_file_path = "input.txt"  # You can change this to any input file name

    if not os.path.exists(input_file_path):
        print(f" Input file '{input_file_path}' not found!")
    else:
        print(f" Reading input file: {input_file_path}")
        try:
            with open(input_file_path, "r", encoding="utf-8") as f:
                input_text = f.read()
            
            print(f" Successfully read {len(input_text)} characters from input file")
            generate_corpus(input_text)
        except Exception as e:
            print(f" Error reading input file: {str(e)}")
            print(" Please check file permissions and encoding.")