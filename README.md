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

## Frontend

```bash
npm install
npm run dev
```

O Vite encaminha `/api` para `http://127.0.0.1:8000` durante o desenvolvimento.
Para ativar o acesso pessoal, configure `APP_ACCESS_PIN` antes do build/deploy
na Vercel. O PIN é embutido no bundle do frontend e a sessão fica salva no
`localStorage`; isso é uma proteção simples para uso pessoal, não uma autenticação
forte para dados sensíveis.

## Git

```bash
git add .
git commit -m "feat: add client-side PDF export and PIN access guard"
git push origin main
```
