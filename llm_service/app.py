import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from llama_cpp import Llama

app = FastAPI(title="Email AI - LLM GGUF Service")

# Path al modelo GGUF
MODEL_PATH = "/app/models/tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf"

llm = None

class GenerateRequest(BaseModel):
    prompt: str
    max_tokens: int = 512
    temperature: float = 0.7
    top_p: float = 0.9

@app.on_event("startup")
async def load_model():
    global llm
    print(f"Loading GGUF model from {MODEL_PATH}...")
    try:
        # Cargamos el modelo optimizado para CPU
        # n_ctx es el tamaño del contexto (tokens)
        # n_threads es el número de hilos de CPU a usar
        llm = Llama(
            model_path=MODEL_PATH,
            n_ctx=2048,
            n_threads=int(os.getenv("CPU_THREADS", 2)), 
            verbose=False
        )
        print("Model successfully loaded!")
    except Exception as e:
        print(f"FAILED to load model: {str(e)}")

@app.post("/generate")
async def generate_text(req: GenerateRequest):
    if llm is None:
        raise HTTPException(status_code=503, detail="Model is not loaded")
        
    try:
        # Prompt en formato TinyLlama Chat
        full_prompt = (
            f"<|system|>\n"
            f"Eres un asistente de atención al cliente experto. Escribe una respuesta profesional, amable y concisa al correo del usuario. "
            f"Responde directamente con la respuesta propuesta en español. No añadidas comentarios extra ni explicaciones sobre tu rol.</s>\n"
            f"<|user|>\n{req.prompt}</s>\n"
            f"<|assistant|>\n"
        )
        
        output = llm(
            full_prompt,
            max_tokens=req.max_tokens,
            temperature=0.4, # Bajamos temperatura para más coherencia
            top_p=0.9,
            repeat_penalty=1.2, # Evita bucles infinitos (como el "por favor, por favor")
            stop=["</s>", "<|user|>", "<|system|>", "Correo recibido"],
            echo=False
        )
        
        response_text = output["choices"][0]["text"].strip()
        return {"response": response_text}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Inference error: {str(e)}")

@app.get("/health")
async def health_check():
    return {
        "status": "ok" if llm is not None else "failed",
        "technology": "GGUF/llama.cpp",
        "model": "TinyLlama-1.1B"
    }
