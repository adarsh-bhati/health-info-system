from sentence_transformers import SentenceTransformer
import faiss
import numpy as np

# ==========================================================
# GLOBAL STORAGE
# ==========================================================
documents = []
metadata_store = []
index = None
model = None

SIMILARITY_THRESHOLD = 0.35


# ==========================================================
# LOAD MODEL ONLY WHEN NEEDED
# ==========================================================
def get_model():
    global model

    if model is None:
        print("Loading embedding model...")
        model = SentenceTransformer("all-MiniLM-L6-v2")

    return model


# ==========================================================
# SMART CHUNKING
# ==========================================================
def chunk_text(text, chunk_size=500, overlap=100):
    words = text.split()

    if not words:
        return []

    chunks = []
    start = 0

    while start < len(words):
        end = start + chunk_size
        chunk = " ".join(words[start:end])
        chunks.append(chunk)

        start += chunk_size - overlap

    return chunks


# ==========================================================
# BUILD VECTOR INDEX
# ==========================================================
def build_index(chunks, source_name, user_id=None):
    global index

    if not chunks:
        return

    model_instance = get_model()

    embeddings = model_instance.encode(
        chunks,
        normalize_embeddings=True,
        show_progress_bar=False
    )

    embeddings = np.array(embeddings).astype("float32")

    if index is None:
        dimension = embeddings.shape[1]
        index = faiss.IndexFlatIP(dimension)

    index.add(embeddings)

    for chunk in chunks:
        documents.append(chunk)
        metadata_store.append({
            "source": source_name,
            "user_id": user_id
        })


# ==========================================================
# RETRIEVE RELEVANT CONTEXT
# ==========================================================
def retrieve(query, k=5, user_id=None):
    global index

    if not query.strip():
        return ["Please enter a health-related question."], ["System"]

    # Lazy load model
    model_instance = get_model()

    # If no index yet, still allow general AI response
    if index is None:
        return [], []

    query_embedding = model_instance.encode(
        [query],
        normalize_embeddings=True,
        show_progress_bar=False
    )

    query_embedding = np.array(query_embedding).astype("float32")

    distances, indices = index.search(query_embedding, k)

    results = []
    refs = []

    for score, idx in zip(distances[0], indices[0]):

        if idx < 0:
            continue

        if score < SIMILARITY_THRESHOLD:
            continue

        meta = metadata_store[idx]

        # Per-user filtering
        if user_id is not None:
            if meta["user_id"] is not None and meta["user_id"] != user_id:
                continue

        results.append(documents[idx])
        refs.append(meta["source"])

    return results, refs


# ==========================================================
# RESET INDEX
# ==========================================================
def reset_index():
    global index
    global documents
    global metadata_store
    global model

    index = None
    documents = []
    metadata_store = []
    model = None