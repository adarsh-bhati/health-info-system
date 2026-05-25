import requests
from config import GROQ_API_KEY

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"


def ask_ai(prompt, system=None):

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    messages = []

    if system:
        messages.append({
            "role": "system",
            "content": system
        })

    messages.append({
        "role": "user",
        "content": prompt
    })

    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 500
    }

    try:
        resp = requests.post(
            GROQ_URL,
            json=payload,
            headers=headers,
            timeout=20
        )

        resp.raise_for_status()

        data = resp.json()

        return data["choices"][0]["message"]["content"]

    except Exception as e:
        print("Groq Error:", e)
        return "I'm unable to reach the AI service right now."