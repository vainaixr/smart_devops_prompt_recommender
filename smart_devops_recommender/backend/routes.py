import json

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
import os
import openai
import weaviate
import polars as pl
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
from datetime import timedelta
from typing import Dict
from typing import List, Optional
from openai import OpenAI

openai_client = OpenAI()

from utils import generate_embedding, calculate_weighted_score

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True,
                   allow_methods=["*"], allow_headers=["*"])

# Initialize the OpenAI client
openai.api_key = os.getenv('OPENAI_KEY')  # Replace with your actual OpenAI API key

# Initialize the Weaviate client
client = weaviate.Client("http://localhost:8080")  # Replace with your Weaviate instance URL

# Define weights for each factor
weights = {
    "distance": 15.9,
    "time_elapsed_since_added": 2,
    "length": 0.05,
    "retrieval_count": 1
}


class ChatRequest(BaseModel):
    message: str
    top_n: int
    weights: Dict[str, float]
    distance_filter: float  # Add this field


class FeatureContribution(BaseModel):
    feature: str
    value: Optional[float]
    score: Optional[float]
    weight: Optional[float]
    contribution: Optional[float]

class ChatResponse(BaseModel):
    prompt: str
    response: str
    distance_score: Optional[float]
    time_elapsed_since_added_score: Optional[float]
    length_score: Optional[float]
    retrieval_count: Optional[int]
    retrieval_count_score: Optional[float]
    weighted_score: Optional[float]
    creation_time: Optional[float]
    time_elapsed: Optional[str]
    contributions: List[FeatureContribution]


def format_number(num):
    return round(num, 3)


# def format_time_elapsed(seconds):
#     if seconds >= 86400:
#         return f"{seconds / 86400:.2f} days"
#     elif seconds >= 3600:
#         return f"{seconds / 3600:.2f} hours"
#     elif seconds >= 60:
#         return f"{seconds / 60:.2f} minutes"
#     else:
#         return f"{seconds:.2f} seconds"


