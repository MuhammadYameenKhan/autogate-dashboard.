# AutoGate Rasa Chatbot

## Setup

```bash
pip install rasa
cd rasa_chatbot
rasa train
```

## Run

Terminal 1 — Action server:
```bash
cd rasa_chatbot
pip install -r actions/requirements.txt
rasa run actions --port 5055
```

Terminal 2 — Rasa server:
```bash
cd rasa_chatbot
rasa run --enable-api --cors "*" --port 5005
```

## Environment Variables (for actions server)
```
BACKEND_API_URL=http://localhost:5000/api
RASA_INTERNAL_TOKEN=          # optional — leave blank for dev
```
