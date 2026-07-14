import threading

_model_lock = threading.Lock()
_embedding_model = None

def get_embedding_model(model_name='paraphrase-multilingual-MiniLM-L12-v2'):
    """Thread-safe singleton model loader for SentenceTransformer"""
    global _embedding_model
    if _embedding_model is None:
        with _model_lock:
            if _embedding_model is None:
                # Lazy import to prevent heavy PyTorch loading at startup
                from sentence_transformers import SentenceTransformer
                print(f"📥 Loading embedding model: {model_name} (first time only)...")
                try:
                    # Attempt to load the multilingual model
                    _embedding_model = SentenceTransformer(model_name)
                    print(f"✅ Loaded: {model_name}")
                except Exception as e:
                    print(f"❌ Model load failed for {model_name}: {e}")
                    print("🔄 Loading smaller fallback model: all-MiniLM-L6-v2...")
                    _embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
                    print("✅ Loaded fallback model")
    return _embedding_model
