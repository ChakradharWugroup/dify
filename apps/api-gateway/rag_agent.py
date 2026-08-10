import os
import glob
import fitz  # PyMuPDF
import numpy as np
import httpx
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DATA_DIR = "./company_data"
HF_API_KEY = os.environ.get("HF_API_KEY", "")
EMBEDDING_URL = "https://api-inference.huggingface.co/pipeline/feature-extraction/sentence-transformers/all-MiniLM-L6-v2"

# In-memory storage since we don't have ChromaDB
cached_documents = []
cached_embeddings = None

def chunk_text(text, chunk_size=1000, overlap=200):
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start += chunk_size - overlap
    return chunks

def get_embeddings(texts):
    headers = {"Authorization": f"Bearer {HF_API_KEY}"}
    response = httpx.post(EMBEDDING_URL, headers=headers, json={"inputs": texts}, timeout=30.0)
    if response.status_code != 200:
        logger.error(f"HF Embedding Error: {response.text}")
        return []
    return response.json()

def init_vector_store():
    global cached_documents, cached_embeddings
    
    if not os.path.exists(DATA_DIR):
        logger.warning(f"Data directory {DATA_DIR} not found.")
        return False

    pdf_files = glob.glob(os.path.join(DATA_DIR, "*.pdf"))
    txt_files = glob.glob(os.path.join(DATA_DIR, "*.txt"))
    csv_files = glob.glob(os.path.join(DATA_DIR, "*.csv"))
    all_files = pdf_files + txt_files + csv_files
    
    if not all_files:
        logger.warning(f"No documents found in {DATA_DIR}")
        return False
        
    logger.info(f"Found {len(all_files)} files. Reading content...")
    
    chunks = []
    
    # Sort files by size so we read small files first
    all_files.sort(key=lambda x: os.path.getsize(x))
    
    # Read files up to a limit so we don't blow up memory or API limits
    processed_count = 0
    for file_path in all_files:
        if processed_count >= 5:
            break
            
        file_size = os.path.getsize(file_path)
        if file_size > 500000: # Skip files larger than 500KB
            continue
            
        try:
            if file_path.endswith('.pdf'):
                doc = fitz.open(file_path)
                text = ""
                for page in doc:
                    text += page.get_text()
            else:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    text = f.read()
                    
            if text.strip():
                file_chunks = chunk_text(text)
                for c in file_chunks:
                    chunks.append({"source": os.path.basename(file_path), "content": c})
                processed_count += 1
        except Exception as e:
            logger.error(f"Error reading {file_path}: {e}")
            
    cached_documents = chunks
    cached_embeddings = np.array([]) # No longer used
    logger.info("Vector store built successfully.")
    return True

def cosine_similarity(a, b):
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

def get_rag_context(query: str, top_k: int = 3):
    global cached_documents, cached_embeddings
    
    if cached_embeddings is None:
        success = init_vector_store()
        if not success:
            return ""
            
    # VERY FAST LOCAL KEYWORD SEARCH
    stop_words = {"a", "an", "and", "are", "as", "at", "be", "but", "by", "for", "if", "in", "into", "is", "it", "no", "not", "of", "on", "or", "such", "that", "the", "their", "then", "there", "these", "they", "this", "to", "was", "will", "with", "what", "how", "when", "where", "who", "why", "so", "now", "system", "working", "get", "from", "can", "do", "does", "did", "have", "has", "had", "my", "your", "i", "you", "me"}
    query_words = set(query.lower().split()) - stop_words
    
    similarities = []
    for doc in cached_documents:
        content = doc['content'].lower()
        score = sum(1 for word in query_words if word in content and len(word) > 2)
        similarities.append(score)
            
    top_indices = np.argsort(similarities)[-top_k:][::-1]
    
    context = ""
    for idx in top_indices:
        # Only include if score > 0
        if similarities[idx] > 0:
            doc = cached_documents[idx]
            context += f"\n\nSource: {doc['source']}\nExcerpt: {doc['content']}"
        
    return context.strip()
