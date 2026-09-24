import os
import glob
import time
import logging
import uuid

try:
    import PyPDF2
    import docx
    import openpyxl
    from langchain_text_splitters import RecursiveCharacterTextSplitter
    import chromadb
except ImportError:
    pass

logger = logging.getLogger(__name__)

LIBRARY_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "jarvis_library")
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "jarvis_vector_db")

# Add backwards compatibility for old dropzone
OLD_DROPZONE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "document_dropzone")

def init_dirs():
    if not os.path.exists(LIBRARY_DIR):
        os.makedirs(LIBRARY_DIR)

def parse_pdf(file_path: str) -> str:
    text = ""
    try:
        with open(file_path, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages:
                extracted = page.extract_text()
                if extracted:
                    text += extracted + "\n"
    except Exception as e:
        logger.error(f"[DOC PARSER] PDF parsing error: {e}")
    return text

def parse_docx(file_path: str) -> str:
    text = ""
    try:
        doc = docx.Document(file_path)
        for para in doc.paragraphs:
            text += para.text + "\n"
    except Exception as e:
        logger.error(f"[DOC PARSER] DOCX parsing error: {e}")
    return text

def parse_xlsx(file_path: str) -> str:
    text = ""
    try:
        wb = openpyxl.load_workbook(file_path, data_only=True)
        for sheet_name in wb.sheetnames:
            sheet = wb[sheet_name]
            text += f"--- Sheet: {sheet_name} ---\n"
            for row in sheet.iter_rows(values_only=True):
                text += " | ".join([str(cell) for cell in row if cell is not None]) + "\n"
    except Exception as e:
        logger.error(f"[DOC PARSER] XLSX parsing error: {e}")
    return text

def scan_and_parse_library():
    """สแกนไฟล์ใน jarvis_library ย่อยเป็นชิ้นๆ แล้วยัดเข้าสมอง RAG"""
    init_dirs()
    logger.info("[DOC PARSER] Scanning jarvis_library...")
    
    # Check old dropzone too just in case
    files = glob.glob(os.path.join(LIBRARY_DIR, "*.*"))
    if os.path.exists(OLD_DROPZONE):
        files.extend(glob.glob(os.path.join(OLD_DROPZONE, "*.*")))
        
    if not files:
        return "ไม่มีเอกสารใหม่ในแฟ้มเลยครับเจ้านาย"

    processed = 0
    
    # Initialize ChromaDB
    try:
        chroma_client = chromadb.PersistentClient(path=DB_PATH)
        collection = chroma_client.get_or_create_collection(name="jarvis_document_brain")
    except Exception as e:
        logger.error(f"[DOC PARSER] Failed to initialize ChromaDB: {e}")
        return f"เกิดข้อผิดพลาดในการเชื่อมต่อสมองเทียม: {e}"
        
    # Text Splitter settings
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        length_function=len,
    )
    
    for file_path in files:
        filename = os.path.basename(file_path)
        ext = filename.split('.')[-1].lower()
        
        content = ""
        if ext == 'pdf':
            content = parse_pdf(file_path)
        elif ext == 'docx':
            content = parse_docx(file_path)
        elif ext == 'xlsx':
            content = parse_xlsx(file_path)
        elif ext in ['txt', 'md']:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
            except Exception:
                pass
        else:
            continue
            
        if content.strip():
            logger.info(f"[DOC PARSER] Chunking and Embedding {filename}...")
            
            # Split into chunks
            chunks = text_splitter.split_text(content)
            
            docs = []
            metas = []
            ids = []
            
            for i, chunk in enumerate(chunks):
                docs.append(chunk)
                metas.append({
                    "source": filename,
                    "chunk": i
                })
                ids.append(f"doc_{uuid.uuid4().hex[:8]}_{i}")
                
            if docs:
                try:
                    collection.add(documents=docs, metadatas=metas, ids=ids)
                    logger.info(f"[DOC PARSER] Added {len(docs)} chunks from {filename} to Brain.")
                except Exception as e:
                    logger.error(f"[DOC PARSER] ChromaDB Add Error: {e}")
                    
            # Delete file after successful ingestion
            try:
                os.remove(file_path)
                processed += 1
            except Exception as e:
                logger.error(f"[DOC PARSER] Could not delete {filename}: {e}")
                
    if processed > 0:
        return f"อ่านและจดจำเอกสารสำเร็จแล้ว {processed} ไฟล์ครับเจ้านาย ตอนนี้ผมพร้อมตอบคำถามจากข้อมูลในนั้นแล้วครับ"
    return "สแกนแล้วแต่ไม่มีข้อมูลใหม่ที่ผมอ่านได้ครับ"

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print(scan_and_parse_library())
