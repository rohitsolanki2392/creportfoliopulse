
from typing import List
import re
import json
import google.generativeai as gen
from app.services.prompts import dynamic_chunk_prompt, chunk_check_prompt
async def is_structured_text(sample_text: str, google_api_key: str) -> bool:
    try:
        print("checking if text is structured or unstructured via LLM...")
        gen.configure(api_key=google_api_key)
        model = gen.GenerativeModel("gemini-2.0-flash")



        result = model.generate_content(chunk_check_prompt)
        response = result.text.strip().lower()
        print(f" Structure detection LLM response: {response}")

        if "structured" in response and "unstructured" not in response:
            print("Final Decision: STRUCTURED text")
            return True
        else:
            print(" Final Decision: UNSTRUCTURED text")
            return False

    except Exception as e:
        print(f"[Fallback Structure Detection] Error: {e}")
        # Simple keyword-based heuristic if LLM check fails
        structured_keywords = ["tenant", "building", "floor", "address", "lease", "date:", "name:"]
        count = sum(1 for k in structured_keywords if k in sample_text.lower())
        print(f" Heuristic structure keyword match count: {count}")
        return count >= 3
    

def normal_split_text(text: str, max_chars: int = 800, overlap: int = 250) -> List[str]:
    print(" Using NORMAL CHUNKING (fast mode)...")
    cleaned_text = re.sub(r'\n\s*\n+', '\n\n', text.strip())
    chunks = [cleaned_text[i:i + max_chars] for i in range(0, len(cleaned_text), max_chars - overlap)]
    print(f" Normal chunking created {len(chunks)} chunks.")
    for i, c in enumerate(chunks[:3]):  # show first few
        print(f"Chunk {i+1} preview: {c}...\n")
    return chunks

async def dynamic_split_text(text: str, google_api_key: str, max_chars: int = 15000) -> List[str]:
    print("Using DYNAMIC CHUNKING (LLM-based)...")
    gen.configure(api_key=google_api_key)
    cleaned_text = re.sub(r'\n\s*\n+', '\n\n', text.strip())
    text_blocks = []
    start = 0
    while start < len(cleaned_text):
        text_blocks.append(cleaned_text[start:start + max_chars])
        start += max_chars

    all_chunks = []
    for block_no, block in enumerate(text_blocks, start=1):

        try:
            print(f" Processing block {block_no}/{len(text_blocks)}...")
            model = gen.GenerativeModel("gemini-2.0-flash")
            result = model.generate_content(dynamic_chunk_prompt)
            response_text = re.sub(r"^```json|```$", "", result.text.strip()).strip()
            chunks = json.loads(response_text)

            if isinstance(chunks, list) and all(isinstance(c, str) for c in chunks):
                for c in chunks:
                    cleaned_chunk = c.strip()
                    if cleaned_chunk and cleaned_chunk not in all_chunks:
                        all_chunks.append(cleaned_chunk)

        except Exception as e:
            print(f"[ Dynamic Split Fallback] Failed for block {block_no}: {e}")
            chunk_size = 800
            overlap = 250
            fallback_chunks = [block[i:i + chunk_size] for i in range(0, len(block), chunk_size - overlap)]
            for c in fallback_chunks:
                if c not in all_chunks:
                    all_chunks.append(c)

    print(f" Dynamic chunking created {len(all_chunks)} total chunks.")
    for i, c in enumerate(all_chunks[:3]):  # print first few chunks
        print(f" Chunk {i+1} preview: {c}...\n")

    return all_chunks

async def smart_chunk_text(text: str, google_api_key: str) -> List[str]:
    preview = text[:800]
    print("Checking if text is structured or unstructured...")
    is_structured = await is_structured_text(preview, google_api_key)

    print(f"Chunking Decision → {'DYNAMIC' if is_structured else 'NORMAL'}")
    if is_structured:
        print(" Detected STRUCTURED text → Using DYNAMIC chunking...")
        chunks = await dynamic_split_text(text, google_api_key)
    else:
        print(" Detected UNSTRUCTURED text → Using NORMAL chunking...")
        chunks = normal_split_text(text)

    print("Final chunk count: {len(chunks)}")
    if chunks:
        print(f" First chunk sample:\n{chunks}...\n")
    return chunks
