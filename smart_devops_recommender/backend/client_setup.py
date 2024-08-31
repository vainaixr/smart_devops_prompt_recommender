import os
import openai
import weaviate

# Initialize the OpenAI client
openai.api_key = os.getenv('OPENAI_KEY')  # Replace with your actual OpenAI API key

# Initialize the Weaviate client
client = weaviate.Client("http://localhost:8080")  # Replace with your Weaviate instance URL
