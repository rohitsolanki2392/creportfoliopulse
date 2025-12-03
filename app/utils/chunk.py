
from typing import List
import re
import json
import google.generativeai as gen
from app.services.prompts import dynamic_chunk_prompt, chunk_check_prompt
import re
from typing import List
import asyncio
from app.config import model

async def is_structured_text(sample_text: str, google_api_key: str) -> bool:
    try:
        gen.configure(api_key=google_api_key)
       



        result = model.generate_content(chunk_check_prompt)
        response = result.text.strip().lower()

        if "structured" in response and "unstructured" not in response:
            return True
        else:
            return False

    except Exception as e:       
        structured_keywords = ["tenant", "building", "floor", "address", "lease", "date:", "name:"]
        count = sum(1 for k in structured_keywords if k in sample_text.lower())
        return count >= 3
    

async def normal_split_text(text: str, max_chars: int = 800, overlap: int = 250) -> List[str]:

    def split_sync():
        cleaned_text = re.sub(r'\n\s*\n+', '\n\n', text.strip())
        chunks = [
            cleaned_text[i:i + max_chars]
            for i in range(0, len(cleaned_text), max_chars - overlap)
        ]
        return chunks
    return await asyncio.to_thread(split_sync)


async def dynamic_split_text(text: str, google_api_key: str, max_chars: int = 15000) -> List[str]:
    gen.configure(api_key=google_api_key)
    cleaned_text = re.sub(r'\n\s*\n+', '\n\n', text.strip())
    text_blocks = []
    start = 0
    while start < len(cleaned_text):
        text_blocks.append(cleaned_text[start:start + max_chars])
        start += max_chars

    all_chunks = []
    for _, block in enumerate(text_blocks, start=1):

        try:
            result = model.generate_content(dynamic_chunk_prompt)
            response_text = re.sub(r"^```json|```$", "", result.text.strip()).strip()
            chunks = json.loads(response_text)

            if isinstance(chunks, list) and all(isinstance(c, str) for c in chunks):
                for c in chunks:
                    cleaned_chunk = c.strip()
                    if cleaned_chunk and cleaned_chunk not in all_chunks:
                        all_chunks.append(cleaned_chunk)

        except Exception as e:

            chunk_size = 800
            overlap = 250
            fallback_chunks = [block[i:i + chunk_size] for i in range(0, len(block), chunk_size - overlap)]
            for c in fallback_chunks:
                if c not in all_chunks:
                    all_chunks.append(c)


    return all_chunks

async def smart_chunk_text(text: str, google_api_key: str) -> List[str]:
    preview = text[:800]
    is_structured = await is_structured_text(preview, google_api_key)

    if is_structured:
        chunks = await dynamic_split_text(text, google_api_key)
    else:
        chunks =await normal_split_text(text)
    return chunks
