#--- [1] Backend: Core data structures and processing functions
import chardet
import requests
import os
from collections import defaultdict

# At the top with other imports

class KnowledgeRetrieval:
    """
    In-memory knowledge retrieval system using nested hash tables for quick data lookup.
    Processes user queries against a corpus of text data and returns relevant information.
    """
    
    def __init__(self):
        """Initialize the knowledge retrieval system with empty tables."""
        self.backend_tables = self._initialize_backend_tables()
        self.backend_params = self._get_backend_params()
        
    def _initialize_backend_tables(self):
        """Initialize all backend tables as empty dictionaries."""
        table_names = (
            'dictionary',     # multitokens (key = multitoken)
            'hash_pairs',     # multitoken associations (key = pairs of multitokens)
            'ctokens',        # not adjacent pairs in hash_pairs (key = pairs of multitokens)
            'hash_context1',  # categories (key = multitoken)
            'hash_context2',  # tags (key = multitoken)
            'hash_context3',  # titles (key = multitoken)
            'hash_context4',  # descriptions (key = multitoken)
            'hash_context5',  # meta (key = multitoken)
            'hash_ID',        # text entity ID table (key = multitoken, value is list of IDs)
            'hash_agents',    # agents (key = multitoken)
            'full_content',   # full content (key = multitoken)
            'ID_to_content',  # full content attached to text entity ID (key = text entity ID)
            'ID_to_agents',   # map text entity ID to agents list (key = text entity ID)
            'ID_size',        # content size (key = text entity ID)
            'KW_map',         # for singularization, map kw to single-token dictionary entry
            'stopwords',      # stopword list
        )
        
        tables = {}
        for name in table_names:
            tables[name] = {}
            
        # Initialize stopwords
