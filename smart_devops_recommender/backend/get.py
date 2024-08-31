import polars as pl
from utils import generate_embedding
from client_setup import client
from polars_udfs import expanded_config
expanded_config()

# Define the query text
query_text = "How do you set up a CI/CD pipeline?"

# Generate the embedding for the query text
query_embedding = generate_embedding(query_text)

# Perform the query using the nearVector filter
result = client.query.get("DevOpsPrompts", ["prompt", "response", "_additional { distance }"]) \
    .with_near_vector({"vector": query_embedding}) \
    .do()

# Print the results with similarity scores
for item in result['data']['Get']['DevOpsPrompts']:
    print(f"Prompt: {item['prompt']}")
    print(f"Response: {item['response']}")
    print(f"Distance: {item['_additional']['distance']}\n")

# Extract the data from the query result
data = [
    {
        "prompt": item['prompt'],
        "response": item['response'],
        "distance": item['_additional']['distance']
    }
    for item in result['data']['Get']['DevOpsPrompts']
]

# Create a Polars DataFrame
df = pl.DataFrame(data)

print(query_text)
# Find unique rows
unique_df = df.unique().sort(by='distance', descending=False)

# Print the unique DataFrame
print(unique_df)