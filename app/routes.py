from flask import (
    Blueprint,
    render_template,
    request,
    jsonify,
    redirect,
    url_for,
    send_from_directory,
    flash
)

from flask_login import login_required, current_user
from bson.objectid import ObjectId
from datetime import datetime
from . import mongo
from .ai_client import ask_ai
from rag import retrieve, build_index, chunk_text
from pdf_loader import load_pdf
import os

main_bp = Blueprint('main', __name__)


# =========================================================
# HELPERS
# =========================================================
def safe_object_id(value):
    try:
        return ObjectId(value)
    except:
        return None


# =========================================================
# HOME
# =========================================================
@main_bp.route('/')
def home():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))

    return redirect(url_for('auth.login'))


# =========================================================
# DASHBOARD
# =========================================================
@main_bp.route('/dashboard')
@login_required
def dashboard():
    user_id = str(current_user.id)

    total_chats = mongo.db.messages.count_documents({
        "user_id": user_id
    })

    total_symptoms = mongo.db.symptom_analysis.count_documents({
        "user_id": user_id
    })

    total_documents = mongo.db.documents.count_documents({
        "user_id": user_id
    })

    recent_chats = list(
        mongo.db.conversations.find({
            "user_id": user_id
        }).sort("created_at", -1).limit(5)
    )

    recent_symptoms = list(
        mongo.db.symptom_analysis.find({
            "user_id": user_id
        }).sort("created_at", -1).limit(5)
    )

    documents = list(
        mongo.db.documents.find({
            "user_id": user_id
        }).sort("created_at", -1)
    )

    return render_template(
        "dashboard.html",
        total_chats=total_chats,
        total_symptoms=total_symptoms,
        total_documents=total_documents,
        recent_chats=recent_chats,
        recent_symptoms=recent_symptoms,
        documents=documents
    )


# =========================================================
# CHAT PAGE
# =========================================================
@main_bp.route('/chat')
@login_required
def chat_page():
    return render_template('chat.html')


# =========================================================
# NEW CHAT
# =========================================================
@main_bp.route('/api/new-chat', methods=['POST'])
@login_required
def new_chat():
    user_id = str(current_user.id)

    convo = {
        "user_id": user_id,
        "title": "New Chat",
        "created_at": datetime.utcnow()
    }

    result = mongo.db.conversations.insert_one(convo)

    return jsonify({
        "conversation_id": str(result.inserted_id)
    })


# =========================================================
# GET ALL CONVERSATIONS
# =========================================================
@main_bp.route('/api/conversations')
@login_required
def get_conversations():
    user_id = str(current_user.id)

    convos = list(
        mongo.db.conversations.find({
            "user_id": user_id
        }).sort("created_at", -1)
    )

    data = []

    for convo in convos:
        data.append({
            "id": str(convo["_id"]),
            "title": convo.get("title", "New Chat")
        })

    return jsonify(data)


# =========================================================
# LOAD SINGLE CONVERSATION
# =========================================================
@main_bp.route('/api/conversation/<conversation_id>')
@login_required
def load_conversation(conversation_id):
    user_id = str(current_user.id)

    messages = list(
        mongo.db.messages.find({
            "user_id": user_id,
            "conversation_id": conversation_id
        }).sort("created_at", 1)
    )

    result = []

    for msg in messages:
        result.append({
            "role": msg["role"],
            "content": msg["content"]
        })

    return jsonify(result)


# =========================================================
# DELETE CONVERSATION
# =========================================================
@main_bp.route('/api/delete-conversation/<conversation_id>', methods=['POST'])
@login_required
def delete_conversation(conversation_id):
    user_id = str(current_user.id)

    convo_id = safe_object_id(conversation_id)

    if not convo_id:
        return jsonify({
            "status": "error"
        })

    mongo.db.messages.delete_many({
        "user_id": user_id,
        "conversation_id": conversation_id
    })

    mongo.db.conversations.delete_one({
        "_id": convo_id,
        "user_id": user_id
    })

    return jsonify({
        "status": "success"
    })