def format_time_elapsed(seconds):
    delta = timedelta(seconds=seconds)
    days = delta.days
    hours, remainder = divmod(delta.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{days} day {hours:02}:{minutes:02}:{seconds:02}"


@app.post("/recommender", response_model=List[ChatResponse])
async def recommender(request: ChatRequest):
    user_input = request.message
    top_n = request.top_n
    weights = request.weights
    distance_filter = request.distance_filter  # Get the distance filter from the request

    if not user_input:
        raise HTTPException(status_code=400, detail="No message provided")

    # Generate the embedding for the user input
    query_embedding = generate_embedding(user_input)

    # Perform the query using the nearVector filter
    result = client.query.get("DevOpsPrompts_v2",
                              ["prompt", "response", "retrievalCount", "_additional { distance, creationTimeUnix }"]) \
        .with_near_vector({"vector": query_embedding}).do()

    # Extract the results and process them
    if result['data']['Get']['DevOpsPrompts_v2']:
        items = [
            {
                "prompt": item["prompt"],
                "response": item["response"],
                "distance": item["_additional"]["distance"],
                "creation_time": int(item["_additional"]["creationTimeUnix"]) / 1000,  # Convert to seconds
                "retrieval_count": item["retrievalCount"]
            }
            for item in result['data']['Get']['DevOpsPrompts_v2']
        ]

        # Create a Polars DataFrame
        df = pl.DataFrame(items)

        # Filter out items with a distance greater than the distance filter
        df = df.filter(pl.col("distance") <= distance_filter)

        # Calculate the current time for time_elapsed_since_added calculation
        current_time = datetime.now().timestamp()

        # Calculate the time elapsed since the document was added
        df = df.with_columns([
            (current_time - pl.col("creation_time").cast(pl.Float64)).alias("time_elapsed_seconds")
        ])

        # Add columns for length, distance_score, time_elapsed_since_added_score, length_score, and retrieval_count_score
        df = df.with_columns([
            (1 - pl.col("distance")).alias("distance_score"),
            (1 - (pl.col("time_elapsed_seconds") / pl.col("time_elapsed_seconds").max())).alias(
                "time_elapsed_since_added_score"),
            (pl.col("response").str.len_chars() / pl.col("response").str.len_chars().max()).alias("length_score"),
            (pl.col("retrieval_count") / pl.col("retrieval_count").max()).alias("retrieval_count_score")
        ])

        # Ensure all scores are between 0 and 1
        df = df.with_columns([
            pl.col("distance_score").clip(0, 1),
            pl.col("time_elapsed_since_added_score").clip(0, 1),
            pl.col("length_score").clip(0, 1),
            pl.col("retrieval_count_score").clip(0, 1)
        ])

        # Calculate the weighted score
        df = df.with_columns(
            (weights["distance"] * pl.col("distance_score") +
             weights["time_elapsed_since_added"] * pl.col("time_elapsed_since_added_score") +
             weights["length"] * pl.col("length_score") +
             weights["retrieval_count"] * pl.col("retrieval_count_score")).alias("weighted_score")
        )

        # Sort items based on weighted score
        df = df.unique(subset=['prompt', 'response']).sort("weighted_score", descending=True)

        # Extract the top N responses
        top_results = df.head(top_n).to_dicts()

        # Update the retrieval count for the top results
        for result in top_results:
            update_retrieval_count(client, "DevOpsPrompts_v2", result["prompt"], result["response"])

        # Add contributions to the response
        for result in top_results:
            result["contributions"] = [
                {
                    "feature": "distance",
                    "value": format_number(result["distance"]),
                    "score": format_number(result["distance_score"]),
                    "weight": format_number(weights["distance"]),
                    "contribution": format_number(result["distance_score"] * weights["distance"])
                },
                {
                    "feature": "time_elapsed_since_added",
                    "value": result["creation_time"],
                    "score": format_number(result["time_elapsed_since_added_score"]),
                    "weight": format_number(weights["time_elapsed_since_added"]),
                    "contribution": format_number(
                        result["time_elapsed_since_added_score"] * weights["time_elapsed_since_added"])
                },
                {
                    "feature": "length",
                    "value": len(result["response"]),
                    "score": format_number(result["length_score"]),
                    "weight": format_number(weights["length"]),
                    "contribution": format_number(result["length_score"] * weights["length"])
                },
                {
                    "feature": "retrieval_count",
                    "value": result["retrieval_count"],
                    "score": format_number(result["retrieval_count_score"]),
                    "weight": format_number(weights["retrieval_count"]),
                    "contribution": format_number(result["retrieval_count_score"] * weights["retrieval_count"])
                }
            ]

            # Calculate the time elapsed in a human-readable format
            time_elapsed_seconds = result["time_elapsed_seconds"]
            result["time_elapsed"] = format_time_elapsed(time_elapsed_seconds)
    else:
        top_results = [{"prompt": "", "response": "I'm sorry, I don't have an answer for that.", "distance": None,
                        "distance_score": None, "time_elapsed_since_added_score": None, "length_score": None,
                        "retrieval_count": None,
                        "retrieval_count_score": None, "weighted_score": None, "creation_time": None,
                        "time_elapsed": None, "contributions": []}]

    # Include creation_time in the response
    return [ChatResponse(**res) for res in top_results]


def escape_graphql_string(value):
    return json.dumps(value)[1:-1]  # json.dumps adds quotes around the string, so we strip them

def update_retrieval_count(client, class_name, prompt, response):

    # Example usage
    prompt = escape_graphql_string(prompt)
    response = escape_graphql_string(response)

    # Search for the object with the given prompt and response
    result = client.query.get(
        class_name,
        ["prompt", "response", "retrievalCount"]
    ).with_where({
        "operator": "And",
        "operands": [
            {
                "path": ["prompt"],
                "operator": "Equal",
                "valueString": prompt
            },
            {
                "path": ["response"],
                "operator": "Equal",
                "valueString": response
            }
        ]
    }).with_additional(["id"]).do()

    if result and result['data']['Get'][class_name]:
        # Get the object ID and current retrieval count
        obj = result['data']['Get'][class_name][0]
        obj_id = obj['_additional']['id']
        current_retrieval_count = obj.get('retrievalCount', 0)

        # If current_retrieval_count is None, set it to 0
        if current_retrieval_count is None:
            current_retrieval_count = 0

        # Increment the retrieval count
        new_retrieval_count = current_retrieval_count + 1

        # Update the object with the new retrieval count
        client.data_object.update(
            data_object={
                "retrievalCount": new_retrieval_count
            },
            class_name=class_name,
            uuid=obj_id
        )
    else:
        print("Object not found")


class CompletionRequest(BaseModel):
    message: str


class CompletionResponse(BaseModel):
    prompt: str
    response: str


@app.post("/chat", response_model=CompletionResponse)
async def chat(request: CompletionRequest):
    user_input = request.message
    if not user_input:
        raise HTTPException(status_code=400, detail="No message provided")

    # Generate a response using OpenAI's Chat Completion API
    response = openai_client.chat.completions.create(
        model="gpt-4o-mini",  # Replace with the appropriate model
        messages=[
            {"role": "system",
             "content": """You are a DevOps helpful assistant. 
             Send Response as html format don't send information as ```html,
             Please necessary hyperlinks for information, don't add much
             Give Answer more descriptive, so that user can understand properly, also added steps if needed"""},
            {"role": "user", "content": user_input}
        ]
    )
    response_text = response.choices[0].message.content

    # Generate the embedding for the combined prompt and response
    combined_text = f"Prompt: {user_input} Response: {response_text}"
    embedding = generate_embedding(combined_text)

    # Store the prompt-response pair in Weaviate with the combined vector
    data_object = {
        "prompt": user_input,
        "response": response_text,
        "retrievalCount": 1  # Initialize retrieval count to 1 when the object is created
    }
    client.data_object.create(
        data_object=data_object,
        class_name="DevOpsPrompts_v2",
        vector=embedding
    )

    return CompletionResponse(prompt=user_input, response=response_text)


if __name__ == '__main__':
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
