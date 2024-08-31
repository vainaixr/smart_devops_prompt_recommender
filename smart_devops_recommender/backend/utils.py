import openai
from openai import OpenAI
from datetime import datetime

client = OpenAI()


def generate_embedding(text):
    return client.embeddings.create(input=[text], model="text-embedding-ada-002").data[0].embedding


def calculate_weighted_score(item, weights, max_length, max_recency):
    # Normalize distance (lower distance is better, so we invert it)
    distance_score = 1 - item["distance"]

    # Normalize recency (more recent is better, so we invert the time difference)
    current_time = datetime.now().timestamp()
    recency_seconds = current_time - int(item["recency"])
    recency_score = 1 - (recency_seconds / max_recency)

    # Normalize length (longer length is better)
    length_score = len(item["response"]) / max_length

    # Ensure all scores are between 0 and 1
    distance_score = max(0, min(1, distance_score))
    recency_score = max(0, min(1, recency_score))
    length_score = max(0, min(1, length_score))

    # Calculate weighted score
    weighted_score = (
            weights["distance"] * distance_score +
            weights["recency"] * recency_score +
            weights["length"] * length_score
    )

    return distance_score, recency_score, length_score, weighted_score
