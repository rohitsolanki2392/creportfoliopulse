
import os
import logging
from typing import Dict, List, Optional, Union
from uuid import uuid4
from app.services.prompts import GENERAL_PROMPT_TEMPLATE, SYSTEM_PROMPT
from app.utils.docx_extreactinon import extract_docx_text
import pinecone
import pandas as pd
from fastapi import HTTPException
import google.generativeai as gen
import PyPDF2
from typing import Optional
from app.utils.smarchunk import  FastUniversalChunker
from app.utils.embeding_utils import generate_embeddings, initialize_pinecone_index
from app.config import api_key,index_name,dimension,cloud,region,client,api_key,model,llm_model,EMBED_BATCH_SIZE
import time
from uuid import uuid4
import asyncio

logger = logging.getLogger(__name__)

async def save_to_temp(file, id, user, category) -> str:
    company_id = user.company_id
    path = None
    try:
        dir_path = os.path.join("uploads", str(company_id), category)
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
            output_dimensionality=output_dim,
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







async def generate_response(classification: str, query: str, contexts: List[str], history: List[Dict[str, str]]) -> str:
    gemini_history = [
        {"role": "user" if msg["role"] == "user" else "model", "parts": [msg["content"]]}
        for msg in history
    ]
    
    def _blocking_chat():
        chat = llm_model.start_chat(history=gemini_history)
        if classification == "RAG":
            prompt = SYSTEM_PROMPT.format(contexts=" ".join(contexts), query=query)
            response = chat.send_message(prompt)
        else:
            prompt = GENERAL_PROMPT_TEMPLATE.format(query=query)
            response = chat.send_message(prompt)
        
        return response.text

    return await asyncio.to_thread(_blocking_chat)





async def process_uploaded_file(
    file_path: str,
    filename: str,
    file_id: str,
    category: str,
    company_id: str,
    building_id: Optional[int] = None,
):
    try:
        logger.info(f"Extracting text from file: {filename}")
        text = await extract_text_from_file(file_path)
        if not text or not text.strip():
            logger.warning(f"No text extracted from file: {filename}")
            return 0

        logger.info(f"Chunking file: {filename}")
        chunker = FastUniversalChunker(llm_model)
        enriched_chunks = await chunker.chunk_document(
            text=text,
            filename=filename,
            user_id=company_id,
            category=category,
            file_id=file_id,
            building_id=building_id
        )

        if not enriched_chunks:
            logger.warning(f"No chunks generated for file: {filename}")
            return 0

   

   
        for i, chunk in enumerate(enriched_chunks, 1):
            meta = chunk["metadata"]

            preview = (chunk["text"].replace("\n", " ")[:400] + " ...") if len(chunk["text"]) > 400 else chunk["text"].replace("\n", " ")
            logger.debug(
                f"Chunk #{i}/{len(enriched_chunks)} | Title: {meta.get('chunk_title', 'Untitled')} | "
                f"Type: {meta.get('chunk_type', 'unknown')} | Doc: {meta.get('doc_type', 'unknown')} | "
                f"Entity: {meta.get('primary_entity_value', '—')} | Length: {len(chunk['text']):,} | Preview: {preview}"
            )

        logger.info(f"Generating embeddings for {len(enriched_chunks)} chunks")
        chunk_texts = [c["text"] for c in enriched_chunks]
        embeddings = await generate_embeddings(chunk_texts)

        vectors = []
        pinecone_index = initialize_pinecone_index()
        for chunk_data, emb in zip(enriched_chunks, embeddings):
            metadata = chunk_data["metadata"].copy()
            for k, v in metadata.items():
                if v is None:
                    metadata[k] = ""
                elif isinstance(v, (list, dict)):
                    metadata[k] = str(v)[:500]
                elif not isinstance(v, (str, int, float, bool)):
                    metadata[k] = str(v)
            vector_values = emb.tolist() if hasattr(emb, "tolist") else emb
            vectors.append({
                "id": str(uuid4()),
                "values": vector_values,
                "metadata": {
                    **metadata,
                    "text": chunk_data["text"],
                    "text_preview": chunk_data["text"][:800],
                    "file_id": file_id,
                    "filename": filename,
                    "category": category,
                    "company_id": str(company_id),
                    "building_id": str(building_id) if building_id is not None else "",
                    "uploaded_at": int(time.time()),
                }
            })
        logger.info(f"Prepared {len(vectors)} vectors for Pinecone for file: {file_id}")

        batch_size = EMBED_BATCH_SIZE or 100
        logger.info(f"Uploading {len(vectors)} vectors to Pinecone in batches of {batch_size}")
        for i in range(0, len(vectors), batch_size):
            batch = vectors[i:i + batch_size]
            await asyncio.to_thread(pinecone_index.upsert, vectors=batch)

        logger.info(f"SUCCESS: {len(vectors)} chunks stored in Pinecone for file: {filename}")
        return len(vectors)

    except Exception as e:
        logger.exception(f"Failed to process {filename} ({file_id}): {str(e)}")
        raise



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

