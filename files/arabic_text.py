import re
import random
from collections import Counter
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize, sent_tokenize
import nltk

# Download necessary NLTK resources
nltk.download('punkt')
nltk.download('stopwords')
nltk.download('punkt_tab')

# Use Arabic stopwords instead of English
stop_words = set(stopwords.words('arabic'))

def clean_text(text):
    # Remove citation numbers like [1], [2], etc.
    text = re.sub(r'\[\d+\]', '', text)

    # Normalize whitespace
    return re.sub(r'\s+', ' ', text).strip()

def generate_title(text):
    # Extract the first sentence as the title
    sentences = sent_tokenize(text)
    if sentences:
        return sentences[0].strip()
    return "بدون عنوان..."  # "Untitled..." in Arabic

def extract_keywords(text, max_keywords=14):
    # Extract keywords from Arabic text
    words = [w for w in word_tokenize(text) if re.match(r'[\u0600-\u06FF]+$', w) and w not in stop_words]
    freq = Counter(words)
    if not freq:
        return []
    # Return top N keywords, each repeated once
    keywords = [word for word, _ in freq.most_common(max_keywords // 2)]
    return keywords * 2  # Repeat each keyword

def random_category(text=""):
    # Arabic category patterns
    category_patterns = {
        'بيانات': ['بيانات', 'قاعدة بيانات', 'تحليلات', 'معلومات', 'مجموعة بيانات'],
        'تعلم الآلة': ['نموذج', 'تدريب', 'تنبؤ', 'خوارزمية', 'تعلم الآلة'],
        'واجهة برمجة التطبيقات': ['واجهة', 'نقطة نهاية', 'طلب', 'استجابة', 'واجهة برمجة'],
        'أمان': ['آمن', 'مصادقة', 'إذن', 'وصول', 'حماية'],
        'بنية تحتية': ['سحابة', 'خادم', 'حاوية', 'كوبرنيتس', 'دوكر'],
        'إرشادات': ['دليل', 'أفضل ممارسة', 'توصية', 'يجب', 'سياسة'],
        'تطوير': ['كود', 'برمجة', 'تطوير', 'برمجيات', 'تطبيق'],
        'توثيق': ['وثيقة', 'دليل', 'مرجع', 'تعليمات'],
        'اختبار': ['اختبار', 'جودة', 'تحقق', 'تأكيد'],
        'تكامل': ['اتصال', 'تكامل', 'مسار', 'سير العمل'],
        'حوكمة': ['حوكمة', 'امتثال', 'تنظيم', 'قانوني'],
    }

    words = set(word_tokenize(text.lower()))
    for category, keywords in category_patterns.items():
        if any(kw in words for kw in keywords):
            return category

    return random.choice(list(category_patterns.keys()))

def random_tower_option():
    return random.choice([
        "توثيق", "دليل", "درس تعليمي", "مرجع", "نظرة عامة", "أفضل ممارسة",
        "سياسة", "معيار", "مثال", "قالب", "مسرد", "مقالة", "تقرير",
        "إجراء", "مواصفات"
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

def process_file(input_path, output_path, append=True, max_description_length=150):
    """Process input file and generate structured data for Arabic text.

    Parameters:
    input_path (str): Path to the input Arabic text file
    output_path (str): Path to the output file
    append (bool): Whether to append to existing file or overwrite
    max_description_length (int): Maximum length of description text in characters
    """
    with open(input_path, 'r', encoding='utf-8') as file:
        raw_text = file.read()

    # Split into paragraphs as logical units
    paragraphs = [clean_text(p) for p in raw_text.split('\n') if p.strip()]

    # Further split long paragraphs into smaller chunks
    chunks = []
    for para in paragraphs:
        # If paragraph is short enough, keep it as is
        if len(para) <= max_description_length:
            chunks.append(para)
        else:
            # Split into sentences
            sentences = sent_tokenize(para)
            current_chunk = ""

            for sentence in sentences:
                # If adding this sentence would make the chunk too long, save current chunk and start a new one
                if len(current_chunk) + len(sentence) > max_description_length and current_chunk:
                    chunks.append(current_chunk.strip())
                    current_chunk = sentence
                # Otherwise, add the sentence to the current chunk
                else:
                    if current_chunk:
                        current_chunk += " " + sentence
                    else:
                        current_chunk = sentence

            # Add the last chunk if it's not empty
            if current_chunk:
                chunks.append(current_chunk.strip())

    # Get the last entity ID from existing file if appending
    start_id = get_last_entity_id(output_path) + 1 if append else 2000
    print(f"Starting entity generation from ID: {start_id}")
    print(f"Created {len(chunks)} entities from {len(paragraphs)} paragraphs")

    # Open file in append mode if append=True, otherwise in write mode
    mode = 'a' if append else 'w'
    with open(output_path, mode, encoding='utf-8') as outfile:
        for idx, chunk in enumerate(chunks):
            entity_id = start_id + idx
            entry = {
                'title_text': generate_title(chunk),
                'description_text': chunk,
                'tags_list_text': extract_keywords(chunk),
                'category_text': random_category(chunk),
                'tower_option_tower': random_tower_option()
            }
            outfile.write(f"{entity_id}~~{entry}\n")

        print(f"Generated {len(chunks)} new entities, from ID {start_id} to {start_id + len(chunks) - 1}")

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Process Arabic text file and generate structured data.')
    parser.add_argument('--input', '-i', default='/home/mandeep/Pictures/corpus/arabic_input.txt',
                        help='Path to input Arabic text file')
    parser.add_argument('--output', '-o', default='/home/mandeep/Pictures/corpus/uploads/arabic_repository_generated.txt',
                        help='Path to output file')
    parser.add_argument('--append', '-a', action='store_true', default=True,
                        help='Append to existing file (default: True)')
    parser.add_argument('--overwrite', '-w', action='store_false', dest='append',
                        help='Overwrite existing file instead of appending')
    parser.add_argument('--max-length', '-m', type=int, default=150,
                        help='Maximum length of description text in characters (default: 150)')

    args = parser.parse_args()

    print(f"Processing file: {args.input}")
    print(f"Output file: {args.output}")
    print(f"Mode: {'Append' if args.append else 'Overwrite'}")
    print(f"Max description length: {args.max_length} characters")

    process_file(args.input, args.output, args.append, args.max_length)
