"""
Test script for the optimized rephrasing function.
This script demonstrates the performance improvements of the optimized rephrasing function.
"""

import time
import os
from optimized_mistral import rephrase_with_mistral, _local_rephrase

def test_rephrasing_performance():
    """Test the performance of different rephrasing options."""
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

    print("\n=== TESTING LOCAL REPHRASING ===")
    start_time = time.time()
    local_result = _local_rephrase(test_description)
    local_time = time.time() - start_time
    print(f"Local rephrasing completed in {local_time:.4f} seconds")
    print(local_result[:200] + "...")  # Show first 200 chars
    
    if os.environ.get("MISTRAL_API_KEY"):
        print("\n=== TESTING FAST MODE API REPHRASING ===")
        start_time = time.time()
        fast_result = rephrase_with_mistral(test_description, fast_mode=True)
        fast_time = time.time() - start_time
        print(f"Fast mode API rephrasing completed in {fast_time:.4f} seconds")
        print(fast_result[:200] + "...")  # Show first 200 chars
        
        print("\n=== TESTING STANDARD API REPHRASING ===")
        start_time = time.time()
        standard_result = rephrase_with_mistral(test_description, fast_mode=False)
        standard_time = time.time() - start_time
        print(f"Standard API rephrasing completed in {standard_time:.4f} seconds")
        print(standard_result[:200] + "...")  # Show first 200 chars
        
        print("\n=== TESTING CACHED REPHRASING ===")
        start_time = time.time()
        cached_result = rephrase_with_mistral(test_description, use_cache=True)
        cached_time = time.time() - start_time
        print(f"Cached rephrasing completed in {cached_time:.4f} seconds")
        print(cached_result[:200] + "...")  # Show first 200 chars
        
        # Print performance comparison
        print("\n=== PERFORMANCE COMPARISON ===")
        print(f"Local rephrasing:      {local_time:.4f} seconds")
        print(f"Fast mode API:         {fast_time:.4f} seconds")
        print(f"Standard API:          {standard_time:.4f} seconds")
        print(f"Cached rephrasing:     {cached_time:.4f} seconds")
        
        # Calculate speedup
        print("\n=== SPEEDUP COMPARISON ===")
        print(f"Fast mode vs Standard: {standard_time/fast_time:.2f}x faster")
        print(f"Cached vs Standard:    {standard_time/cached_time:.2f}x faster")
        print(f"Local vs Standard:     {standard_time/local_time:.2f}x faster")
    else:
        print("\nAPI testing skipped: MISTRAL_API_KEY environment variable not set")

if __name__ == "__main__":
    test_rephrasing_performance()
