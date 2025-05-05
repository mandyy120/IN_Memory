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
        tables['stopwords'] = (
            # English stopwords
            '', '-', 'in', 'the', 'and', 'to', 'of', 'a', 'this', 'for', 'is', 'with', 'from',
            'as', 'on', 'an', 'that', 'it', 'are', 'within', 'will', 'by', 'or', 'its', 'can',
            'your', 'be', 'about', 'used', 'our', 'their', 'you', 'into', 'using', 'these',
            'which', 'we', 'how', 'see', 'below', 'all', 'use', 'across', 'provide', 'provides',
            'aims', 'one', '&', 'ensuring', 'crucial', 'at', 'various', 'through', 'find', 'ensure',
            'more', 'another', 'but', 'should', 'considered', 'provided', 'must', 'whether',
            'located', 'where', 'begins', 'any', 'what'
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

        # Standard text cleaning for English
        text = text.replace('/', " ").replace('(', ' ').replace(')', ' ').replace('?', '')
        text = text.replace("'", "").replace('"', "").replace('\\n', '').replace('!', '')
        text = text.replace("\\s", '').replace("\\t", '').replace(",", " ").replace(":", " ")
        text = text.lower()

        sentence_separators = ('.', '!')
        for sep in sentence_separators:
            text = text.replace(sep, '_~')
        text = text.split('_~')

        hash_pairs = self.backend_tables['hash_pairs']
        ctokens = self.backend_tables['ctokens']
        KW_map = self.backend_tables['KW_map']
        stopwords = self.backend_tables['stopwords']
        hwords = {}  # local word hash with word position, to update hash_pairs

        for sentence in text:
            # Split by spaces
            words = sentence.split(" ")
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
        """Load data from local file or URL and build backend tables. English-only version."""
        if local:
            # Read file with UTF-8 encoding
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = f.read()
            except UnicodeDecodeError:
                # Fall back to chardet if UTF-8 fails
                with open(file_path, "rb") as f:
                    raw_data = f.read()
                encoding_info = chardet.detect(raw_data)
                encoding = encoding_info["encoding"] if encoding_info["encoding"] else "utf-8"
                print(f"Using detected encoding: {encoding}")
                with open(file_path, "r", encoding=encoding, errors="replace") as f:
                    data = f.read()
        else:
            # Get repository from GitHub URL
            response = requests.get(url)
            response.encoding = 'utf-8'
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


    def detect_language(self, _):
        """
        Always returns English as the language code since we're only supporting English

        Parameters:
        _ (str): Text to analyze (ignored)

        Returns:
        str: Always returns 'en' for English
        """
        return 'en'


    def translate_text(self, text, *_):
        """
        No translation needed since we only support English

        Parameters:
        text (str): Text to translate
        *_ (any): Other parameters (ignored)

        Returns:
        str: Original text unchanged
        """
        return text


    def is_non_english_text(self, _):
        """
        Always returns False since we only support English

        Parameters:
        _ (str): Text to check (ignored)

        Returns:
        bool: Always False since we only support English
        """
        return False


    def generate_description(self, user_query):
        """
        Generate a descriptive text based on a user query by analyzing the backend tables.
        English-only version.

        Parameters:
        user_query (str): The user's input query in English

        Returns:
        str: A description text based on the query with PMI insights
        """
        # Process the query
        query = user_query.lower().split()

        # Get necessary tables
        try:
            dictionary = self.backend_tables.get('dictionary', {})
            hash_context3 = self.backend_tables.get('hash_context3', {})  # Titles
            hash_context4 = self.backend_tables.get('hash_context4', {})  # Descriptions
            KW_map = self.backend_tables.get('KW_map', {})
            stopwords = self.backend_tables.get('stopwords', {})
            embeddings = self.backend_tables.get('embeddings', {})  # Added for PMI context
        except Exception as e:
            return f"Error processing your query: {e}. Please try again."

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
        description = f"Based on your query: '{user_query}'\n\n"

        # Add relevant titles
        if sorted_titles:
            description += "Related topics:\n"
            for title, _ in sorted_titles[:7]:
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
            for desc, _ in sorted_descriptions[:7]:
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
                    for item, _ in sorted_context[:5]:
                        description += f"{item}\n"
                else:
                    description += "However, no specific details were found in our knowledge base. "
                    description += "Consider refining your query for more specific results."
            else:
                description += "No specific information was found for your query. "
                description += "Please try rephrasing your question or using different terms."

        return description




    def rephrase_with_mistral(self, description):
        """
        Rephrase the generated description using Mistral AI for clearer explanation.
        English-only version.

        Parameters:
        description (str): The original description text

        Returns:
        str: A rephrased description that's clearer and more concise
        """
        # Check if the description is a "no relevant information found" message
        if "No relevant information found for query" in description:
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
            model = "mistral-small-latest"
            client = Mistral(api_key=api_key)

            # Create prompt for English
            prompt = f"""Convert the following chatbot response into a clear, explanatory paragraph format.
                Keep the information comprehensive but present it as a cohesive explanation rather than a structured response.
                Do not include additional resources or conclusion sections. Focus only on explaining the content in a natural,
                conversational way and do not include PMI score explanation. IMPORTANT: Do not add any information that is not present in the original text.
                If the original says there are no results, preserve that message without trying to guess what the user meant:

                {description}"""

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