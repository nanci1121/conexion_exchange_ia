import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from llama_cpp import Llama

app = FastAPI(title="Email AI - LLM GGUF Service")

# Path al nuevo modelo Llama-3.2-3B
MODEL_PATH = "/app/models/llama-3.2-3b-instruct-q4_k_m.gguf"

llm = None

class GenerateRequest(BaseModel):
    prompt: str
    max_tokens: int = 256
    temperature: float = 0.1
    top_p: float = 0.9

@app.on_event("startup")
async def load_model():
    global llm
    print(f"Loading GGUF model from {MODEL_PATH}...")
    try:
        # Llama 3.2 3B se beneficia de un contexto de hasta 128k, pero para correos 4096 es suficiente y ahorra RAM
        llm = Llama(
            model_path=MODEL_PATH,
            n_ctx=4096,
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
        # Template oficial de Llama 3.2 Instruct
        system_content = (
            "Eres un asistente de redacción de correos profesional. "
            "Responde directamente al mensaje de forma breve, amable y sin inventar datos ni enlaces."
        )
        
        full_prompt = (
            f"<|begin_of_text|><|start_header_id|>system<|end_header_id|>\n\n"
            f"{system_content}<|eot_id|>"
            f"<|start_header_id|>user<|end_header_id|>\n\n"
            f"{req.prompt}<|eot_id|>"
            f"<|start_header_id|>assistant<|end_header_id|>\n\n"
        )
        
        output = llm(
            full_prompt,
            max_tokens=min(req.max_tokens, 256),
            temperature=0.1,
            top_p=0.9,
            repeat_penalty=1.1,
            stop=["<|eot_id|>", "<|end_of_text|>", "---"],
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
