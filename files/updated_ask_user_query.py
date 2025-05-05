"""
This file contains the updated ask_user_query method for final4.py
to use the optimized rephrase_with_mistral function.

To use this code:
1. Copy the ask_user_query method and replace the existing one in final4.py
2. The optimized rephrase_with_mistral function should already be in final4.py
"""

def ask_user_query(self):
    """
    Ask the user for a query, process it, and generate a description with PMI components.
    The description is then rephrased for clearer explanation with optimized performance.
    """
    print("\n--------------------------------------------------------------------")
    print("Welcome to the Knowledge Retrieval System")
    print("Enter your query to get information from our knowledge base.")
    print("Type 'exit' or leave empty to quit.")
    print("Type 'fast' before your query for faster processing (e.g., 'fast climate change')")
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
            original_description = self.generate_description(user_query)

            # Rephrase the description with appropriate options
            rephrased_description = self.rephrase_with_mistral(
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
