import json
import os
import re
import uuid
import logging
import asyncio
from typing import List, Optional, Union
from app.utils.chunk import smart_chunk_text
from app.utils.docx_extreactinon import extract_docx_text
import pinecone
import pandas as pd
from fastapi import HTTPException
import os
from app.config import api_key,index_name,dimension,cloud,region,model
import google.generativeai as gen
import PyPDF2
import PyPDF2
import pandas as pd
import uuid
from typing import Optional

from app.utils.metadata import extract_metadata_llm
logger = logging.getLogger(__name__)


async def save_to_temp(file, id, user, category) -> str:
    company_id = user.company_id
    path = None
    try:
     
        dir_path = os.path.join("temps", str(company_id), category)
        os.makedirs(dir_path, exist_ok=True)

        path = os.path.join(dir_path, f"{id}_{file.filename}")
        with open(path, "wb") as f:
            f.write(file.file.read())

        return path
    except Exception as e:
        if path and os.path.exists(path):
            os.remove(path)
        raise HTTPException(status_code=500, detail=f"Failed to save temp file: {str(e)}")


def extract_text_from_file(file_path: str) -> str:
    ext = file_path.split('.')[-1].lower()
    
    if ext == "pdf":
        with open(file_path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            text = "".join(page.extract_text() or "" for page in reader.pages)
        if not text.strip():
            raise ValueError("Cannot process file: No text extracted")
        return text

    elif ext == "docx":
        text = extract_docx_text(file_path)  # Call the existing extract_docx_text function
        if not text.strip():
            raise ValueError("Cannot process file: No text extracted")
        return text

    elif ext == "xlsx":
        df = pd.read_excel(file_path, engine="openpyxl")
        if df.empty:
            raise ValueError("Cannot process file: No data extracted")
        return df.to_string()

    elif ext == "csv":
        df = pd.read_csv(file_path)
        if df.empty:
            raise ValueError("Cannot process file: No data extracted")
        return df.to_string()

    elif ext == "txt":
        with open(file_path, "r", encoding="utf-8") as f:
            text = f.read()
        if not text.strip():
            raise ValueError("Cannot process file: No text extracted")
        return text

    else:
        raise ValueError("Unsupported file format")




async def get_embedding(texts: Union[str, List[str]], api_key: str, output_dim: int = 1536) -> List[List[float]]:
    if isinstance(texts, str):
        texts = [texts] 
    if not texts:
        raise ValueError("No texts provided for embedding")
    
    gen.configure(api_key=api_key)
    
    def embed_sync():
        result = gen.embed_content(
            model=model,
            content=texts, 
            task_type="RETRIEVAL_DOCUMENT",
            output_dimensionality=output_dim
        )
        return result['embedding']  
    
    embeddings = await asyncio.get_event_loop().run_in_executor(None, embed_sync)
    return embeddings


def get_pinecone_index():

    if not api_key:
        raise ValueError("PINECONE_API_KEY environment variable is not set")
    
    pc = pinecone.Pinecone(api_key=api_key)
    
    existing_indexes = pc.list_indexes().names()
    if index_name not in existing_indexes:
        logger.info(f"Creating Pinecone index: {index_name} with dimension {dimension}")
        pc.create_index(
            name=index_name,
            dimension=dimension,
            metric="cosine",
            spec=pinecone.ServerlessSpec(cloud=cloud, region=region)
        )
        import time
        while not pc.describe_index(index_name).status['ready']:
            logger.info("Waiting for index to become ready...")
            time.sleep(1)
    else:
        logger.info(f"Using existing Pinecone index: {index_name}")
    
    return pc.Index(index_name)


async def process_uploaded_file(
    file_path, filename, file_id, google_api_key, category, company_id,
    building_id: Optional[int] = None
):

    try:

        text = extract_text_from_file(file_path)
        if not text.strip():
            logger.warning(f"No text extracted from file: {filename}")
            return

        metadata_info = await extract_metadata_llm(text)
        logger.info(f"Extracted Metadata for {filename}: {metadata_info}")

        tenant_name = metadata_info.get("tenant_name", "")
        building = metadata_info.get("building", "")
        floor = metadata_info.get("floor", "")

        chunks = await smart_chunk_text(text, google_api_key)
        if not chunks:
            logger.warning(f"No chunks generated for file: {filename}")
            return

        index = get_pinecone_index()
        embeddings = await get_embedding(chunks, google_api_key)

        vectors = []
        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            vector_id = str(uuid.uuid4())
            metadata = {
                "file_id": str(file_id),
                "file_name": filename,
                "company_id": str(company_id),
                "category": category,
                "building_id": str(building_id) if building_id else "",
                "tenant_name": tenant_name,
                "building": building,
                "floor": floor,
                "chunk": chunk,
                "total_chunks": len(chunks)
            }
            vectors.append((vector_id, embedding, metadata))
        if vectors:
            index.upsert(vectors=vectors)
            logger.info(f" Upserted {len(vectors)} vectors for file {filename} ({file_id})")
        else:
            logger.warning(f"No vectors to upsert for {filename}")

    except Exception as e:
        logger.error(f" Failed to process {filename} ({file_id}): {str(e)}")
        raise


async def extract_search_entities(question: str, google_api_key: str):
    """
    Use LLM to extract potential tenant_name, building, floor from a natural question.
    """
    from langchain.prompts import ChatPromptTemplate
    from langchain.chat_models import ChatVertexAI  # or your llm object


    try:
        llm_extractor = ChatVertexAI(model="gemini-1.5-flash", temperature=0, api_key=google_api_key)
        response = await llm_extractor.ainvoke(extraction_prompt.format_messages())
        content = response.content.strip()
        json_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", content, re.DOTALL)
        if json_match:
            content = json_match.group(1)
        entities = json.loads(content)
        return {
            "tenant_name": entities.get("tenant_name", "").strip().lower(),
            "building": entities.get("building", "").strip().lower(),
            "floor": entities.get("floor", "").strip().lower(),
        }
    except Exception as e:
        logger.warning(f"Entity extraction failed: {e}")
        return {"tenant_name": "", "building": "", "floor": ""}
