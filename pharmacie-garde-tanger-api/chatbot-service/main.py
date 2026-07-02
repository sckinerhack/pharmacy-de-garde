"""
Microservice: Chatbot Service
Responsabilité: Proxy sécurisé vers l'API Anthropic Claude
Port: 8002
"""
import os
import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional

app = FastAPI(
    title="Chatbot Service",
    description="Microservice proxy pour l'IA PharmAssist (Claude)",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Charger le fichier .env si présent pour le développement local
for path in [".env", "../.env", "../../.env"]:
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        k = k.strip()
                        v = v.strip().strip('"').strip("'")
                        if k and k not in os.environ:
                            os.environ[k] = v
        except Exception:
            pass
        break

DO_API_URL = "https://inference.do-ai.run/v1/chat/completions"
RAW_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
DO_API_KEY = os.getenv("DO_API_KEY", "")

# Utiliser ANTHROPIC_API_KEY si elle est valide (pas un placeholder)
if RAW_API_KEY and not any(placeholder in RAW_API_KEY for placeholder in ["sk-ant-", "COLLE_TA_CLE_ICI", "ta-cle-ici"]):
    DO_API_KEY = RAW_API_KEY


SYSTEM_PROMPT = """Tu es PharmAssist, assistant pharmacien bienveillant à Tanger.
Règles :
- Réponds en français, de façon claire et concise.
- Rappelle TOUJOURS de consulter un médecin ou un pharmacien.
- Ne remplace pas un avis médical. Urgent : orienter vers le SAMU (15).
- Structure tes réponses de façon très lisible (points clés, gras)."""


# ─── Modèles ─────────────────────────────────────────────────────────────────

class Message(BaseModel):
    role: str  # "user" | "assistant"
    content: str


class ChatRequest(BaseModel):
    messages: list[Message]
    max_tokens: Optional[int] = 1000
    model: Optional[str] = "claude-sonnet-4-20250514"


class ChatResponse(BaseModel):
    content: list[dict]
    model: str
    usage: dict


# ─── Routes ──────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok", "service": "chatbot-service"}


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Envoie un message à DigitalOcean Inference Router et retourne la réponse au format Claude."""
    if not DO_API_KEY:
        raise HTTPException(500, "API key non configurée")

    # Aplatit l'historique de la conversation dans un seul message pour contourner le bug de timeout multi-tours de DigitalOcean.
    if len(request.messages) > 1:
        history_text = "Historique de la conversation :\n"
        for m in request.messages[:-1]:
            sender = "Utilisateur" if m.role == "user" else "Assistant"
            history_text += f"[{sender}]: {m.content}\n"
        
        last_msg = request.messages[-1].content
        flattened_content = (
            f"[CONSIGNES SYSTÈME: {SYSTEM_PROMPT}]\n\n"
            f"{history_text}\n"
            f"Question actuelle de l'utilisateur :\n{last_msg}"
        )
    else:
        last_msg = request.messages[0].content
        flattened_content = (
            f"[CONSIGNES SYSTÈME: {SYSTEM_PROMPT}]\n\n"
            f"Question de l'utilisateur :\n{last_msg}"
        )

    messages = [{"role": "user", "content": flattened_content}]

    payload = {
        "model": "llama3.3-70b-instruct",
        "messages": messages,
        "max_tokens": request.max_tokens
    }

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {DO_API_KEY}"
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.post(DO_API_URL, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
            
            choices = data.get("choices", [])
            text_content = ""
            if choices:
                text_content = choices[0].get("message", {}).get("content", "")
            
            content_list = [{"type": "text", "text": text_content}]
            usage_dict = data.get("usage", {})
            mapped_usage = {
                "input_tokens": usage_dict.get("prompt_tokens", 0),
                "output_tokens": usage_dict.get("completion_tokens", 0)
            }
            
            return ChatResponse(
                content=content_list,
                model=data.get("model", "llama3.3-70b-instruct"),
                usage=mapped_usage
            )
        except httpx.HTTPStatusError as e:
            raise HTTPException(e.response.status_code, f"Erreur API DigitalOcean: {e.response.text}")
        except httpx.TimeoutException:
            raise HTTPException(504, "Timeout: l'API DigitalOcean ne répond pas")
        except Exception as e:
            raise HTTPException(500, f"Erreur inattendue: {str(e)}")


@app.get("/suggestions")
def get_suggestions():
    """Retourne les suggestions de questions prédéfinies."""
    return {
        "suggestions": [
            "Quels sont les effets secondaires du paracétamol ?",
            "Comment conserver mes médicaments ?",
            "Que faire en cas de fièvre ?",
            "C'est quoi un antibiotique ?",
            "Pharmacies de garde à Tanger aujourd'hui ?",
            "Comment gérer une allergie saisonnière ?"
        ]
    }
