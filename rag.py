import numpy as np

documents = []
metadata_store = []

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
    for chunk in chunks:
        documents.append(chunk)
        metadata_store.append({
            "source": source_name,
            "user_id": user_id
        })


def retrieve(query, k=5, user_id=None):
    if not query.strip():
        return [], []

    results = []
    refs = []

    query_words = query.lower().split()

    for doc, meta in zip(documents, metadata_store):

        if user_id is not None:
            if meta["user_id"] is not None and meta["user_id"] != user_id:
                continue

        score = 0

        for word in query_words:
            if word in doc.lower():
                score += 1

        if score > 0:
            results.append(doc)
            refs.append(meta["source"])

        if len(results) >= k:
            break

    return results, refs