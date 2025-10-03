import os
import uuid
import logging
import asyncio
from typing import List, Optional, Union
from app.utils.docx_extreactinon import extract_docx_text
import pinecone
import google.generativeai as genai
import pandas as pd
from fastapi import HTTPException
from docx.text.paragraph import Paragraph
import os
from google import genai
import google.generativeai as gen
import PyPDF2
import docx
from docx.table import Table
from docx.text.paragraph import Paragraph


logger = logging.getLogger(__name__)

client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))

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







import PyPDF2
import pandas as pd



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




def guess_mime_type(file_path: str) -> str:
    ext = file_path.split(".")[-1].lower()
    if ext == "pdf":
        return "application/pdf"
    elif ext == "docx":
        return "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    elif ext == "xlsx":
        return "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    elif ext == "csv":
        return "text/csv"
    elif ext == "txt":
        return "text/plain"
    else:
        return "application/octet-stream"





def extract_text_from_file_using_llm(file_path: str) -> str:
    """
    Extract text and tables from a file using Gemini.
    - Returns extracted text as string
    - Raises ValueError("Cannot process file: No text extracted") if fails
    """
    try:

        uploaded_file = client.files.upload(file=file_path)  


        response = client.models.generate_content(
            model="gemini-2.0-flash",   # or "gemini-1.5-flash"
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

        # 3. Get output
        text = getattr(response, "text", "").strip()
        if not text:
            raise ValueError("Cannot process file: No text extracted")
        return text

    except Exception as e:
        raise ValueError(f"Cannot process file: {e}")




async def get_embedding(texts: Union[str, List[str]], api_key: str, output_dim: int = 1536) -> List[List[float]]:
    if isinstance(texts, str):
        texts = [texts] 
    if not texts:
        raise ValueError("No texts provided for embedding")
    
    gen.configure(api_key=api_key)
    model = os.getenv("GEMINI_EMBEDDING_MODEL")
    
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


