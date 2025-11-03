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
import google.generativeai as gen
import PyPDF2
from app.utils.metadata import extract_metadata_llm
from app.config import index_name,dimension,cloud,region,model
logger = logging.getLogger(__name__)
from app.config import api_key

async def save_to_temp(file, id, user, category) -> str:
    company_id = user.company_id
    path = None
    try:
        dir_path = os.path.join("temps", str(company_id), category)
        os.makedirs(dir_path, exist_ok=True)

        path = os.path.join(dir_path, f"{id}_{file.filename}")
        await asyncio.to_thread(lambda: open(path, "wb").write(file.file.read()))

        return path
    except Exception as e:
        if path and os.path.exists(path):
            await asyncio.to_thread(os.remove, path)
        raise HTTPException(status_code=500, detail=f"Failed to save temp file: {str(e)}")


async def extract_text_from_file(file_path: str) -> str:
    ext = file_path.split('.')[-1].lower()

    if ext == "pdf":
        def read_pdf():
            with open(file_path, "rb") as f:
                reader = PyPDF2.PdfReader(f)
                return "".join(page.extract_text() or "" for page in reader.pages)
        text = await asyncio.to_thread(read_pdf)
        if not text.strip():
            raise ValueError("Cannot process file: No text extracted")
        return text

    elif ext == "docx":
        text = await extract_docx_text(file_path) 
        if not text.strip():
            raise ValueError("Cannot process file: No text extracted from DOCX")
        return text

    elif ext == "xlsx":
        def read_xlsx():
            df = pd.read_excel(file_path, engine="openpyxl")
            if df.empty:
                raise ValueError("Cannot process file: No data extracted")
            return df.to_string()
        return await asyncio.to_thread(read_xlsx)

    elif ext == "csv":
        def read_csv():
            df = pd.read_csv(file_path)
            if df.empty:
                raise ValueError("Cannot process file: No data extracted")
            return df.to_string()
        return await asyncio.to_thread(read_csv)

    elif ext == "txt":
        def read_txt():
            with open(file_path, "r", encoding="utf-8") as f:
                text = f.read()
                if not text.strip():
                    raise ValueError("Cannot process file: No text extracted")
                return text
        return await asyncio.to_thread(read_txt)

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

async def get_pinecone_index():
    if not api_key:
        raise ValueError("PINECONE_API_KEY not set")

    pc = pinecone.Pinecone(api_key=api_key)
    existing_indexes = await asyncio.to_thread(lambda: pc.list_indexes().names())
    if index_name not in existing_indexes:
        logger.info(f"Creating Pinecone index: {index_name} with dimension {dimension}")
        await asyncio.to_thread(lambda: pc.create_index(
            name=index_name,
            dimension=dimension,
            metric="cosine",
            spec=pinecone.ServerlessSpec(cloud=cloud, region=region)
        ))
        while not await asyncio.to_thread(lambda: pc.describe_index(index_name).status['ready']):
            logger.info("Waiting for index to become ready...")
            await asyncio.sleep(1)
    else:
        logger.info(f"Using existing Pinecone index: {index_name}")
    return pc.Index(index_name)


async def process_uploaded_file(
    file_path, filename, file_id, google_api_key, category, company_id,
    building_id: Optional[int] = None
):
    try:
        text = await extract_text_from_file(file_path)
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

        index = await get_pinecone_index()
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
            await asyncio.to_thread(lambda: index.upsert(vectors=vectors))
            logger.info(f"Upserted {len(vectors)} vectors for file {filename} ({file_id})")
        else:
            logger.warning(f"No vectors to upsert for {filename}")

    except Exception as e:
        logger.error(f"Failed to process {filename} ({file_id}): {str(e)}")
        raise

from app.config import client
def extract_text_from_file_using_llm(file_path: str) -> str:

    try:

        uploaded_file = client.files.upload(file=file_path)  


        response = client.models.generate_content(
            model="gemini-2.0-flash",  
            contents=[
                uploaded_file,
                """You are an expert data extractor. Extract content from the given file, regardless of format: PDF, DOCX, TXT, CSV, or scanned image-based files. 
                Requirements:
                -If the file contains scanned images or PDFs, perform OCR to extract text accurately.
                -Extract all text, headings, bullet points, numbers, formulas, and annotations.
                -Preserve tables exactly as they appear in the file, keeping rows and columns intact in **markdown or CSV format**.
                -For images, describe them briefly if they contain important information.
                -Return only clean, structured content, without any unrelated metadata or formatting artifacts.
                -Organize the output logically, preserving the original structure of the document as much as possible.
                Output should be fully text-based, structured, and ready for further analysis or processing."""
            ],
        )

        text = getattr(response, "text", "").strip()
        if not text:
            raise ValueError("Cannot process file: No text extracted")
        return text

    except Exception as e:
        raise ValueError(f"Cannot process file: {e}")

