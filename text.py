import re
import random
from collections import Counter
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize, sent_tokenize
import nltk

# Uncomment these lines and add punkt_tab
nltk.download('punkt')
nltk.download('stopwords')
# Add this line to download punkt_tab resource
nltk.download('punkt_tab')

stop_words = set(stopwords.words('english'))

def clean_text(text):

    text = re.sub(r'\[\d+\]', '', text)

    return re.sub(r'\s+', ' ', text).strip()

def generate_title(text):

    sentences = sent_tokenize(text)
    if sentences:
        return sentences[0].strip()
    return "Untitled..."

def extract_keywords(text, max_keywords=14):
    words = [w.lower() for w in word_tokenize(text) if w.isalpha() and w.lower() not in stop_words]
    freq = Counter(words)
    if not freq:
        return []
    # Return top N keywords, each repeated once
    keywords = [word for word, _ in freq.most_common(max_keywords // 2)]
    return keywords * 2  # Repeat each keyword

def random_category(text=""):
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

    words = set(word_tokenize(text.lower()))
    for category, keywords in category_patterns.items():
        if any(kw in words for kw in keywords):
            return category.capitalize()

    return random.choice(list(category_patterns.keys())).capitalize()

def random_tower_option():
    return random.choice([
        "Documentation", "Guide", "Tutorial", "Reference", "Overview", "Best Practice",
        "Policy", "Standard", "Example", "Template", "Glossary", "Article", "Report",
        "Procedure", "Specification"
    ])

def get_last_entity_id(output_path):
    """Get the last entity ID from the existing output file."""
    try:
        with open(output_path, 'r', encoding='utf-8') as file:
            # Read the file line by line from the end to find the last valid entity
            lines = file.readlines()

            # Start from the end and go backwards
            for line in reversed(lines):
                line = line.strip()
                if line:  # Skip empty lines
                    # Extract the entity ID from the beginning of the line
                    parts = line.split('~~', 1)
                    if len(parts) >= 1 and parts[0].isdigit():
                        return int(parts[0])

            # If no valid entity found, return default starting ID
            return 1999  # So the next ID will be 2000
    except FileNotFoundError:
        # If the file doesn't exist, return default starting ID
        print(f"Output file {output_path} not found. Starting with ID 2000.")
        return 1999  # So the next ID will be 2000
    except Exception as e:
        print(f"Error reading last entity ID: {e}. Starting with ID 2000.")
        return 1999  # So the next ID will be 2000

def process_file(input_path, output_path, append=True):
    """Process input file and generate structured data.

    Parameters:
    input_path (str): Path to the input text file
    output_path (str): Path to the output file
    append (bool): Whether to append to existing file or overwrite
    """
    with open(input_path, 'r', encoding='utf-8') as file:
        raw_text = file.read()

    # Split into paragraphs as logical units
    paragraphs = [clean_text(p) for p in raw_text.split('\n') if p.strip()]

    # Get the last entity ID from existing file if appending
    start_id = get_last_entity_id(output_path) + 1 if append else 2000
    print(f"Starting entity generation from ID: {start_id}")

    # Open file in append mode if append=True, otherwise in write mode
    mode = 'a' if append else 'w'
    with open(output_path, mode, encoding='utf-8') as outfile:
        for idx, para in enumerate(paragraphs):
            entity_id = start_id + idx
            entry = {
                'title_text': generate_title(para),
                'description_text': para,
                'tags_list_text': extract_keywords(para),
                'category_text': random_category(para),
                'tower_option_tower': random_tower_option()
            }
            outfile.write(f"{entity_id}~~{entry}\n")

        print(f"Generated {len(paragraphs)} new entities, from ID {start_id} to {start_id + len(paragraphs) - 1}")

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Process text file and generate structured data.')
    parser.add_argument('--input', '-i', default='/home/mandeep/Pictures/corpus/input.txt',
                        help='Path to input text file')
    parser.add_argument('--output', '-o', default='/home/dtp2025-001/Pictures/corpus/uploads/uploads/repository_generated.txt',
                        help='Path to output file')
    parser.add_argument('--append', '-a', action='store_true', default=True,
                        help='Append to existing file (default: True)')
    parser.add_argument('--overwrite', '-w', action='store_false', dest='append',
                        help='Overwrite existing file instead of appending')

    args = parser.parse_args()

    print(f"Processing file: {args.input}")
    print(f"Output file: {args.output}")
    print(f"Mode: {'Append' if args.append else 'Overwrite'}")

    process_file(args.input, args.output, args.append)