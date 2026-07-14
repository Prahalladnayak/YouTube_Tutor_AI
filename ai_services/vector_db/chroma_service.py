import threading

_client_lock = threading.Lock()
_chroma_client = None

def get_chroma_client():
    """Thread-safe singleton ChromaDB client manager"""
    global _chroma_client
    if _chroma_client is None:
        with _client_lock:
            if _chroma_client is None:
                # Lazy import to prevent ChromaDB loading at startup
                import chromadb
                print("💾 Initializing global in-memory ChromaDB client...")
                _chroma_client = chromadb.Client()
                print("✅ Global ChromaDB client initialized.")
    return _chroma_client
