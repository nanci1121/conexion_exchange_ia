# Modelos LLM

Esta carpeta contiene los modelos GGUF para el servicio LLM.

## Descargar Llama 3.2 3B GGUF

Para que la aplicación funcione, necesitas descargar el modelo **Llama 3.2 3B Instruct** en formato GGUF cuantizado Q4:

### Opción 1: Descargar desde Hugging Face (Recomendado)

```bash
# Requiere git-lfs instalado
git clone https://huggingface.co/Microsoft/Llama-3.2-3B-Instruct-GGUF

# O descargar directamente el archivo
wget https://huggingface.co/microsoft/Llama-3.2-3B-Instruct-GGUF/resolve/main/Llama-3.2-3B-Instruct-Q4_K_M.gguf
```

### Opción 2: Descargar desde TheBloke (Mirror)

```bash
wget https://huggingface.co/TheBloke/Llama-3.2-3B-Instruct-GGUF/resolve/main/Llama-3.2-3B-Instruct-Q4_K_M.gguf
```

### Opción 3: Usar script de descarga automática

```bash
python download_model.py
```

## Requisitos

- Espacio en disco: 2.5GB (para Q4_K_M cuantizado)
- RAM: 8GB mínimo (16GB recomendado)
- Conexión a internet estable (descarga ~2.5GB)

## Estructura esperada

```
llm_service/models/
├── llama-3.2-3b-instruct-q4_k_m.gguf    # Modelo principal (~2.5GB)
└── README.md                              # Este archivo
```

## Verificar descarga

Una vez descargado, verifica que el archivo existe:

```bash
ls -lh llm_service/models/llama-3.2-3b-instruct-q4_k_m.gguf
```

## Información del modelo

| Propiedad | Valor |
|-----------|-------|
| Modelo | Llama 3.2 3B Instruct |
| Tamaño | 2.5GB (Q4_K_M cuantizado) |
| Contexto | 128K tokens (configurado a 4K para correos) |
| Cuantización | Q4_K_M (4-bit) |
| Precisión | ~95-98% comparado con fp32 |
| Velocidad | ~10-15 tokens/seg en CPU (4 threads) |

## Notas importantes

1. **No commitear el modelo a Git**: Es demasiado pesado (~2.5GB)
2. **Ruta correcta**: El archivo DEBE estar en esta carpeta exactamente
3. **Nombre exacto**: DEBE ser `llama-3.2-3b-instruct-q4_k_m.gguf` (minúsculas)
4. **Dentro de Docker**: Se monta en `/app/models/` automáticamente

## Solución de problemas

### "Model not found" error
- Verifica que el archivo está en: `llm_service/models/llama-3.2-3b-instruct-q4_k_m.gguf`
- Reinicia Docker: `docker-compose restart email_ai_llm`

### "Out of memory" error
- Reduce `n_ctx` en app.py (actualmente 4096)
- Usa GPU si disponible (descomenta en docker-compose.yml)
- Aumenta RAM disponible

### Descarga muy lenta
- Usa un espejo alternativo (TheBloke)
- Descarga en paralelo con `aria2c`
- Usa torrent si disponible

## GPU Support (Opcional)

Si tienes NVIDIA GPU, modifica docker-compose.yml:

```yaml
deploy:
  resources:
    reservations:
      devices:
        - driver: nvidia
          count: 1
          capabilities: [gpu]
```

Esto acelera significativamente la generación de texto (~100x más rápido).
