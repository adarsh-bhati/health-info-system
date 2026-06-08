import os
from groq import Groq

try:
    from config import GROQ_API_KEY
except:
    GROQ_API_KEY = None

api_key = os.getenv("GROQ_API_KEY") or GROQ_API_KEY

if not api_key:
    raise ValueError("Groq API key not found in config.py or environment variables")

client = Groq(api_key=api_key)


def ask_ai(prompt):
    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0.5,
        max_tokens=500
    )

    return response.choices[0].message.content