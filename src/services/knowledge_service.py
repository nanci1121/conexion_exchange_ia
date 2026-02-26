import asyncio
import os
import logging
from ..infrastructure.database.postgres import get_db_connection
from ..domain.knowledge.embedder import process_and_index_file
from psycopg2.extras import RealDictCursor

logger = logging.getLogger("KnowledgeService")

async def list_knowledge_documents():
    """List all indexed knowledge documents"""
    conn = await asyncio.to_thread(get_db_connection)
    if not conn:
        return []
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT DISTINCT filename, created_at FROM documents ORDER BY created_at DESC")
        files = cur.fetchall()
        cur.close()
        conn.close()
        
        # Format dates
        for f in files:
            if f['created_at']:
                f['created_at'] = f['created_at'].strftime("%Y-%m-%d %H:%M")
        return files
    except Exception as e:
        logger.error(f"Error listing documents: {e}")
        return []

async def upload_knowledge_document(file_path: str, filename: str):
    """Upload and index a knowledge document"""
    try:
        success, message = await asyncio.to_thread(process_and_index_file, file_path, filename)
        
        # Clean up temp file
        if os.path.exists(file_path):
            os.remove(file_path)
        
        return {
            "status": "success" if success else "error",
            "message": message
        }
    except Exception as e:
        logger.error(f"Error uploading document: {e}")
        return {
            "status": "error",
            "message": str(e)
        }