# Add Arabic stopwords
        tables['stopwords'] = (
            # Existing English stopwords
            '', '-', 'in', 'the', 'and', 'to', 'of', 'a', 'this', 'for', 'is', 'with', 'from', 
            'as', 'on', 'an', 'that', 'it', 'are', 'within', 'will', 'by', 'or', 'its', 'can', 
            'your', 'be', 'about', 'used', 'our', 'their', 'you', 'into', 'using', 'these', 
            'which', 'we', 'how', 'see', 'below', 'all', 'use', 'across', 'provide', 'provides',
            'aims', 'one', '&', 'ensuring', 'crucial', 'at', 'various', 'through', 'find', 'ensure',
            'more', 'another', 'but', 'should', 'considered', 'provided', 'must', 'whether',
            'located', 'where', 'begins', 'any', 'what',
    
            # Arabic stopwords (common prepositions, articles, and connectors)
            'و', 'في', 'من', 'على', 'إلى', 'عن', 'مع', 'هذا', 'هذه', 'تلك', 'ذلك', 'هو', 'هي',
            'أنا', 'نحن', 'أنت', 'أنتم', 'هم', 'كان', 'كانت', 'يكون', 'تكون', 'ال', 'أن', 'لا',
            'ما', 'لم', 'لن', 'إن', 'إذا', 'كما', 'بعد', 'قبل', 'عند', 'حتى', 'أو', 'ثم', 'لكن',
            'بل', 'لأن', 'كل', 'بعض', 'غير', 'مثل', 'فقط', 'بين', 'حول', 'ضد', 'عبر', 'خلال'
        )
        
        # Load keyword map if available
        tables['KW_map'] = self._load_keyword_map()
        
        return tables
    
    def _load_keyword_map(self):
        """Load keyword map from file or return empty dict if not available."""
        kw_map = {}
        try:
            with open("KW_map.txt", "r") as f:
                for line in f:
                    pair = line.strip().split('\t')
                    if len(pair) > 1:
                        kw_map[pair[0]] = pair[1]
        except FileNotFoundError:
            print("KW_map.txt not found on first run: working with empty KW_map.")
            print("KW_map.txt will be created after exiting if save = True.")
        return kw_map
    
    def _get_backend_params(self):
        """Define backend parameters for data processing."""
        return {
            'max_multitoken': 4,  # max. consecutive terms per multi-token for inclusion in dictionary
            'maxDist': 3,         # max. position delta between 2 multitokens to link them in hash_pairs
            'maxTerms': 3,        # maxTerms must be <= max_multitoken
            'extraWeights': {     # default weight is 1
                'description': 0.0,
                'category': 0.3,
                'tag_list': 0.4,
                'title': 0.2,
                'meta': 0.1
            }
        }
    
    def update_hash(self, hash_table, key, count=1):
        """Update hash table with key and count."""
        if key in hash_table:
            hash_table[key] += count
        else:
            hash_table[key] = count
        return hash_table
    
    def update_nested_hash(self, hash_table, key, value, count=1):
        """Update nested hash table with key, value and count."""
        if key in hash_table:
            local_hash = hash_table[key]
        else:
            local_hash = {}
            
        if type(value) is not tuple:
            value = (value,)
            
        for item in value:
            if item in local_hash:
                local_hash[item] += count
            else:
                local_hash[item] = count
                
        hash_table[key] = local_hash
        return hash_table
    
    def get_value(self, key, hash_table):
        """Get value from hash table with default empty string."""
        return hash_table.get(key, '')
    
    def clean_list(self, value):
        """Convert string representation of list to tuple."""
        value = value.replace("[", "").replace("]", "")
        aux = value.split("~")
        value_list = ()
        for val in aux:
            val = val.replace("'", "").replace('"', "").lstrip()
            if val != '':
                value_list = (*value_list, val)
        return value_list
    
    def get_key_value_pairs(self, entity):
        """Extract key-value pairs from entity string."""
        entity = entity[1].replace("}", ", '")
        flag = False
        entity2 = ""

        for idx in range(len(entity)):
            if entity[idx] == '[':
                flag = True
            elif entity[idx] == ']':
                flag = False
            if flag and entity[idx] == ",":
                entity2 += "~"
            else:
                entity2 += entity[idx]

        entity = entity2
        key_value_pairs = entity.split(", '")
        return key_value_pairs
    
    def update_tables(self, word, hash_crawl):
        """Update all backend tables with word and crawled hash data."""
        category = self.get_value('category', hash_crawl)
        tag_list = self.get_value('tag_list', hash_crawl)
        title = self.get_value('title', hash_crawl)
        description = self.get_value('description', hash_crawl)
        meta = self.get_value('meta', hash_crawl)
        ID = self.get_value('ID', hash_crawl)
        agents = self.get_value('agents', hash_crawl)
        full_content = self.get_value('full_content', hash_crawl)

        extra_weights = self.backend_params['extraWeights']
        word = word.lower()  # add stemming
        weight = 1.0
        
        if word in category:
            weight += extra_weights['category']
        if word in tag_list:
            weight += extra_weights['tag_list']
        if word in title:
            weight += extra_weights['title']
        if word in meta:
            weight += extra_weights['meta']

        self.update_hash(self.backend_tables['dictionary'], word, weight)
        self.update_nested_hash(self.backend_tables['hash_context1'], word, category)
        self.update_nested_hash(self.backend_tables['hash_context2'], word, tag_list)
        self.update_nested_hash(self.backend_tables['hash_context3'], word, title)
        self.update_nested_hash(self.backend_tables['hash_context4'], word, description)
        self.update_nested_hash(self.backend_tables['hash_context5'], word, meta)
        self.update_nested_hash(self.backend_tables['hash_ID'], word, ID)
        self.update_nested_hash(self.backend_tables['hash_agents'], word, agents)
        
        for agent in agents:
            self.update_nested_hash(self.backend_tables['ID_to_agents'], ID, agent)
            
        self.update_nested_hash(self.backend_tables['full_content'], word, full_content)
        self.update_nested_hash(self.backend_tables['ID_to_content'], ID, full_content)

    def update_dict(self, hash_crawl):
        """Update dictionary and related hash tables with crawled data. Enhanced for Arabic support."""
        max_multitoken = self.backend_params['max_multitoken']
        max_dist = self.backend_params['maxDist']
        max_terms = self.backend_params['maxTerms']

        category = self.get_value('category', hash_crawl)
        tag_list = self.get_value('tag_list', hash_crawl)
        title = self.get_value('title', hash_crawl)
        description = self.get_value('description', hash_crawl)
        meta = self.get_value('meta', hash_crawl)

        text = category + "." + str(tag_list) + "." + title + "." + description + "." + meta
    
        # Modified text cleaning to preserve Arabic characters
        text = text.replace('/', " ").replace('(', ' ').replace(')', ' ').replace('?', '')
        text = text.replace("'", "").replace('"', "").replace('\\n', '').replace('!', '')
        text = text.replace("\\s", '').replace("\\t", '').replace(",", " ").replace(":", " ")
        text = text.lower()  # Note: this only affects Latin characters, not Arabic
    
        sentence_separators = ('.', '؟', '!', '،', '؛')  # Added Arabic punctuation
        for sep in sentence_separators:
            text = text.replace(sep, '_~')
        text = text.split('_~')

        hash_pairs = self.backend_tables['hash_pairs']
        ctokens = self.backend_tables['ctokens']
        KW_map = self.backend_tables['KW_map']
        stopwords = self.backend_tables['stopwords']
        hwords = {}  # local word hash with word position, to update hash_pairs

        for sentence in text:
            # Split by both spaces and zero-width spaces (common in Arabic text)
            words = sentence.replace('\u200c', ' ').split(" ")
            position = 0
            buffer = []

            for word in words:
                if not word:  # Skip empty tokens
                    continue
                
                if word in KW_map:
                    word = KW_map[word]

                if word not in stopwords:
                    # word is single token
                    buffer.append(word)
                    key = (word, position)
                    self.update_hash(hwords, key)  # for word correlation table (hash_pairs)
                    self.update_tables(word, hash_crawl)

                    for k in range(1, max_multitoken):
                        if position > k:
                            # word is now multi-token with k+1 tokens
                            word = buffer[position - k] + "~" + word
                            key = (word, position)
                            self.update_hash(hwords, key)  # for word correlation table (hash_pairs)
                            self.update_tables(word, hash_crawl)

                    position += 1

        for keyA in hwords:
            for keyB in hwords:
                wordA = keyA[0]
                positionA = keyA[1]
                n_termsA = len(wordA.split("~"))

                wordB = keyB[0]
                positionB = keyB[1]
                n_termsB = len(wordB.split("~"))

                key = (wordA, wordB)
                n_termsAB = max(n_termsA, n_termsB)
                distanceAB = abs(positionA - positionB)

                if wordA < wordB and distanceAB <= max_dist and n_termsAB <= max_terms:
                    hash_pairs = self.update_hash(hash_pairs, key)
                    if distanceAB > 1:
                        ctokens = self.update_hash(ctokens, key)

    def load_data(self, local=True, file_path="/home/mandeep/Pictures/corpus/uploads/repository_generated.txt", url="https://mltblog.com/3y8MXq5", append=True):
        """Load data from local file or URL and build backend tables. Enhanced for multilingual support."""
        if local:
            # Detect file encoding before reading, with UTF-8 preference for Arabic support
            with open(file_path, "rb") as f:
                raw_data = f.read()

            encoding_info = chardet.detect(raw_data)
            # Prefer UTF-8 for proper Arabic character handling
            encoding = encoding_info["encoding"] if encoding_info["encoding"] else "utf-8"
            if encoding.lower() not in ['utf-8', 'utf8']:
                print(f"Warning: Detected encoding {encoding} might not fully support Arabic. Trying UTF-8...")
                try:
                    # Test UTF-8 decoding
                    raw_data.decode('utf-8')
                    encoding = 'utf-8'
                    print("Successfully validated UTF-8 encoding.")
                except UnicodeDecodeError:
                    print(f"UTF-8 decoding failed, continuing with detected encoding: {encoding}")
    
            print(f"Using encoding: {encoding}")
    
            # Read file with detected encoding
            with open(file_path, "r", encoding=encoding, errors="replace") as f:
                data = f.read()
        else:
            # Get repository from GitHub URL
            response = requests.get(url)
            response.encoding = 'utf-8'  # Force UTF-8 for proper Arabic support
            data = response.text

        print("Data loaded successfully!")
    
        # Build tables with the loaded data
        self.build_tables(data, append=append)
        
    def build_tables(self, data, append=True):
        """Build all backend tables from loaded data."""
        entities = data.split("\n")
        ID_size = self.backend_tables['ID_size']
    
        # If not appending, clear all tables except KW_map and stopwords
        if not append:
            # Preserve KW_map and stopwords
            kw_map = self.backend_tables['KW_map']
            stopwords = self.backend_tables['stopwords']
        
            # Reinitialize all tables
            self.backend_tables = self._initialize_backend_tables()
        
            # Restore KW_map and stopwords
            self.backend_tables['KW_map'] = kw_map
            self.backend_tables['stopwords'] = stopwords
    
        # Keep track of processed entity IDs to avoid duplicates
        processed_ids = set()
        if append:
            # If appending, collect already processed IDs
            processed_ids = set(self.backend_tables['ID_to_content'].keys())
        
        # Agent mapping for entity processing
        agent_map = {
            'template': 'Template',
            'policy': 'Policy',
            'governance': 'Governance',
            'documentation': 'Documentation',
            'best practice': 'Best Practices',
            'bestpractice': 'Best Practices',
            'standard': 'Standards',
            'naming': 'Naming',
            'glossary': 'Glossary',
            'historical data': 'Data',
            'overview': 'Overview',
            'training': 'Training',
            'genai': 'GenAI',
            'gen ai': 'GenAI',
            'example': 'Example',
            'example1': 'Example',
            'example2': 'Example',
        }

        # To avoid duplicate entities
        entity_list = ()

        for entity_raw in entities:
            entity = entity_raw.split("~~")
            agent_list = ()
            
            if len(entity) > 1 and entity[1] not in entity_list:
                entity_list = (*entity_list, entity[1])
                try:
                    entity_ID = int(entity[0])
                    if append and entity_ID in processed_ids:
                        continue
                    entity_split = entity[1].split("{")
                    hash_crawl = {}
                    hash_crawl['ID'] = entity_ID
                    ID_size[entity_ID] = len(entity[1])
                    hash_crawl['full_content'] = entity_raw

                    key_value_pairs = self.get_key_value_pairs(entity_split)

                    for pair in key_value_pairs:
                        if ": " in pair:
                            key, value = pair.split(": ", 1)
                            key = key.replace("'", "")
                            if key == 'category_text':
                                hash_crawl['category'] = value
                            elif key == 'tags_list_text':
                                hash_crawl['tag_list'] = self.clean_list(value)
                            elif key == 'title_text':
                                hash_crawl['title'] = value
                            elif key == 'description_text':
                                hash_crawl['description'] = value
                            elif key == 'tower_option_tower':
                                hash_crawl['meta'] = value
                                
                            if key in ('category_text', 'tags_list_text', 'title_text'):
                                for word in agent_map:
                                    if word in value.lower():
                                        agent = agent_map[word]
                                        if agent not in agent_list:
                                            agent_list = (*agent_list, agent)

                    hash_crawl['agents'] = agent_list
                    self.update_dict(hash_crawl)
                except Exception as e:
                    print(f"Error processing entity: {e}")
                    continue

        # Create embeddings after building all tables
        self.create_embeddings()
        self.create_sorted_ngrams()
        
    def create_embeddings(self):
        """Create embeddings for multitokens based on hash_pairs."""
        embeddings = {}
        
        hash_pairs = self.backend_tables['hash_pairs']
        dictionary = self.backend_tables['dictionary']
        
        for key in hash_pairs:
            wordA = key[0]
            wordB = key[1]
            nA = dictionary.get(wordA, 0)
            nB = dictionary.get(wordB, 0)
            if nA > 0 and nB > 0:  # Avoid division by zero
                nAB = hash_pairs[key]
                pmi = nAB / (nA * nB) ** 0.5  # PMI calculation
                self.update_nested_hash(embeddings, wordA, wordB, pmi)
                self.update_nested_hash(embeddings, wordB, wordA, pmi)
            
        self.backend_tables['embeddings'] = embeddings
        
    def create_sorted_ngrams(self):
        """Create sorted n-grams for matching with embeddings entries."""
        sorted_ngrams = {}
        dictionary = self.backend_tables['dictionary']
        
        for word in dictionary:
            tokens = word.split('~')
            tokens.sort()
            sorted_ngram = tokens[0]
            for token in tokens[1:len(tokens)]:
                sorted_ngram += "~" + token
            self.update_nested_hash(sorted_ngrams, sorted_ngram, word)
            
        self.backend_tables['sorted_ngrams'] = sorted_ngrams
        
    def calculate_pmi(self, word, token):
        """Calculate the Pointwise Mutual Information between two words."""
        dictionary = self.backend_tables['dictionary']
        hash_pairs = self.backend_tables['hash_pairs']

        nAB = 0
        pmi = 0.00
        keyAB = (word, token)
        if word > token:
            keyAB = (token, word)
            
        if keyAB in hash_pairs:
            nAB = hash_pairs[keyAB]
            nA = dictionary.get(word, 0)
            nB = dictionary.get(token, 0)
            if nA > 0 and nB > 0:  # Avoid division by zero
                pmi = nAB / (nA * nB) ** 0.5
                
        return pmi
    
    
    def detect_language(self, text):
        """
        Detect the language of the given text using external translation service
        
        Parameters:
        text (str): Text to analyze
        
        Returns:
        str: ISO language code
        """
        try:
            # Call the external translation service
            response = requests.post('http://127.0.0.1:5002/detect', json={'text': text})
            data = response.json()
            
            if data.get('success'):
                return data.get('lang')
            else:
                print(f"Translation service error: {data.get('error')}")
                # Fall back to character-based detection
        except Exception as e:
            print(f"Failed to connect to translation service: {e}")
            # Fall back to character-based detection
                
        # Fall back to the original character-based detection
        # Arabic Unicode range
        if any('\u0600' <= c <= '\u06FF' for c in text):
            return 'ar'
        # Hindi/Devanagari
        elif any('\u0900' <= c <= '\u097F' for c in text):
            return 'hi'
        # Cyrillic (Russian, etc.)
        elif any('\u0400' <= c <= '\u04FF' for c in text):
            return 'ru'
        # Chinese
        elif any('\u4E00' <= c <= '\u9FFF' for c in text):
            return 'zh'
        # Japanese
        elif any('\u3040' <= c <= '\u30FF' for c in text):
            return 'ja'
        # Korean
        elif any('\uAC00' <= c <= '\uD7A3' for c in text):
            return 'ko'
        # Thai
        elif any('\u0E00' <= c <= '\u0E7F' for c in text):
            return 'th'
        # Default to English
        else:
            return 'en'
    
    
    def translate_text(self, text, source_lang=None, target_lang='en'):
        """
        Translate text between languages using external translation service

        Parameters:
        text (str): Text to translate
        source_lang (str): Source language code (auto-detected if None)
        target_lang (str): Target language code (defaults to 'en')

        Returns:
        str: Translated text
        """
        # If source and target are the same, no translation needed
        if source_lang == target_lang:
            return text

        try:
            # Prepare request data
            data = {
                'text': text,
                'source_lang': source_lang if source_lang else 'auto',
                'target_lang': target_lang
            }

            # Call the external translation service
            response = requests.post('http://127.0.0.1:5002/translate', json=data)
            result = response.json()

            if result.get('success'):
                # Get detected language if it was auto
                if source_lang is None or source_lang == 'auto':
                    detected_lang_code = result.get('source_lang')
                    print(f"Detected source language: {detected_lang_code}")

                return result.get('translated_text')
            else:
                print(f"Translation service error: {result.get('error')}")
                return text

        except Exception as e:
            print(f"Failed to connect to translation service: {e}")
            # If translation fails, return original text
            return text
    
    
    def is_non_english_text(self, text):
        """
        Check if text contains non-English characters

        Parameters:
        text (str): Text to check

        Returns:
        bool: True if text contains non-English characters, False otherwise
        """
        # Simple check for non-Latin alphabets
        return any(not (c.isascii() and c.isprintable()) for c in text if not c.isspace())
    
    
    def generate_description(self, user_query):
        """
        Generate a descriptive text based on a user query by analyzing the backend tables.
        Enhanced with translation support for any language.

        Parameters:
        user_query (str): The user's input query in any language

        Returns:
        str: A description text based on the query with PMI insights
        """
        # Detect query language
        source_lang = self.detect_language(user_query)
        original_query = user_query

        # Translate non-English query to English for processing
        if source_lang != 'en':
            print(f"Detected {source_lang} query: {user_query}")
            user_query = self.translate_text(user_query, source_lang, 'en')
            print(f"Translated to English: {user_query}")

        # Process the query - now in English
        query = user_query.lower().split()

        # Get necessary tables
        try:
            dictionary = self.backend_tables.get('dictionary', {})
            hash_context3 = self.backend_tables.get('hash_context3', {})  # Titles
            hash_context4 = self.backend_tables.get('hash_context4', {})  # Descriptions
            hash_agents = self.backend_tables.get('hash_agents', {})
            hash_pairs = self.backend_tables.get('hash_pairs', {})  # For PMI calculations
            KW_map = self.backend_tables.get('KW_map', {})
            stopwords = self.backend_tables.get('stopwords', {})
            embeddings = self.backend_tables.get('embeddings', {})  # Added for PMI context
        except Exception as e:
            result = f"Error processing your query: {e}. Please try again."
            # Translate error message back to original language if needed
            return self.translate_text(result, 'en', source_lang) if source_lang != 'en' else result

        # Filter out stopwords and map query tokens to known keywords
        processed_query = []
        for token in query:
            if token not in stopwords:
                if token in KW_map:
                    token = KW_map[token]
                processed_query.append(token)

        # Find relevant multitokens in dictionary
        relevant_tokens = {}
        for token in processed_query:
            if token in dictionary:
                relevant_tokens[token] = dictionary[token]

        # If no relevant tokens found, return generic message
        if not relevant_tokens:
            if source_lang != 'en':
                result = f"No relevant information found for query: '{original_query}'. Please try different keywords."
                return self.translate_text(result, 'en', source_lang)
            else:
                return f"No relevant information found for query: '{user_query}'. Please try different keywords."

        # Find related titles and descriptions
        related_titles = {}
        related_descriptions = {}

        # Collect PMI data for related terms
        pmi_insights = {}

        for token in relevant_tokens:
            if token in hash_context3:
                for title in hash_context3[token]:
                    if title in related_titles:
                        related_titles[title] += relevant_tokens[token]
                    else:
                        related_titles[title] = relevant_tokens[token]

            if token in hash_context4:
                for desc in hash_context4[token]:
                    if desc in related_descriptions:
                        related_descriptions[desc] += relevant_tokens[token]
                    else:
                        related_descriptions[desc] = relevant_tokens[token]

            if token in embeddings:
                token_embeddings = embeddings[token]
                for related_term, pmi_value in token_embeddings.items():
                    if pmi_value > 0.1:
                        pmi_insights[f"{token} ↔ {related_term}"] = pmi_value

        # Sort results
        sorted_titles = sorted(related_titles.items(), key=lambda x: x[1], reverse=True)
        sorted_descriptions = sorted(related_descriptions.items(), key=lambda x: x[1], reverse=True)
        sorted_pmi_insights = sorted(pmi_insights.items(), key=lambda x: x[1], reverse=True)

        # Generate base description
        if source_lang != 'en':
            description = f"Based on your query: '{original_query}'\n\n"
        else:
            description = f"Based on your query: '{user_query}'\n\n"

        # Add relevant titles
        if sorted_titles:
            description += "Related topics:\n"
            for title, score in sorted_titles[:7]:
                description += f"- {title}\n"
            description += "\n"

        # Add PMI insights
        if sorted_pmi_insights:
            description += "Term Relationships (PMI):\n"
            for term_pair, pmi_score in sorted_pmi_insights[:5]:
                description += f"- {term_pair}: {pmi_score:.2f}\n"
            description += "\n"

        # Add descriptions
        if sorted_descriptions:
            description += "Summary:\n"
            for desc, score in sorted_descriptions[:3]:
                description += f"{desc}\n\n"

        # Fallback if no relevant descriptions found
        if not sorted_descriptions:
            all_context_tables = {
                'Category': self.backend_tables.get('hash_context1', {}),
                'Tags': self.backend_tables.get('hash_context2', {}),
                'Titles': hash_context3,
                'Meta': self.backend_tables.get('hash_context5', {})
            }

            key_terms = [token for token in processed_query if token in dictionary]

            if key_terms:
                description += f"Your query relates to {', '.join(key_terms)}. "

                context_info = {}
                for context_type, context_table in all_context_tables.items():
                    for token in key_terms:
                        if token in context_table:
                            for item in context_table[token]:
                                if item not in context_info:
                                    context_info[item] = (context_type, 1)
                                else:
                                    curr_type, curr_count = context_info[item]
                                    context_info[item] = (curr_type, curr_count + 1)

                sorted_context = sorted(context_info.items(), key=lambda x: x[1][1], reverse=True)

                if sorted_context:
                    description += "Based on our knowledge base, the following information is relevant:\n\n"
                    for item, (item_type, count) in sorted_context[:5]:
                        description += f"{item}\n"
                else:
                    description += "However, no specific details were found in our knowledge base. "
                    description += "Consider refining your query for more specific results."
            else:
                description += "No specific information was found for your query. "
                description += "Please try rephrasing your question or using different terms."

        # Translate result back if needed
        if source_lang != 'en':
            return self.translate_text(description, 'en', source_lang)
        else:
            return description
    
    
        
    
    def rephrase_with_mistral(self, description):
        """
        Rephrase the generated description using Mistral AI for clearer explanation.
        Enhanced to handle multiple languages, not just English and Arabic.

        Parameters:
        description (str): The original description text

        Returns:
        str: A rephrased description that's clearer and more concise
        """
        # Detect the language of the description
        source_lang = self.detect_language(description)

        # Check if the description is a "no relevant information found" message
        # Define common patterns in various languages
        no_results_patterns = {
            'en': "No relevant information found for query",
            'ar': "لم يتم العثور على معلومات",
            'fr': "Aucune information pertinente trouvée",
            'es': "No se encontró información relevante",
            'de': "Keine relevanten Informationen gefunden",
            # Add more languages as needed
        }

        # Check if the description contains any of the "no results" patterns
        for lang, pattern in no_results_patterns.items():
            if pattern in description:
                # Return the original message without rephrasing
                return description

        try:
            from mistralai import Mistral

            # Get API key from environment variable
            api_key = os.environ.get("MISTRAL_API_KEY")

            if not api_key:
                print("Warning: MISTRAL_API_KEY environment variable not set. Using original description.")
                return description

            # Initialize Mistral client
            model = "mistral-large-latest"
            client = Mistral(api_key=api_key)

            # Create language-specific prompts
            prompts = {
                'en': f"""Convert the following chatbot response into a clear, explanatory paragraph format. 
                    Keep the information comprehensive but present it as a cohesive explanation rather than a structured response.
                    Do not include additional resources or conclusion sections. Focus only on explaining the content in a natural, 
                    conversational way and do not include PMI score explanation. IMPORTANT: Do not add any information that is not present in the original text. 
                    If the original says there are no results, preserve that message without trying to guess what the user meant:

                    {description}""",

                'ar': f"""حوّل رد برنامج المحادثة التالي إلى فقرة توضيحية واضحة. 
                    احتفظ بالمعلومات شاملة ولكن قدمها كشرح متماسك بدلاً من رد منظم.
                    لا تضمن موارد إضافية أو أقسام ختامية. ركز فقط على شرح المحتوى بطريقة طبيعية ومحادثة  
                    ولا تضمن شرح درجة PMI. مهم: لا تضيف أي معلومات غير موجودة في النص الأصلي.
                    إذا كان النص الأصلي يقول أنه لا توجد نتائج، حافظ على هذه الرسالة دون محاولة تخمين ما قصده المستخدم:

                    {description}""",

                'fr': f"""Convertissez la réponse suivante du chatbot en un format de paragraphe clair et explicatif.
                    Gardez l'information complète mais présentez-la comme une explication cohérente plutôt qu'une réponse structurée.
                    N'incluez pas de ressources supplémentaires ou de sections de conclusion. Concentrez-vous uniquement sur l'explication du contenu
                    de manière naturelle et conversationnelle et n'incluez pas l'explication du score PMI. IMPORTANT: N'ajoutez aucune information
                    qui n'est pas présente dans le texte original. Si l'original indique qu'il n'y a pas de résultats, conservez ce message sans
                    essayer de deviner ce que l'utilisateur voulait dire:

                    {description}""",

                'es': f"""Convierte la siguiente respuesta del chatbot en un formato de párrafo claro y explicativo.
                    Mantén la información completa pero preséntala como una explicación coherente en lugar de una respuesta estructurada.
                    No incluyas recursos adicionales ni secciones de conclusión. Concéntrate solo en explicar el contenido de manera
                    natural y conversacional y no incluyas explicación de puntuación PMI. IMPORTANTE: No agregues ninguna información
                    que no esté presente en el texto original. Si el original dice que no hay resultados, conserva ese mensaje sin
                    tratar de adivinar lo que el usuario quiso decir:

                    {description}""",

                'de': f"""Wandle die folgende Chatbot-Antwort in ein klares, erklärendes Absatzformat um.
                    Behalte die Informationen umfassend, präsentiere sie aber als zusammenhängende Erklärung statt einer strukturierten Antwort.
                    Füge keine zusätzlichen Ressourcen oder Abschlussbereiche hinzu. Konzentriere dich nur darauf, den Inhalt auf natürliche,
                    konversationelle Weise zu erklären und erkläre nicht den PMI-Wert. WICHTIG: Füge keine Informationen hinzu, die nicht im Originaltext
                    vorhanden sind. Wenn das Original besagt, dass keine Ergebnisse vorliegen, behalte diese Nachricht bei, ohne zu versuchen zu erraten,
                    was der Benutzer meinte:

                    {description}""",
            }

            # Select prompt based on detected language, fall back to English if not available
            prompt = prompts.get(source_lang, prompts['en'])

            # If the language isn't one of the predefined ones, translate to English first
            working_description = description
            need_translation_back = False
            if source_lang not in prompts:
                print(f"Translating from {source_lang} to English for processing...")
                working_description = self.translate_text(description, source_lang, 'en')
                prompt = prompts['en']
                need_translation_back = True

            # Get response from Mistral
            chat_response = client.chat.complete(
                model=model,
                messages=[
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ]
            )

            # Extract the rephrased content
            rephrased_description = chat_response.choices[0].message.content

            # Translate back to original language if needed
            if need_translation_back:
                print(f"Translating back to {source_lang} from English...")
                rephrased_description = self.translate_text(rephrased_description, 'en', source_lang)

            return rephrased_description

        except ImportError:
            print("Warning: mistralai package not installed. Using original description.")
            return description
        except Exception as e:
            print(f"Error using Mistral AI: {e}")
            return description

    def create_keyword_map(self):
        """Create keyword map for single token mapping and save to file."""
        dictionary = self.backend_tables['dictionary']
        
        with open("KW_map.txt", "w") as f:
            for key in dictionary:
                if key.count('~') == 0:
                    j = len(key)
                    if j > 1:  # Make sure the key has at least 2 characters
                        keyB = key[0:j-1]
                        if keyB in dictionary and key[j-1] == 's':
                            if dictionary[key] > dictionary[keyB]:
                                f.write(keyB + "\t" + key + "\n")
                            else:
                                f.write(key + "\t" + keyB + "\n")
                                
    def save_backend_tables(self):
        """Save all backend tables to files for future use, preserving existing data."""
        self.create_keyword_map()
    
        # Before saving tables, check if we need to merge with existing data
        for table_name, table in self.backend_tables.items():
            # Skip saving stopwords and KW_map for now (handled separately)
            if table_name in ['stopwords', 'KW_map']:
                continue
            
            file_path = f'backend_{table_name}.txt'
            try:
                # Skip empty tables
                if not table:
                    continue
                
                # For ID_to_content and hash_ID which contain mapping to entity data
                # These are crucial for preserving entity information
                if table_name in ['ID_to_content', 'hash_ID', 'ID_to_agents', 'ID_size']:
                    print(f"Saving {table_name} data...")
                
                # Save the table
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(str(table))
                
            except Exception as e:
                print(f"Error saving {table_name}: {e}")
            
    # Save KW_map (this is handled by create_keyword_map already)
    
    # Save embeddings separately if not already in backend_tables
        if 'embeddings' not in self.backend_tables:
            with open('backend_embeddings.txt', "w", encoding="utf-8") as f:
                f.write(str({}))
            
    # Save sorted_ngrams separately if not already in backend_tables
        if 'sorted_ngrams' not in self.backend_tables:
            with open('backend_sorted_ngrams.txt', "w", encoding="utf-8") as f:
                f.write(str({}))
            
    print("Backend tables saved successfully!")
                
    def ask_user_query(self):
        """
        Ask the user for a query, process it, and generate a description with PMI components.
        The description is then rephrased using Mistral AI for clearer explanation.
        """
        print("\n--------------------------------------------------------------------")
        print("Welcome to the Knowledge Retrieval System")
        print("Enter your query to get information from our knowledge base.")
        print("Type 'exit' or leave empty to quit.")
        print("--------------------------------------------------------------------\n")
        
        # Create embeddings table if not present
        if 'embeddings' not in self.backend_tables:
            self.create_embeddings()
        
        while True:
            user_query = input("Enter your query: ").strip()
            
            if not user_query or user_query.lower() == 'exit':
                print("\nThank you for using our system. Goodbye!")
                break
            
            try:
                # Process the query and generate description with PMI
                original_description = self.generate_description(user_query)
                
                # Rephrase the description using Mistral AI
                rephrased_description = self.rephrase_with_mistral(original_description)
                
                # Print the description
                print("\n====================================================================")
                print("QUERY RESULTS ")
                print("====================================================================\n")
                print(rephrased_description)
                print("\n====================================================================\n")
                
                # Option to see original description
                show_original = input("Would you like to see the original description? (y/n): ").strip().lower()
                if show_original == 'y':
                    print("\n====================================================================")
                    print("ORIGINAL QUERY RESULTS")
                    print("====================================================================\n")
                    print(original_description)
                    print("\n====================================================================\n")
                    print("\n====================================================================\n")
            except Exception as e:
                print(f"Error processing query: {e}")
                
                
                
                
if __name__ == "__main__":
    # Create instance of KnowledgeRetrieval system
    knowledge_system = KnowledgeRetrieval()
    
    # Default file path for local data
    file_path = "/home/mandeep/Pictures/corpus/uploads/repository_generated.txt"
    
    # Load data automatically without asking user
    print(f"Loading data from: {file_path}")
    try:
        knowledge_system.load_data(local=True, file_path=file_path)
        print("Data loaded successfully!")
    except Exception as e:
        print(f"Error loading data: {e}")
        print("Using existing backend tables if available.")
    
    # First save backend tables
    print("\nSaving backend tables...")
    knowledge_system.save_backend_tables()
    print("Backend tables saved successfully!")
    
    # Then start interactive query session
    print("\nStarting interactive query session...")
    knowledge_system.ask_user_query()