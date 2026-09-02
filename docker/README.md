# Ollama Setup for Local LLM

This directory contains Docker configuration to run Ollama locally for AI-powered failure analysis.

## Prerequisites

- Docker and Docker Compose installed
- 2+ GB RAM available
- 5+ GB disk space (for LLM models)

## Quick Start

### 1. Start Ollama

```bash
cd docker
docker-compose up -d
```

This starts the Ollama service and exposes it on `http://localhost:11434`.

### 2. Pull a Model

Choose one of these small, efficient models:

**Gemma 2B (fastest, ~1GB)**
```bash
docker exec api_test_analysis_ollama ollama pull gemma:2b
```

**Gemma 7B (recommended, ~4GB)**
```bash
docker exec api_test_analysis_ollama ollama pull gemma:7b
```

**Mistral 7B (good quality, ~4GB)**
```bash
docker exec api_test_analysis_ollama ollama pull mistral:latest
```

### 3. Verify Installation

```bash
curl http://localhost:11434/api/tags
```

You should see the downloaded models listed.

### 4. Update Configuration

In `python/.env`, set the model name:

```
OLLAMA_API_URL=http://localhost:11434
OLLAMA_MODEL=gemma:7b
```

## Model Comparison

| Model | Size | Speed | Quality | RAM |
|-------|------|-------|---------|-----|
| Gemma 2B | 1.4GB | ⭐⭐⭐⭐⭐ | ⭐⭐ | 2GB |
| Gemma 7B | 4GB | ⭐⭐⭐ | ⭐⭐⭐⭐ | 4GB |
| Mistral 7B | 4GB | ⭐⭐⭐ | ⭐⭐⭐⭐ | 4GB |
| Llama 2 7B | 3.8GB | ⭐⭐⭐ | ⭐⭐⭐⭐ | 4GB |

## Stopping Ollama

```bash
docker-compose down
```

To remove models as well:

```bash
docker-compose down -v
```

## Troubleshooting

### Ollama not responding
```bash
docker logs api_test_analysis_ollama
```

### Out of memory
- Reduce resource limits in `docker-compose.yml`
- Use a smaller model (Gemma 2B)
- Ensure no other heavy processes are running

### Model download timeout
- Download manually outside container:
  ```bash
  docker exec -it api_test_analysis_ollama ollama pull gemma:7b
  ```

## Testing Ollama

```bash
curl -X POST http://localhost:11434/api/generate \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gemma:7b",
    "prompt": "Explain API failures",
    "stream": false
  }'
```

## Advanced Configuration

### Using GPU Acceleration

If you have NVIDIA GPU:

```yaml
services:
  ollama:
    # ... other config ...
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
```

### Custom Model Names

Update `OLLAMA_MODEL` in `python/.env` to any available model.

List available models:
```bash
curl http://localhost:11434/api/tags | jq '.models[].name'
```
