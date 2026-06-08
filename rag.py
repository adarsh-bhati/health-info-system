from sentence_transformers import SentenceTransformer
import faiss
import numpy as np

# EMBEDDING MODEL
model = SentenceTransformer("all-MiniLM-L6-v2")

documents = []
metadata_store = []
index = None

SIMILARITY_THRESHOLD = 0.35


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


def build_index(chunks, source_name, user_id=None):
    global index

    if not chunks:
        return

    embeddings = model.encode(
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


def retrieve(query, k=5, user_id=None):
    global index

    if index is None:
        return ["No medical knowledge base loaded yet."], ["System"]

    if not query.strip():
        return ["Empty query received."], ["System"]

    query_embedding = model.encode(
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

        if user_id is not None:
            if meta["user_id"] is not None and meta["user_id"] != user_id:
                continue

        results.append(documents[idx])
        refs.append(meta["source"])

    if not results:
        return ["No relevant medical context found."], ["System"]

    return results, refs


def reset_index():
    global index
    global documents
    global metadata_store

    index = None
    documents = []
    metadata_store = []