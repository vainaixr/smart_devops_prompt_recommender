import os
import weaviate

# Initialize the client with OpenAI module configuration
# Initialize the client with OpenAI module configuration
client = weaviate.Client(
    "http://localhost:8080",  # Replace with your Weaviate instance URL
    additional_headers={
        "X-OpenAI-Api-Key": os.getenv('OPENAI_KEY')  # Replace with your actual OpenAI API key
    }
)
# # Define the schema
# schema = {
#     "classes": [
#         {
#             "class": "Prompts",
#             "description": "A class to store DevOps prompts",
#             "properties": [
#                 {
#                     "name": "text",
#                     "dataType": ["text"],
#                     "description": "The text of the prompt"
#                 }
#             ],
#             "vectorizer": "text2vec-openai"  # Use the OpenAI vectorizer
#         }
#     ]
# }
#
# # Create the schema
# client.schema.create(schema)

# Define the data to insert
data_object = {
    "text": "This is a sample prompt about climate change."
}

# Insert the data into the Prompts class
client.data_object.create(
    data_object,
    "Prompts"
)

print("Schema created and data inserted successfully.")
