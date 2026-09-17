# dinheiro

## API local

```bash
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
uvicorn api.main:app --reload --port 8000
```

Configure as variáveis do Firebase e, para habilitar a análise com Gemini,
defina `GEMINI_API_KEY` no ambiente local. Sem essa chave, a rota de IA usa um
fallback local baseado em palavras-chave para manter o desenvolvimento possível.

Endpoint de interpretação:

```bash
curl -X POST http://localhost:8000/api/ai/parse-request \
  -H 'Content-Type: application/json' \
  -d '{"mensagem":"Meu PC está esquentando, travando e quero colocar um SSD mais rápido"}'
```

## Git

```bash
git add .
git commit -m "feat(api): complete sprint 1 & 2 - backend core, schemas, firestore crud and quote engine"
git push origin main
```
