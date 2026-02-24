import os
import torch
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
from peft import PeftModel

app = FastAPI(title="Email AI - LLM Service")

# Device detection (use CUDA if available on WSL)
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

model = None
tokenizer = None

class GenerateRequest(BaseModel):
    prompt: str
    max_tokens: int = 512
    temperature: float = 0.7
    top_p: float = 0.9

@app.on_event("startup")
async def load_model():
    global model, tokenizer
    print(f"Loading model. Target device: {DEVICE}")
    
    # Model configuration based on config.yaml specifications
    base_model_name = "TinyLlama/TinyLlama-1.1B-Chat-v1.0"
    adapter_path = "/app/modelo_correos_final"
    
    try:
        # Load the base tokenizer
        tokenizer = AutoTokenizer.from_pretrained(base_model_name, trust_remote_code=True)
        
        # BitsAndBytes configuration for 4-bit quantization
        bnb_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.float16,
            bnb_4bit_use_double_quant=True,
        )
        
        print(f"Loading base model {base_model_name} in 4-bit mode...")
        # Load base model
        base_model = AutoModelForCausalLM.from_pretrained(
            base_model_name,
            quantization_config=bnb_config,
            device_map="auto" if DEVICE == "cuda" else None,
            trust_remote_code=True,
        )
        
        # Load the LoRA adapter if it exists in the mounted volume
        if os.path.exists(adapter_path):
            print(f"Applying LoRA adapter from {adapter_path}...")
            model = PeftModel.from_pretrained(base_model, adapter_path)
            print("Model+Adapter successfully loaded!")
        else:
            print(f"WARNING: Adapter path '{adapter_path}' not found. Serving BASE model only.")
            model = base_model
            
    except Exception as e:
        print(f"FAILED to load model on startup: {str(e)}")
        # In production we might raise the error, but for development we just log it
        # so the container doesn't crash loop immediately

@app.post("/generate")
async def generate_text(req: GenerateRequest):
    if model is None or tokenizer is None:
        raise HTTPException(status_code=503, detail="Model is not loaded or failed to load")
        
    try:
        inputs = tokenizer(req.prompt, return_tensors="pt").to(DEVICE)
        
        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=req.max_tokens,
                temperature=req.temperature,
                top_p=req.top_p,
                do_sample=True,
                pad_token_id=tokenizer.eos_token_id,
                eos_token_id=tokenizer.eos_token_id,
            )
            
        # Decode the generated text, excluding the prompt itself
        prompt_length = inputs["input_ids"].shape[-1]
        generated_tokens = outputs[0][prompt_length:]
        generated_text = tokenizer.decode(generated_tokens, skip_special_tokens=True)
        
        return {"response": generated_text}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Inference error: {str(e)}")

@app.get("/health")
async def health_check():
    return {
        "status": "ok" if model is not None else "failed",
        "device": DEVICE,
        "is_quantized": True
    }
