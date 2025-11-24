
import asyncio
import google.generativeai as genai
from app.config import model, dimension
from typing import List

async def generate_embeddings(chunks: List[str]) -> List[List[float]]:
    loop = asyncio.get_running_loop()

    async def embed_one(text: str) -> List[float]:
        response = await loop.run_in_executor(
            None,
            lambda: genai.embed_content(
                model,
                content=text,
                task_type="RETRIEVAL_DOCUMENT",
                output_dimensionality=dimension, 
            ),
        )

        if isinstance(response, dict) and "embedding" in response:
            return [float(x) for x in response["embedding"]]
        elif hasattr(response, "embedding"):
            return [float(x) for x in response.embedding.values]
        else:
            raise ValueError(f"Unexpected Gemini response: {response}")

    tasks = [embed_one(chunk) for chunk in chunks]
    embeddings = await asyncio.gather(*tasks)
    return embeddings


from pinecone import Pinecone, ServerlessSpec
from app.config import api_key, index_name, dimension, cloud, region

def initialize_pinecone_index():
    pc = Pinecone(api_key=api_key)
    if index_name not in [idx.name for idx in pc.list_indexes()]:
        pc.create_index(
            name=index_name,
            dimension=dimension,
            metric="cosine",
            spec=ServerlessSpec(cloud=cloud, region=region)
        )
    return pc.Index(index_name)
