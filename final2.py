#--- [1] Backend: Core data structures and processing functions
import chardet
import requests
import os
import re
import json
import time
import hashlib
import pickle
from collections import defaultdict
from pymongo import MongoClient
from pymongo import UpdateOne
from pymongo.errors import BulkWriteError, ConnectionFailure
from tqdm import tqdm

# Import file locking utility
try:
    from file_lock import FileLock
except ImportError:
    # Define a simple FileLock class if the file_lock module is not available
    class FileLock:
        def __init__(self, file_path, timeout=10, delay=0.1):
            self.file_path = file_path

        def __enter__(self):
            return self

        def __exit__(self, type, value, traceback):
            pass

# Define required collections that must exist for the system to work properly
REQUIRED_COLLECTIONS = [
    'dictionary',
    'hash_pairs',
    'ctokens',
    'hash_context1',
    'hash_context2',
    'hash_context3',
    'hash_context4',
    'hash_context5',
    'hash_ID',
    'hash_agents',
    'full_content',
    'ID_to_content',
    'ID_to_agents',
    'ID_size',
    'KW_map',
    'stopwords',
    'embeddings',
    'sorted_ngrams',
    'metadata'  # For storing file hashes and other metadata
]

class KnowledgeRetrieval:
    """
    In-memory knowledge retrieval system using nested hash tables for quick data lookup.
    Processes user queries against a corpus of text data and returns relevant information.
    """

    def __init__(self, use_mongodb=True, mongo_connection_string="mongodb://localhost:27017", mongo_db_name="KnowledgeBase"):
        """
        Initialize the knowledge retrieval system with empty tables.

        Args:
            use_mongodb (bool): Whether to use MongoDB for storage (default: True)
            mongo_connection_string (str): MongoDB connection string
            mongo_db_name (str): MongoDB database name
        """
        # MongoDB configuration
        self.use_mongodb = use_mongodb  # Use the provided value
        self.mongo_connection_string = mongo_connection_string
        self.mongo_db_name = mongo_db_name
        self.mongo_client = None
        self.mongo_db = None

        # Connect to MongoDB
        try:
            if not self.use_mongodb:
                print("MongoDB is disabled in configuration. Using file-based storage.")
                self.mongo_client = None
                self.mongo_db = None
                return

            self.mongo_client = MongoClient(self.mongo_connection_string, serverSelectionTimeoutMS=5000)
            # Verify connection
            self.mongo_client.admin.command('ping')
            self.mongo_db = self.mongo_client[self.mongo_db_name]
            print(f"Connected to MongoDB database: {self.mongo_db_name}")

            # Check if all required collections exist
            existing_collections = self.mongo_db.list_collection_names()
            missing_collections = [col for col in REQUIRED_COLLECTIONS if col not in existing_collections]

            if missing_collections:
                print(f"Missing collections: {missing_collections}")
                print("Creating missing collections...")
                for collection in missing_collections:
                    # Create collection by inserting and then removing a dummy document
                    self.mongo_db[collection].insert_one({"_id": "dummy", "value": None})
                    self.mongo_db[collection].delete_one({"_id": "dummy"})
                    print(f"Created empty collection: {collection}")
                print("Missing collections created.")

            # Check multiple possible repository file paths
            repo_paths = [
                "/home/dtp2025-001/Pictures/corpus/uploads/uploads/repository_generated.txt",
                "uploads/repository_generated.txt",
                "repository_generated.txt",
                "repository.txt"
            ]

            # Try to load repository file path from config.json if it exists
            config_path = os.path.join(os.path.dirname(__file__), 'config.json')
            if os.path.exists(config_path):
                try:
                    with open(config_path, 'r') as f:
                        config = json.load(f)
                        if "repository_file" in config:
                            repo_paths.insert(0, config["repository_file"])
                except Exception as e:
                    print(f"Error loading repository path from config: {e}")

            repo_file = None
            for path in repo_paths:
                if os.path.exists(path):
                    repo_file = path
                    print(f"Found repository file: {repo_file}")
                    break

            if repo_file:
                # Calculate file hash
                with open(repo_file, 'rb') as f:
                    file_content = f.read()
                    file_hash = hashlib.md5(file_content).hexdigest()

                # Check if we have a record of this file hash
                metadata = self.mongo_db.metadata.find_one({"_id": "repository_file"})
                last_hash = metadata.get('hash') if metadata else None

                # If no previous hash or hash is different, we have new data
                has_new_data = last_hash is None or last_hash != file_hash

                # Check if we have all required collections with data
                collection_counts = {}
                for collection in ['dictionary', 'hash_pairs', 'KW_map']:
                    collection_counts[collection] = self.mongo_db[collection].count_documents({})

                all_have_data = all(count > 0 for count in collection_counts.values())

                if has_new_data:
                    print(f"New data detected in repository file: {repo_file}")
                    # We'll load this data later in the load_data method
                else:
                    print(f"Repository file exists but no new data detected: {repo_file}")

                    if all_have_data:
                        print("All required collections exist with data. No need to reload from file.")
                    else:
                        print("Some collections are empty. Will load from file...")
            else:
                print("Repository file not found in any of the expected locations.")

        except Exception as e:
            print(f"WARNING: Failed to connect to MongoDB: {e}")
            print("Falling back to file-based storage.")
            self.use_mongodb = False
            self.mongo_client = None
            self.mongo_db = None

        # Initialize backend tables and parameters
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
        """
        Load keyword map from MongoDB or file.
        Returns empty dict if not available.
        """
        kw_map = {}

        # Try to load from MongoDB if enabled
        if self.use_mongodb and self.mongo_db is not None:
            try:
                kw_collection = self.mongo_db['KW_map']
                cursor = kw_collection.find()
                for doc in cursor:
                    kw_map[doc["_id"]] = doc["value"]
                print(f"Successfully loaded {len(kw_map)} entries from MongoDB KW_map")
                return kw_map
            except Exception as e:
                print(f"Error loading KW_map from MongoDB: {e}")
                print("Falling back to file-based KW_map")

        # Fall back to file-based loading
        try:
            with open("KW_map.txt", "r") as f:
                for line in f:
                    pair = line.strip().split('\t')
                    if len(pair) > 1:
                        kw_map[pair[0]] = pair[1]
            print(f"Successfully loaded {len(kw_map)} entries from KW_map.txt")
        except FileNotFoundError:
            print("KW_map.txt not found on first run: working with empty KW_map.")
            print("KW_map.txt will be created after exiting if save = True.")
        except Exception as e:
            print(f"Error loading KW_map.txt: {e}")

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
        """Update dictionary and related hash tables with crawled data."""
        max_multitoken = self.backend_params['max_multitoken']
        max_dist = self.backend_params['maxDist']
        max_terms = self.backend_params['maxTerms']

        category = self.get_value('category', hash_crawl)
        tag_list = self.get_value('tag_list', hash_crawl)
        title = self.get_value('title', hash_crawl)
        description = self.get_value('description', hash_crawl)
        meta = self.get_value('meta', hash_crawl)

        # Debug: Print KW_map size
        kw_map_size = len(self.backend_tables['KW_map'])
        if kw_map_size == 0:
            print("Warning: KW_map is empty during update_dict processing")
        elif kw_map_size < 10:
            print(f"KW_map has only {kw_map_size} entries during update_dict processing")

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

                    # Dynamically update KW_map for singular/plural forms
                    if len(word) > 2 and word.endswith('s'):
                        singular = word[:-1]
                        # Check if both forms exist in dictionary
                        if singular in self.backend_tables['dictionary']:
                            # Add to KW_map based on frequency
                            if self.backend_tables['dictionary'].get(word, 0) > self.backend_tables['dictionary'].get(singular, 0):
                                self.backend_tables['KW_map'][singular] = word
                            else:
                                self.backend_tables['KW_map'][word] = singular

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

    def load_data(self, local=True, file_path=None, url="https://mltblog.com/3y8MXq5", append=True, save_to_db=True, process_source="main"):
        """
        Load data from local file or URL and build backend tables. English-only version.

        Args:
            local (bool): Whether to load from local file (True) or URL (False)
            file_path (str): Path to local file (if None, will search in common locations)
            url (str): URL to load data from if local=False
            append (bool): Whether to append to existing data or replace it
            save_to_db (bool): Whether to save to MongoDB after loading (default: True)
            process_source (str): Source of the process calling this method ('main' or 'worker')
        """
        # Create a lock file path based on the repository file
        lock_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'repository_lock')

        # Use a file lock to prevent multiple processes from loading data simultaneously
        with FileLock(lock_file_path):
            print(f"[{process_source}] Acquired lock for data loading")

            # First, ensure KW_map is loaded if it exists
            if not self.backend_tables['KW_map']:
                self.backend_tables['KW_map'] = self._load_keyword_map()

            # Check if we have all required collections with data
            all_have_data = False
            if self.use_mongodb and self.mongo_db is not None:
                collection_counts = {}
                for collection in ['dictionary', 'hash_pairs', 'KW_map']:
                    collection_counts[collection] = self.mongo_db[collection].count_documents({})

                all_have_data = all(count > 0 for count in collection_counts.values())

                # If all collections have data, we might not need to load from file
                if all_have_data:
                    print(f"[{process_source}] All required collections already have data in MongoDB.")

            # Check multiple possible repository file paths if file_path is not specified
            if local and file_path is None:
                repo_paths = [
                    "/home/dtp2025-001/Pictures/corpus/uploads/uploads/repository_generated.txt",
                    "uploads/repository_generated.txt",
                    "repository_generated.txt",
                    "repository.txt"
                ]

                # Try to load repository file path from config.json if it exists
                config_path = os.path.join(os.path.dirname(__file__), 'config.json')
                if os.path.exists(config_path):
                    try:
                        with open(config_path, 'r') as f:
                            config = json.load(f)
                            if "repository_file" in config:
                                repo_paths.insert(0, config["repository_file"])
                    except Exception as e:
                        print(f"Error loading repository path from config: {e}")

                for path in repo_paths:
                    if os.path.exists(path):
                        file_path = path
                        print(f"Found repository file: {file_path}")
                        break

                if file_path is None:
                    print("Repository file not found in any of the expected locations.")
                    if all_have_data:
                        print("Using existing data from MongoDB.")
                        return
                    else:
                        print("No repository file found and MongoDB collections are empty.")
                        return

            # Check if we need to load data
            file_hash = None
            has_new_data = False  # Default to False if we have data in MongoDB

            if local and os.path.exists(file_path):
                # Calculate file hash
                with open(file_path, 'rb') as f:
                    file_content = f.read()
                    file_hash = hashlib.md5(file_content).hexdigest()

                # Get the highest entity ID from the repository file
                highest_entity_id = 0
                with open(file_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        if line.strip():
                            try:
                                # Extract the entity ID from the beginning of the line
                                parts = line.split('~~', 1)
                                if len(parts) >= 1 and parts[0].isdigit():
                                    entity_id = int(parts[0])
                                    if entity_id > highest_entity_id:
                                        highest_entity_id = entity_id
                            except Exception as e:
                                pass

                # Count lines in the file for an additional check
                with open(file_path, 'r', encoding='utf-8') as f:
                    line_count = sum(1 for line in f if line.strip())

                # Default to loading data if MongoDB is not available
                has_new_data = True
                last_highest_entity_id = 0

                # If MongoDB is available, check if we have a record of this file hash
                if self.use_mongodb and self.mongo_db is not None:
                    metadata = self.mongo_db.metadata.find_one({"_id": "repository_file"})
                    last_hash = metadata.get('hash') if metadata else None

                    # Get the last line count and highest entity ID from metadata
                    last_line_count = metadata.get('line_count', metadata.get('entity_count')) if metadata else None
                    last_highest_entity_id = metadata.get('highest_entity_id') if metadata else None

                    # If no previous hash or hash is different AND line count has changed, we have new data
                    hash_changed = last_hash is None or last_hash != file_hash
                    count_changed = last_line_count is None or last_line_count != line_count
                    id_changed = last_highest_entity_id is None or last_highest_entity_id < highest_entity_id

                    # Consider it new data if the highest entity ID has increased
                    # This is the most reliable way to detect new data
                    has_new_data = id_changed

                    if id_changed:
                        print(f"New data detected: Highest entity ID increased from {last_highest_entity_id} to {highest_entity_id}")

                    # If hash changed but IDs didn't, it's likely just formatting changes
                    if hash_changed and not id_changed:
                        print(f"Repository file hash has changed but highest entity ID ({highest_entity_id}) is the same.")
                        print("This is likely due to formatting changes, not new data.")

                    if hash_changed and not count_changed:
                        print(f"Repository file hash has changed but line count ({line_count}) is the same.")
                        print("This is likely due to formatting changes, not new data.")
                else:
                    print(f"MongoDB not available. Loading data from file: {file_path}")
                    print(f"Found {line_count} lines with highest entity ID: {highest_entity_id}")
                    # No MongoDB available, so we can't update the hash

                    # No new data to process
                    has_new_data = False

                if not has_new_data and all_have_data:
                    print(f"Repository file {file_path} has not changed since last load.")
                    print("All required collections exist with data. No need to reload from file.")
                    return
                elif not has_new_data and not all_have_data:
                    print(f"Repository file {file_path} has not changed, but some collections are empty.")
                    print("Loading from file to populate empty collections...")
                    has_new_data = True
                elif has_new_data:
                    print(f"New data detected in repository file: {file_path}")
                    if count_changed:
                        print(f"Line count changed from {last_line_count} to {line_count}")
                    print("Loading new data...")

            # Load data from file or URL if needed
            if not local or has_new_data:
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

                # After building tables, ensure KW_map is updated and saved
                print("Finalizing KW_map after data loading...")
                self.create_keyword_map(update_memory=True, save_to_file=False)

                # Save to MongoDB if save_to_db is True
                if save_to_db:
                    print("Saving data to MongoDB...")
                    # Only force save if this is the first time loading data or we have new data
                    force_save = len(self.backend_tables.get('dictionary', {})) == 0 or has_new_data
                    self.save_backend_tables(force=force_save)

                    # Update the processed file hash, line count, and highest entity ID in the database
                    if file_hash:
                        # Count lines in the file
                        with open(file_path, 'r', encoding='utf-8') as f:
                            line_count = sum(1 for line in f if line.strip())

                        # Get the highest entity ID from the repository file
                        highest_entity_id = 0
                        with open(file_path, 'r', encoding='utf-8') as f:
                            for line in f:
                                if line.strip():
                                    try:
                                        # Extract the entity ID from the beginning of the line
                                        parts = line.split('~~', 1)
                                        if len(parts) >= 1 and parts[0].isdigit():
                                            entity_id = int(parts[0])
                                            if entity_id > highest_entity_id:
                                                highest_entity_id = entity_id
                                    except Exception as e:
                                        pass

                        self.mongo_db.metadata.update_one(
                            {"_id": "repository_file"},
                            {"$set": {
                                "hash": file_hash,
                                "line_count": line_count,
                                "entity_count": line_count,  # Keep for backward compatibility
                                "highest_entity_id": highest_entity_id,
                                "timestamp": time.time()
                            }},
                            upsert=True
                        )
                        print(f"Updated repository file hash in database: {file_hash}")
                        print(f"Updated line count in database: {line_count}")
                        print(f"Updated highest entity ID in database: {highest_entity_id}")
            else:
                print("No new data to load. Using existing data from MongoDB.")

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

        # Try to load KW_map from file if it's empty
        if not self.backend_tables['KW_map']:
            print("KW_map is empty, attempting to load from file...")
            self.backend_tables['KW_map'] = self._load_keyword_map()

        # Keep track of processed entity IDs to avoid duplicates
        processed_ids = set()
        highest_processed_id = 0
        if append:
            # If appending, collect already processed IDs
            processed_ids = set(self.backend_tables['ID_to_content'].keys())

            # Find the highest processed ID
            if processed_ids:
                highest_processed_id = max(processed_ids)
                print(f"Highest processed entity ID: {highest_processed_id}")
                print(f"Will only process entities with ID > {highest_processed_id}")

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

        # Count new entities processed
        new_entities_count = 0

        for entity_raw in entities:
            entity = entity_raw.split("~~")
            agent_list = ()

            if len(entity) > 1 and entity[1] not in entity_list:
                entity_list = (*entity_list, entity[1])
                try:
                    entity_ID = int(entity[0])

                    # Skip if already processed or ID is not greater than highest processed ID
                    if append and (entity_ID in processed_ids or entity_ID <= highest_processed_id):
                        continue

                    # Count new entities being processed
                    new_entities_count += 1

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

        # Create embeddings and other derived tables after building all tables
        self.create_embeddings()
        self.create_sorted_ngrams()

        # Update the KW_map based on the dictionary
        print("Updating KW_map based on dictionary...")
        self.create_keyword_map(update_memory=True, save_to_file=False)

        # Print summary of processed entities
        print(f"Processed {new_entities_count} new entities from the repository file.")
        if new_entities_count == 0:
            print("No new entities were found in the repository file.")

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


    def _get_mongo_value(self, collection_name, key):
        """
        Get a value from MongoDB.

        Args:
            collection_name (str): Name of the collection
            key: Key to retrieve

        Returns:
            The value if found, empty dict or list otherwise
        """
        if self.mongo_db is None:
            return {}

        try:
            doc = self.mongo_db[collection_name].find_one({"_id": str(key)})
            return doc["value"] if doc else {}
        except Exception as e:
            print(f"Error getting value from MongoDB {collection_name}: {e}")
            return {}

    def _get_mongo_values(self, collection_name, keys):
        """
        Get multiple values from MongoDB.

        Args:
            collection_name (str): Name of the collection
            keys (list): List of keys to retrieve

        Returns:
            dict: Dictionary of key-value pairs
        """
        if self.mongo_db is None:
            return {}

        result = {}
        try:
            # Convert all keys to strings for MongoDB _id
            str_keys = [str(k) for k in keys]
            cursor = self.mongo_db[collection_name].find({"_id": {"$in": str_keys}})

            for doc in cursor:
                # Find the original key
                original_key = None
                for k in keys:
                    if str(k) == doc["_id"]:
                        original_key = k
                        break

                if original_key is not None:
                    result[original_key] = doc["value"]

            return result
        except Exception as e:
            print(f"Error getting values from MongoDB {collection_name}: {e}")
            return {}

    def generate_description(self, user_query, include_topics_and_pmi=True):
        """
        Generate a descriptive text based on a user query by analyzing the backend tables.
        English-only version. Supports both MongoDB and local storage.

        Parameters:
        user_query (str): The user's input query in English
        include_topics_and_pmi (bool): Whether to include related topics and PMI information

        Returns:
        str: A description text based on the query, optionally with PMI insights
        """
        # Process the query
        query = user_query.lower().split()

        # Get necessary data
        try:
            # Get stopwords and KW_map
            stopwords = self.backend_tables.get('stopwords', {})
            KW_map = self.backend_tables.get('KW_map', {})

            # Filter out stopwords and map query tokens to known keywords
            processed_query = []
            for token in query:
                if token not in stopwords:
                    if token in KW_map:
                        token = KW_map[token]
                    processed_query.append(token)

            # If using MongoDB, get data from there
            if self.use_mongodb and self.mongo_db is not None:
                # Get dictionary entries for processed query tokens
                dictionary_entries = self._get_mongo_values('dictionary', processed_query)

                # Find relevant multitokens in dictionary
                relevant_tokens = {}
                for token in processed_query:
                    if token in dictionary_entries:
                        relevant_tokens[token] = dictionary_entries[token]

                # If no relevant tokens found, return generic message
                if not relevant_tokens:
                    return f"No relevant information found for query: '{user_query}'. Please try different keywords."

                # Find related titles and descriptions
                related_titles = {}
                related_descriptions = {}
                pmi_insights = {}

                for token in relevant_tokens:
                    # Get context data from MongoDB
                    titles_context = self._get_mongo_value('hash_context3', token)
                    desc_context = self._get_mongo_value('hash_context4', token)

                    # Process titles
                    if titles_context:
                        for title, count in titles_context.items():
                            if title in related_titles:
                                related_titles[title] += relevant_tokens[token]
                            else:
                                related_titles[title] = relevant_tokens[token]

                    # Process descriptions
                    if desc_context:
                        for desc, count in desc_context.items():
                            if desc in related_descriptions:
                                related_descriptions[desc] += relevant_tokens[token]
                            else:
                                related_descriptions[desc] = relevant_tokens[token]

                    # Get PMI data if requested
                    if include_topics_and_pmi:
                        token_embeddings = self._get_mongo_value('embeddings', token)
                        if token_embeddings:
                            for related_term, pmi_value in token_embeddings.items():
                                if pmi_value > 0.1:
                                    pmi_insights[f"{token} ↔ {related_term}"] = pmi_value
            else:
                # Use local storage
                dictionary = self.backend_tables.get('dictionary', {})
                hash_context3 = self.backend_tables.get('hash_context3', {})  # Titles
                hash_context4 = self.backend_tables.get('hash_context4', {})  # Descriptions
                embeddings = self.backend_tables.get('embeddings', {})  # Added for PMI context

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

                    if include_topics_and_pmi and token in embeddings:
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

            # Add relevant titles and PMI insights only if requested
            if include_topics_and_pmi:
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
                for desc, _ in sorted_descriptions[:3]:
                    description += f"{desc}\n\n"

            # Fallback if no relevant descriptions found
            if not sorted_descriptions:
                # Get fallback context data
                if self.use_mongodb and self.mongo_db is not None:
                    # For MongoDB, we need to fetch context data for each token
                    context_info = {}
                    for token in processed_query:
                        if token in dictionary_entries:
                            # Get context data from different collections
                            for context_type, collection in [
                                ('Category', 'hash_context1'),
                                ('Tags', 'hash_context2'),
                                ('Titles', 'hash_context3'),
                                ('Meta', 'hash_context5')
                            ]:
                                context_data = self._get_mongo_value(collection, token)
                                if context_data:
                                    for item, count in context_data.items():
                                        if item not in context_info:
                                            context_info[item] = (context_type, 1)
                                        else:
                                            curr_type, curr_count = context_info[item]
                                            context_info[item] = (curr_type, curr_count + 1)
                else:
                    # For local storage, use the existing tables
                    all_context_tables = {
                        'Category': self.backend_tables.get('hash_context1', {}),
                        'Tags': self.backend_tables.get('hash_context2', {}),
                        'Titles': hash_context3,
                        'Meta': self.backend_tables.get('hash_context5', {})
                    }

                    key_terms = [token for token in processed_query if token in dictionary]

                    context_info = {}
                    if key_terms:
                        for context_type, context_table in all_context_tables.items():
                            for token in key_terms:
                                if token in context_table:
                                    for item in context_table[token]:
                                        if item not in context_info:
                                            context_info[item] = (context_type, 1)
                                        else:
                                            curr_type, curr_count = context_info[item]
                                            context_info[item] = (curr_type, curr_count + 1)

                # Process fallback information
                if context_info:
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

        except Exception as e:
            return f"Error processing your query: {e}. Please try again."




    # Cache for rephrased descriptions to avoid repeated API calls (currently disabled)
    # _rephrase_cache = {}

    def _local_rephrase(self, description):
        """
        Simple local rephrasing without API calls.
        This is a fallback method when API calls are not available or too slow.
        Formats the text as a chatbot response paragraph without headings.

        Parameters:
        description (str): The original description text

        Returns:
        str: A slightly improved description formatted as a chatbot response
        """
        # Simple improvements without changing content
        result = description

        # Extract the main content, removing query reference
        if "Based on your query:" in result:
            result = re.sub(r'Based on your query: .*?\n\n', '', result)

        # Remove section headings
        result = re.sub(r'Summary:\s*', '', result)
        result = re.sub(r'Overview:\s*', '', result)
        result = re.sub(r'Related Terms:\s*', '', result)
        result = re.sub(r'Term Relationships \(PMI\):\s*', '', result)
        result = re.sub(r'Related topics:\s*', '', result)

        # Remove bullet points and list formatting
        result = re.sub(r'\n- ', ' ', result)
        result = re.sub(r'\n• ', ' ', result)

        # Remove redundant newlines and convert to paragraph
        result = re.sub(r'\n+', ' ', result)

        # Clean up extra spaces
        result = re.sub(r'\s+', ' ', result)
        result = result.strip()

        return result

    def rephrase_with_mistral(self, description, use_api=True, use_cache=True):  # use_cache parameter kept for compatibility
        """
        Rephrase the generated description for clearer explanation.
        Note: Caching functionality is currently disabled.

        Parameters:
        description (str): The original description text
        use_api (bool): Whether to use the Mistral API (True) or local rephrasing (False)
        use_cache (bool): Not used - caching is disabled (parameter kept for compatibility)

        Returns:
        str: A rephrased description that's clearer and more concise
        """
        # Check if the description is a "no relevant information found" message
        if "No relevant information found for query" in description:
            # Return the original message without rephrasing
            return description

        # If API use is disabled, use local rephrasing
        if not use_api:
            print("Using local rephrasing (no API call)")
            result = self._local_rephrase(description)
            return result

        # Try using the Mistral API
        try:
            import time
            start_time = time.time()

            # Check if the mistralai package is installed
            try:
                from mistralai.client import MistralClient
                from mistralai.models.chat_completion import ChatMessage
            except ImportError:
                try:
                    # Try the newer package structure
                    from mistralai import Mistral
                except ImportError:
                    print("Mistral AI package not installed. Install with: pip install mistralai")
                    print("Using local rephrasing instead.")
                    return self._local_rephrase(description)

            # Get API key from environment variable
            api_key = os.environ.get("MISTRAL_API_KEY")
            if not api_key:
                print("MISTRAL_API_KEY environment variable not set.")
                print("To use API rephrasing, set the MISTRAL_API_KEY environment variable:")
                print("export MISTRAL_API_KEY=your_api_key_here")
                print("Using local rephrasing instead.")
                return self._local_rephrase(description)

            print("Using Mistral API for rephrasing...")

            # Try the newer API first
            try:
                # Initialize Mistral client (newer version)
                client = Mistral(api_key=api_key)

                # Create a prompt for rephrasing
                prompt = f"""Rewrite this text as a natural, conversational chatbot response in paragraph form.
                Do NOT include any headings or section titles like 'Summary:' or 'Overview:'.
                Present all information as a flowing, cohesive paragraph without bullet points or numbered lists.
                Use a friendly, helpful tone as if directly answering a user's question.
                Do not add any information that is not present in the original text:

                {description}"""

                # Get response from Mistral
                chat_response = client.chat.complete(
                    model="mistral-small-latest",
                    messages=[
                        {
                            "role": "user",
                            "content": prompt,
                        }
                    ]
                )

                # Extract the rephrased content
                rephrased_description = chat_response.choices[0].message.content

            except (AttributeError, NameError):
                # Fall back to older API
                client = MistralClient(api_key=api_key)

                # Create prompt
                prompt = f"""Rewrite this text as a natural, conversational chatbot response in paragraph form.
                Do NOT include any headings or section titles like 'Summary:' or 'Overview:'.
                Present all information as a flowing, cohesive paragraph without bullet points or numbered lists.
                Use a friendly, helpful tone as if directly answering a user's question.
                Do not add any information that is not present in the original text:

                {description}"""

                # Create chat messages
                messages = [
                    ChatMessage(role="user", content=prompt)
                ]

                # Get chat completion
                chat_response = client.chat(
                    model="mistral-small",
                    messages=messages,
                    max_tokens=4096
                )

                # Extract the rephrased content
                rephrased_description = chat_response.choices[0].message.content

            elapsed_time = time.time() - start_time
            print(f"API rephrasing completed in {elapsed_time:.2f} seconds")

            return rephrased_description

        except Exception as e:
            print(f"Error using Mistral API: {e}")
            print("Using local rephrasing instead.")
            return self._local_rephrase(description)

    def create_keyword_map(self, update_memory=True, save_to_file=True):
        """Create keyword map for single token mapping and optionally save to file.

        Parameters:
        update_memory (bool): Whether to update the KW_map in memory
        save_to_file (bool): Whether to save the KW_map to a file

        Returns:
        dict: The created keyword map
        """
        dictionary = self.backend_tables['dictionary']
        kw_map = {}

        for key in dictionary:
            if key.count('~') == 0:
                j = len(key)
                if j > 1:  # Make sure the key has at least 2 characters
                    keyB = key[0:j-1]
                    if keyB in dictionary and key[j-1] == 's':
                        if dictionary[key] > dictionary[keyB]:
                            kw_map[keyB] = key
                        else:
                            kw_map[key] = keyB

        # Update the KW_map in memory if requested
        if update_memory:
            # Merge with existing KW_map
            self.backend_tables['KW_map'].update(kw_map)
            print(f"Updated KW_map in memory with {len(kw_map)} entries")

        # Save to file if requested
        if save_to_file:
            try:
                # Save the COMPLETE KW_map from memory, not just the new entries
                complete_kw_map = self.backend_tables['KW_map']
                with open("KW_map.txt", "w") as f:
                    for key, value in complete_kw_map.items():
                        f.write(f"{key}\t{value}\n")
                print(f"Saved {len(complete_kw_map)} entries to KW_map.txt")
            except Exception as e:
                print(f"Error saving KW_map to file: {e}")

        return kw_map

    def save_backend_tables(self, force=False):
        """
        Save all backend tables to MongoDB, preserving existing data.

        Args:
            force (bool): If True, save even if data already exists in MongoDB
        """
        # Create and save the keyword map (never save to file)
        self.create_keyword_map(update_memory=True, save_to_file=False)

        # Save to MongoDB
        self._save_to_mongodb(force=force)

        print("Backend tables saved successfully!")

    def _save_to_local_files(self):
        """
        Save backend tables to local files as a fallback when MongoDB is not available.
        """
        try:
            # Create a directory for the data files if it doesn't exist
            data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
            os.makedirs(data_dir, exist_ok=True)

            # Save each table to a separate file
            for table_name, table_data in self.backend_tables.items():
                file_path = os.path.join(data_dir, f"{table_name}.pkl")
                with open(file_path, 'wb') as f:
                    pickle.dump(table_data, f)
                print(f"Saved {table_name} to {file_path}")

            # Save metadata
            metadata = {
                "timestamp": time.time(),
                "tables": list(self.backend_tables.keys())
            }
            with open(os.path.join(data_dir, "metadata.pkl"), 'wb') as f:
                pickle.dump(metadata, f)

            print("All tables saved to local files successfully!")
        except Exception as e:
            print(f"Error saving tables to local files: {e}")

    def _save_to_mongodb(self, force=False):
        """
        Save all backend tables to MongoDB.

        Args:
            force (bool): If True, save even if data already exists
        """
        if not self.use_mongodb or self.mongo_db is None:
            print("MongoDB not connected or disabled. Cannot save tables to MongoDB.")
            print("Using file-based storage instead.")
            self._save_to_local_files()
            return

        # Check if data already exists in MongoDB and skip saving if it does
        # unless force=True is specified
        if not force and self.mongo_db.dictionary.count_documents({}) > 0:
            print("Data already exists in MongoDB. Skipping save.")
            return

        try:
            # Save each table
            for table_name, table_data in self.backend_tables.items():
                # Skip empty tables
                if not table_data:
                    continue

                # Skip stopwords (handled separately)
                if table_name == 'stopwords':
                    continue

                collection = self.mongo_db[table_name]
                operations = []

                # Process items in batches
                for key, value in tqdm(table_data.items(), desc=f"Saving {table_name} to MongoDB", leave=False):
                    # Convert key to string for MongoDB _id
                    key_str = str(key)

                    # Handle nested dictionaries
                    if isinstance(value, dict):
                        value = {str(k): v for k, v in value.items()}

                    operations.append(
                        UpdateOne(
                            {"_id": key_str},
                            {"$set": {"value": value}},
                            upsert=True
                        )
                    )

                    # Execute batch when it reaches 2000 operations
                    if len(operations) >= 2000:
                        try:
                            collection.bulk_write(operations, ordered=False)
                            operations = []
                        except BulkWriteError as bwe:
                            print(f"Bulk write error in {table_name}: {bwe.details}")
                            operations = []

                # Execute remaining operations
                if operations:
                    try:
                        collection.bulk_write(operations, ordered=False)
                    except BulkWriteError as bwe:
                        print(f"Bulk write error in {table_name}: {bwe.details}")

                print(f"Saved {table_name} to MongoDB")

            # Save stopwords as a special case
            stopwords_collection = self.mongo_db['stopwords']
            stopwords_collection.delete_many({})  # Clear existing stopwords

            # Save each stopword with an index
            operations = []
            for i, word in enumerate(self.backend_tables['stopwords']):
                operations.append(
                    UpdateOne(
                        {"_id": str(i)},
                        {"$set": {"value": word}},
                        upsert=True
                    )
                )

            if operations:
                try:
                    stopwords_collection.bulk_write(operations, ordered=False)
                    print("Saved stopwords to MongoDB")
                except BulkWriteError as bwe:
                    print(f"Bulk write error in stopwords: {bwe.details}")

            # Save KW_map separately
            kw_collection = self.mongo_db['KW_map']
            operations = []
            for k, v in self.backend_tables['KW_map'].items():
                operations.append(
                    UpdateOne(
                        {"_id": str(k)},
                        {"$set": {"value": v}},
                        upsert=True
                    )
                )

            if operations:
                try:
                    kw_collection.bulk_write(operations, ordered=False)
                    print("Saved KW_map to MongoDB")
                except BulkWriteError as bwe:
                    print(f"Bulk write error in KW_map: {bwe.details}")

        except Exception as e:
            print(f"Error saving to MongoDB: {e}")
            print("Falling back to local file storage")
            self._save_to_local_files()

    def _save_to_local_files(self):
        """Save all backend tables to local files."""
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

        # Save KW_map (this is handled by create_keyword_map already if save_to_file=True)

        # Save embeddings separately if not already in backend_tables
        if 'embeddings' not in self.backend_tables:
            with open('backend_embeddings.txt', "w", encoding="utf-8") as f:
                f.write(str({}))

        # Save sorted_ngrams separately if not already in backend_tables
        if 'sorted_ngrams' not in self.backend_tables:
            with open('backend_sorted_ngrams.txt', "w", encoding="utf-8") as f:
                f.write(str({}))

    def ask_user_query(self):
        """
        Ask the user for a query, process it, and generate a description.
        The description is then rephrased for clearer explanation.
        """
        print("\n--------------------------------------------------------------------")
        print("Welcome to the Knowledge Retrieval System")
        print("Enter your query to get information from our knowledge base.")
        print("Type 'exit' or leave empty to quit.")
        print("Type 'local' before your query to skip API calls (e.g., 'local climate change')")
        print("--------------------------------------------------------------------\n")

        # Create embeddings table if not present
        if 'embeddings' not in self.backend_tables:
            self.create_embeddings()

        while True:
            user_input = input("Enter your query: ").strip()

            if not user_input or user_input.lower() == 'exit':
                print("\nThank you for using our system. Goodbye!")
                break

            # Parse special commands
            use_api = True
            user_query = user_input

            if user_input.lower().startswith('local '):
                use_api = False
                user_query = user_input[6:].strip()
                print("Using local rephrasing (no API calls)")

            try:
                # Process the query and generate description with PMI for original only
                original_description = self.generate_description(user_query, include_topics_and_pmi=True)

                # Generate a clean version without topics and PMI for rephrasing
                clean_description = self.generate_description(user_query, include_topics_and_pmi=False)

                # Rephrase the clean description with appropriate options
                # Note: Caching is disabled, use_cache parameter has no effect
                rephrased_description = self.rephrase_with_mistral(
                    clean_description,
                    use_api=use_api
                    # use_cache parameter omitted as it's not used
                )

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

            except Exception as e:
                print(f"Error processing query: {e}")




if __name__ == "__main__":
    # Create instance of KnowledgeRetrieval system
    knowledge_system = KnowledgeRetrieval()

    # Default file path for local data
    file_path = "/home/dtp2025-001/Pictures/corpus/uploads/uploads/repository_generated.txt"

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