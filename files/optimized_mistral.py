import re
import time
import os

# Cache for rephrased descriptions to avoid repeated API calls
_rephrase_cache = {}

def _local_rephrase(description):
    """
    Simple local rephrasing without API calls.
    This is a fallback method when API calls are not available or too slow.
    
    Parameters:
    description (str): The original description text
    
    Returns:
    str: A slightly improved description
    """
    # Simple improvements without changing content
    result = description
    
    # Remove redundant newlines
    result = re.sub(r'\n\s*\n+', '\n\n', result)
    
    # Clean up PMI section to make it more readable
    if "Term Relationships (PMI):" in result:
        result = result.replace("Term Relationships (PMI):", "Related Terms:")
        result = re.sub(r'- ([^:]+): ([0-9.]+)', r'- \1', result)
    
    # Make lists more readable
    result = re.sub(r'\n- ', '\n• ', result)
    
    # Improve readability of the summary section
    if "Summary:" in result:
        result = result.replace("Summary:", "Summary:\n")
    
    return result

def rephrase_with_mistral(description, use_api=True, use_cache=True, fast_mode=False):
    """
    Rephrase the generated description for clearer explanation.
    Optimized for speed with caching and local fallback options.

    Parameters:
    description (str): The original description text
    use_api (bool): Whether to use the Mistral API (True) or local rephrasing (False)
    use_cache (bool): Whether to use cached results for identical descriptions
    fast_mode (bool): If True, uses a faster model with shorter timeout

    Returns:
    str: A rephrased description that's clearer and more concise
    """
    # Check if the description is a "no relevant information found" message
    if "No relevant information found for query" in description:
        # Return the original message without rephrasing
        return description
        
    # Check cache first if enabled
    if use_cache and description in _rephrase_cache:
        print("Using cached rephrasing result")
        return _rephrase_cache[description]
        
    # If API use is disabled, use local rephrasing
    if not use_api:
        print("Using local rephrasing (no API call)")
        result = _local_rephrase(description)
        if use_cache:
            _rephrase_cache[description] = result
        return result

    # Try using the Mistral API
    try:
        start_time = time.time()
        
        from mistralai import Mistral
        import requests.exceptions

        # Get API key from environment variable
        api_key = os.environ.get("MISTRAL_API_KEY")

        if not api_key:
            print("Warning: MISTRAL_API_KEY environment variable not set. Using local rephrasing.")
            return _local_rephrase(description)

        # Initialize Mistral client
        # Use a faster model in fast mode
        model = "mistral-small-latest" if fast_mode else "mistral-medium-latest"
        client = Mistral(api_key=api_key)
        
        # Set timeout based on mode
        timeout = 5 if fast_mode else 15  # seconds

        # Create prompt for English - simplified in fast mode
        if fast_mode:
            prompt = f"""Rewrite this text in a clear, concise way without changing the meaning:
            {description}"""
        else:
            prompt = f"""Convert the following chatbot response into a clear, explanatory paragraph format.
                Keep the information comprehensive but present it as a cohesive explanation rather than a structured response.
                Do not include additional resources or conclusion sections. Focus only on explaining the content in a natural,
                conversational way and do not include PMI score explanation. IMPORTANT: Do not add any information that is not present in the original text.
                If the original says there are no results, preserve that message without trying to guess what the user meant:

                {description}"""

        # Get response from Mistral with timeout
        try:
            chat_response = client.chat.complete(
                model=model,
                messages=[
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
                timeout=timeout
            )
            
            # Extract the rephrased content
            rephrased_description = chat_response.choices[0].message.content
            
            # Cache the result if caching is enabled
            if use_cache:
                _rephrase_cache[description] = rephrased_description
                
            elapsed_time = time.time() - start_time
            print(f"API rephrasing completed in {elapsed_time:.2f} seconds")
            
            return rephrased_description
            
        except requests.exceptions.Timeout:
            print(f"API call timed out after {timeout} seconds. Using local rephrasing.")
            return _local_rephrase(description)

    except ImportError:
        print("Warning: mistralai package not installed. Using local rephrasing.")
        return _local_rephrase(description)
    except Exception as e:
        print(f"Error using Mistral AI: {e}. Using local rephrasing.")
        return _local_rephrase(description)

# Example usage in ask_user_query method
def example_ask_user_query():
    """
    Example of how to use the optimized rephrase_with_mistral function
    in the ask_user_query method.
    """
    print("\n--------------------------------------------------------------------")
    print("Welcome to the Knowledge Retrieval System")
    print("Enter your query to get information from our knowledge base.")
    print("Type 'exit' or leave empty to quit.")
    print("Type 'fast' before your query for faster processing (e.g., 'fast climate change')")
    print("Type 'local' before your query to skip API calls (e.g., 'local climate change')")
    print("--------------------------------------------------------------------\n")

    while True:
        user_input = input("Enter your query: ").strip()

        if not user_input or user_input.lower() == 'exit':
            print("\nThank you for using our system. Goodbye!")
            break
            
        # Parse special commands
        use_api = True
        fast_mode = False
        user_query = user_input
        
        if user_input.lower().startswith('fast '):
            fast_mode = True
            user_query = user_input[5:].strip()
            print("Using fast mode (smaller model, shorter timeout)")
            
        elif user_input.lower().startswith('local '):
            use_api = False
            user_query = user_input[6:].strip()
            print("Using local rephrasing (no API calls)")

        try:
            # Process the query and generate description with PMI
            original_description = "Sample description for " + user_query  # Replace with actual generation
            
            # Rephrase the description with appropriate options
            rephrased_description = rephrase_with_mistral(
                original_description,
                use_api=use_api,
                use_cache=True,
                fast_mode=fast_mode
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
    # Test the optimized rephrasing function
    test_description = """Based on your query: 'machine learning'

Related topics:
- Introduction to Machine Learning
- Supervised Learning Algorithms
- Neural Networks and Deep Learning
- Feature Engineering Techniques
- Model Evaluation Metrics
- Unsupervised Learning Methods
- Reinforcement Learning

Term Relationships (PMI):
- machine learning ↔ algorithm: 0.85
- machine learning ↔ model: 0.78
- machine learning ↔ data: 0.72
- machine learning ↔ neural: 0.65
- machine learning ↔ training: 0.61

Summary:
Machine learning is a branch of artificial intelligence that focuses on developing systems that can learn from and make decisions based on data.

Supervised learning algorithms are trained using labeled examples, where the desired output is known. These algorithms learn by comparing their actual output with correct outputs to find errors and modify the model accordingly.

Neural networks are a set of algorithms designed to recognize patterns, inspired by the human brain. Deep learning uses neural networks with many layers (deep neural networks) to analyze various factors of data.

Feature engineering is the process of using domain knowledge to extract features from raw data that make machine learning algorithms work better."""

    # Test with different options
    print("\n=== TESTING LOCAL REPHRASING ===")
    local_result = rephrase_with_mistral(test_description, use_api=False)
    print(local_result)
    
    print("\n=== TESTING FAST MODE (if API key available) ===")
    if os.environ.get("MISTRAL_API_KEY"):
        fast_result = rephrase_with_mistral(test_description, fast_mode=True)
        print(fast_result)
    else:
        print("No API key available, skipping fast mode test")
    
    print("\n=== TESTING CACHING ===")
    cached_result = rephrase_with_mistral(test_description, use_cache=True)
    print(cached_result)