# =========================================================
# CHAT API
# =========================================================
@main_bp.route('/api/chat', methods=['POST'])
@login_required
def chat_api():
    data = request.get_json()

    user_message = data.get("message", "").strip()
    conversation_id = data.get("conversation_id")

    if not user_message:
        return jsonify({
            "response": "Please type a message."
        })

    if not conversation_id:
        return jsonify({
            "response": "Conversation missing."
        })

    user_id = str(current_user.id)

    convo = mongo.db.conversations.find_one({
        "_id": safe_object_id(conversation_id),
        "user_id": user_id
    })

    if not convo:
        return jsonify({
            "response": "Conversation not found."
        })

    # First message becomes title
    if convo.get("title") == "New Chat":
        mongo.db.conversations.update_one(
            {
                "_id": safe_object_id(conversation_id)
            },
            {
                "$set": {
                    "title": user_message[:40]
                }
            }
        )

    contexts, refs = retrieve(
        user_message,
        user_id=user_id
    )

    combined_context = "\n".join(contexts)

    prompt = f"""
    You are STRICTLY a healthcare AI assistant.

    Medical Context:
    {combined_context}

    User Question:
    {user_message}

    STRICT RULES:
    1. Answer ONLY health, medical, symptom, disease, wellness, lab report, medicine, hospital related questions.
    2. If the question is unrelated to healthcare, reply EXACTLY:
       "Sorry, I can only help with health and medical related questions."
    3. Never answer math, coding, history, geography, politics, entertainment, or any non-medical topic.
    4. No exact diagnosis.
    5. No prescriptions.
    6. Suggest doctor consultation if serious.
    7.Always answer if someone greet and remember his identity if he exploit.
    """ 

    ai_response = ask_ai(prompt)
    ai_response = ai_response.replace("**", "")
    now = datetime.utcnow()

    mongo.db.messages.insert_one({
        "user_id": user_id,
        "conversation_id": conversation_id,
        "role": "user",
        "content": user_message,
        "created_at": now
    })

    mongo.db.messages.insert_one({
        "user_id": user_id,
        "conversation_id": conversation_id,
        "role": "assistant",
        "content": ai_response,
        "created_at": now
    })

    return jsonify({
        "response": ai_response,
        "sources": refs
    })
# =========================================================
# SYMPTOM PAGE
# =========================================================
@main_bp.route('/symptoms')
@login_required
def symptoms_page():
    return render_template('symptoms.html')


# =========================================================
# SYMPTOM ANALYSIS API
# =========================================================
@main_bp.route('/api/analyze', methods=['POST'])
@login_required
def analyze_api():
    data = request.get_json()

    symptoms = data.get("symptoms", [])

    if not symptoms:
        return jsonify({
            "response": "No symptoms provided."
        })

    symptom_text = ", ".join(symptoms)

    # Global medical KB retrieval
    contexts, refs = retrieve(
        symptom_text,
        user_id=None
    )

    combined_context = "\n".join(contexts)

    prompt = f"""
You are a medical symptom assistant.

Use ONLY verified medical context:

{combined_context}

User symptoms:
{symptom_text}

Return:

1. Possible causes
2. Home care suggestions
3. Severity level
4. When doctor consultation is needed

Rules:
- No hallucinations
- No prescriptions
- General health guidance only
"""

    ai_response = ask_ai(prompt)
    ai_response = ai_response.replace("**", "")
    mongo.db.symptom_analysis.insert_one({
        "user_id": str(current_user.id),
        "symptoms": symptom_text,
        "result": ai_response,
        "created_at": datetime.utcnow()
    })

    return jsonify({
        "response": ai_response,
        "sources": refs
    })


# =========================================================
# SYMPTOM HISTORY API
# =========================================================
@main_bp.route('/api/symptom-history')
@login_required
def symptom_history():
    history = list(
        mongo.db.symptom_analysis.find({
            "user_id": str(current_user.id)
        }).sort("created_at", -1)
    )

    results = []

    for item in history:
        results.append({
            "symptoms": item["symptoms"],
            "result": item["result"]
        })

    return jsonify(results)


