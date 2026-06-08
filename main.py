from app import create_app
from pdf_loader import load_pdf
from rag import chunk_text, build_index

app = create_app()

print("Loading medical knowledge base...")

text = load_pdf("common_disease_symptoms.pdf")

chunks = chunk_text(text)

build_index(
    chunks,
    "Common Disease Knowledge Base",
    user_id=None
)

print("Medical knowledge loaded.")

if __name__ == "__main__":
    app.run(debug=True)