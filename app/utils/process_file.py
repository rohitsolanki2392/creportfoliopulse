import os
import uuid
import logging
import asyncio

from typing import List, Optional, Union
import pinecone
import google.generativeai as genai
import PyPDF2
import pandas as pd
import docx
from fastapi import HTTPException


import docx
import pandas as pd
from docx.table import Table
from docx.text.paragraph import Paragraph
import PyPDF2
import docx
import pandas as pd
import io
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



def extract_docx_mixed(file_path: str) -> str:
    doc = docx.Document(file_path)
    text_parts = []

    def table_to_text(table: Table) -> str:
        rows = []
        for row in table.rows:
            cells = [cell.text.strip() for cell in row.cells]
            if any(cells):  
                rows.append(cells)
        if rows:
            try:
                df = pd.DataFrame(rows)
                return df.to_string(index=False, header=False)
            except Exception:
                return "\n".join([" | ".join(r) for r in rows])
        return ""

    for element in doc.element.body:
        if isinstance(element, docx.oxml.CT_P):  
            para = Paragraph(element, doc)
            if para.text.strip():
                text_parts.append(para.text.strip())
        elif isinstance(element, docx.oxml.CT_Tbl):  
            table = Table(element, doc)
            table_text = table_to_text(table)
            if table_text:
                text_parts.append(table_text)

    full_text = "\n\n".join(text_parts)

    if not full_text.strip():
        raise ValueError("Cannot process file: No text extracted")

    return full_text


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
        text= extract_docx_mixed(file_path)
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
    
    genai.configure(api_key=api_key)
    model = os.getenv("GEMINI_EMBEDDING_MODEL")
    
    def embed_sync():
        result = genai.embed_content(
            model=model,
            content=texts, 
            task_type="RETRIEVAL_DOCUMENT",
            output_dimensionality=output_dim
        )
        return result['embedding']  
    
    embeddings = await asyncio.get_event_loop().run_in_executor(None, embed_sync)
    return embeddings

def get_pinecone_index():
    api_key = os.getenv("PINECONE_API_KEY")
    index_name = os.getenv("PINECONE_INDEX")
    dimension = os.getenv("EMBEDDING_DIMENSION")
    cloud = os.getenv("PINECONE_CLOUD")
    region = os.getenv("PINECONE_REGION")
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

async def process_uploaded_file(file_path,  filename,  file_id,  google_api_key,  category,  company_id,building_id: Optional[int] = None ):
    try:
        text = extract_text_from_file(file_path)

        if not text:
            logger.warning(f"No text extracted from {filename}")
            return
        
        chunk_size = 1000
        overlap = 200
        chunks = [text[i:i + chunk_size] for i in range(0, len(text), chunk_size - overlap)]
        
        index = get_pinecone_index()
        vectors = []
        
        print(len(chunks))
        if chunks:
            embeddings = await get_embedding(chunks, google_api_key)  
            vectors = []
            for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
                vector_id = f"{uuid.uuid4()}"
                metadata = {
                    "file_id": file_id,
                    "category": category,
                    "company_id": str(company_id),
                    "building_id": str(building_id) if building_id is not None else "",  
                    "total_chunks": len(chunks),
                    "chunk": chunk
                }

                vectors.append((vector_id, embedding, metadata))
        if vectors:
            index.upsert(vectors=vectors)
            logger.info(f"Upserted {len(vectors)} vectors for file {file_id}")
    except Exception as e:
        logger.error(f"Failed to process and upsert file {file_id}: {str(e)}")
        raise


