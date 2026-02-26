import os
import logging
import fitz  # PyMuPDF
from docx import Document
from sentence_transformers import SentenceTransformer
import numpy as np

logger = logging.getLogger("KnowledgeBase")

# Cargamos el modelo de embeddings (ligero y rápido para CPU)
# 384 dimensiones - all-MiniLM-L6-v2
try:
    model = SentenceTransformer('all-MiniLM-L6-v2')
    logger.info("Modelo de embeddings cargado correctamente.")
except Exception as e:
    logger.error(f"Error cargando modelo de embeddings: {e}")
    model = None

def extract_text_from_pdf(file_path):
    text = ""
    try:
        with fitz.open(file_path) as doc:
            for page in doc:
                text += page.get_text()
    except Exception as e:
        logger.error(f"Error extrayendo texto de PDF {file_path}: {e}")
    return text

def extract_text_from_docx(file_path):
    text = ""
    try:
        doc = Document(file_path)
        for para in doc.paragraphs:
            text += para.text + "\n"
    except Exception as e:
        logger.error(f"Error extrayendo texto de DOCX {file_path}: {e}")
    return text

def chunk_text(text, chunk_size=500, overlap=50):
    """Divide el texto en trozos pequeños para mejor recuperación."""
    words = text.split()
    chunks = []
    for i in range(0, len(words), chunk_size - overlap):
        chunk = " ".join(words[i:i + chunk_size])
        chunks.append(chunk)
    return chunks

def process_and_index_file(file_path, filename):
    """Extrae texto, lo fragmenta y genera embeddings para la DB."""
    ext = os.path.splitext(filename)[1].lower()
    text = ""
    
    if ext == '.pdf':
        text = extract_text_from_pdf(file_path)
    elif ext in ['.docx', '.doc']:
        text = extract_text_from_docx(file_path)
    elif ext == '.txt':
        with open(file_path, 'r', encoding='utf-8') as f:
            text = f.read()
            
    if not text:
        return False, "No se pudo extraer texto del archivo."

    chunks = chunk_text(text)
    from ...infrastructure.database.postgres import get_db_connection
    
    conn = get_db_connection()
    if not conn: return False, "Error de conexión a DB."
    
    try:
        cur = conn.cursor()
        for i, chunk in enumerate(chunks):
            # Generar el embedding (vector numérico)
            embedding = model.encode(chunk).tolist()
            
            cur.execute("""
                INSERT INTO documents (filename, content, embedding, metadata)
                VALUES (%s, %s, %s, %s)
            """, (filename, chunk, embedding, '{}'))
            
        conn.commit()
        cur.close()
        conn.close()
        return True, f"Indexado correctamente en {len(chunks)} fragmentos."
    except Exception as e:
        logger.error(f"Error indexando documento {filename}: {e}")
        return False, str(e)

def search_knowledge(query, top_k=3):
    """Busca los fragmentos más relevantes para una pregunta."""
    if not model: return []
    
    query_embedding = model.encode(query).tolist()
    
    from ...infrastructure.database.postgres import get_db_connection
    conn = get_db_connection()
    if not conn: return []
    
    try:
        cur = conn.cursor()
        # Usamos el operador <=> de pgvector (distancia coseno)
        cur.execute("""
            SELECT content, filename, 1 - (embedding <=> %s::vector) as similarity
            FROM documents
            ORDER BY embedding <=> %s::vector
            LIMIT %s
        """, (query_embedding, query_embedding, top_k))
        
        results = cur.fetchall()
        cur.close()
        conn.close()
        return results
    except Exception as e:
        logger.error(f"Error buscando en conocimiento: {e}")
        return []