# =========================================================
# UPLOAD PAGE
# =========================================================
@main_bp.route('/upload')
@login_required
def upload_page():
    user_docs = list(
        mongo.db.documents.find({
            "user_id": str(current_user.id)
        }).sort("_id", -1)
    )

    return render_template(
        "upload.html",
        documents=user_docs
    )

# =========================================================
# UPLOAD PDF
# =========================================================
@main_bp.route('/upload-pdf', methods=['POST'])
@login_required
def upload_pdf():
    file = request.files.get("file")

    if not file:
        flash("No file selected")
        return redirect(url_for('main.upload_page'))

    # DUPLICATE CHECK
    existing = mongo.db.documents.find_one({
        "user_id": str(current_user.id),
        "filename": file.filename
    })

    if existing:
        flash("This PDF already exists.")
        return redirect(url_for('main.upload_page'))

    upload_folder = "uploads"
    os.makedirs(upload_folder, exist_ok=True)

    filepath = os.path.join(upload_folder, file.filename)

    file.save(filepath)

    pdf_text = load_pdf(filepath)

    chunks = chunk_text(pdf_text)

    build_index(
        chunks,
        file.filename,
        user_id=str(current_user.id)
    )

    mongo.db.documents.insert_one({
        "user_id": str(current_user.id),
        "filename": file.filename,
        "filepath": filepath,
        "created_at": datetime.utcnow()
    })

    flash("PDF uploaded and indexed successfully.")

    return redirect(url_for('main.upload_page'))

# =========================================================
# VIEW PDF
# =========================================================
@main_bp.route('/view-pdf/<doc_id>')
@login_required
def view_pdf(doc_id):
    doc = mongo.db.documents.find_one({
        "_id": ObjectId(doc_id),
        "user_id": str(current_user.id)
    })

    if not doc:
        return "Document not found", 404

    return send_from_directory(
        os.path.abspath("uploads"),
        doc["filename"]
    )
# =========================================================
# DELETE PDF
# =========================================================
@main_bp.route('/delete-pdf/<doc_id>')
@login_required
def delete_pdf(doc_id):
    doc = mongo.db.documents.find_one({
        "_id": safe_object_id(doc_id),
        "user_id": str(current_user.id)
    })

    if doc:
        if os.path.exists(doc["filepath"]):
            os.remove(doc["filepath"])

        mongo.db.documents.delete_one({
            "_id": safe_object_id(doc_id)
        })

    flash("Document deleted.")

    return redirect(url_for('main.upload_page'))


# =========================================================
# REPORT ANALYSIS
# =========================================================
# =========================================================
# REPORT ANALYSIS
# =========================================================
@main_bp.route('/analyze-report/<doc_id>')
@login_required
def analyze_report(doc_id):

    oid = safe_object_id(doc_id)

    if not oid:
        return "Invalid document ID", 400

    doc = mongo.db.documents.find_one({
        "_id": oid,
        "user_id": str(current_user.id)
    })

    if not doc:
        return "Document not found", 404

    pdf_text = load_pdf(doc["filepath"])

    if not pdf_text.strip():
        return "Could not extract text from PDF"

    prompt = f"""
Analyze this medical report EXACTLY as written.

STRICT RULES:
- Use ONLY report content
- No hallucinations
- Do NOT invent diseases
- Mention abnormal values clearly
- Explain in simple language
- General precautions only
- No prescriptions

Medical Report:
{pdf_text}

Return exactly:

1. Important abnormal findings
2. Normal findings
3. Medical meaning in simple language
4. Whether doctor consultation is advised
5. General precautions
"""

    analysis = ask_ai(prompt)
    analysis = analysis.replace("**", "")
    return render_template(
        "report_analysis.html",
        filename=doc["filename"],
        analysis=analysis
    )