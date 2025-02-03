import logging
import os
import pickle
from typing import List, Dict
import click
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


# Suppose you already have an embeddings function or an external library to generate embeddings.
# This could be OpenAI, Cohere, or Anthropic embeddings, etc.
def get_embedding(text, model="text-embedding-3-small"):
    text = text.replace("\n", " ")
    return client.embeddings.create(input=[text], model=model).data[0].embedding


def build_codebase_index(directory: str, index_path: str) -> Dict:
    """
    Reads all files from `directory`, chunks them, and stores a mapping from chunk embeddings to chunk text + metadata.
    Returns an index dictionary. Also saves index to disk for caching.
    """
    # If the index already exists on disk, we can return it right away.
    if os.path.exists(index_path):
        with open(index_path, "rb") as f:
            return pickle.load(f)

    # If no index exists, build it.
    # For each file in the directory:
    #   1. Read file content.
    #   2. Chunk the content (for instance, 200-400 tokens or ~1500 characters).
    #   3. Generate embeddings for each chunk.
    #   4. Store the chunk, the embedding, and the file name in a list or dictionary.

    index = {"chunks": []}  # Put all chunk info here.

    for root, dirs, files in os.walk(directory):
        for filename in files:
            click.echo(f"Indexing file: {filename}...")
            full_path = os.path.join(root, filename)
            # Basic check for text-like files
            if not filename.endswith(
                (
                    ".py",
                    ".js",
                    ".ts",
                    ".md",
                    ".txt",
                    ".java",
                    ".rs",
                    ".c",
                    ".cs",
                    ".sql",
                )
            ):
                continue
            with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()

            # Example simple chunking by lines or fixed-size segments.
            chunk_size = 1000
            for i in range(0, len(content), chunk_size):
                chunk_text = content[i : i + chunk_size]
                chunk_embedding = get_embedding(chunk_text)
                # Keep track of chunk + metadata
                index["chunks"].append(
                    {
                        "embedding": chunk_embedding,
                        "text": chunk_text,
                        "file_path": full_path,
                    }
                )

    # Save index to disk
    with open(index_path, "wb") as f:
        pickle.dump(index, f)
    return index


def retrieve_relevant_chunks(query: str, index: Dict, top_k: int = 3) -> List[Dict]:
    """
    Given a user query and an already-built index,
    compute the query embedding, find the top_k closest chunks, and return them.
    """
    query_embedding = get_embedding(query)

    # A simple approach is to compute cosine similarity by hand
    # or use a library to do vector similarity. We’ll do a naive example:
    def cosine_similarity(a: List[float], b: List[float]) -> float:
        # Simple manual implementation
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = sum(x * x for x in a) ** 0.5
        norm_b = sum(x * x for x in b) ** 0.5
        return dot / (norm_a * norm_b + 1e-8)

    # Score each chunk by similarity to the query
    chunk_scores = []
    for chunk_info in index["chunks"]:
        sim = cosine_similarity(query_embedding, chunk_info["embedding"])
        chunk_scores.append((chunk_info, sim))

    # Sort by descending similarity
    chunk_scores.sort(key=lambda x: x[1], reverse=True)

    # Return the top_k
    return [chunk_scores[i][0] for i in range(min(top_k, len(chunk_scores)))]
