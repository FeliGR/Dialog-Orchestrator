# Dialog Orchestrator

A microservice for generating personalized AI dialog responses by integrating user personality data with large language models. Now includes support for personality assessment evaluation via MPI-AE (Multi-dimensional Personality Inventory - Assessment Evaluation).

## Features

- **Personality-Driven Dialog**: Generates responses based on Big Five personality traits (openness, conscientiousness, extraversion, agreeableness, neuroticism)
- **GPT Integration**: Leverages OpenAI's GPT models for natural language generation
- **MPI-AE Evaluation**: Supports personality assessment evaluation with strict output parsing
- **RESTful API**: Clean HTTP endpoints for dialog generation and evaluation
- **Persona Engine Integration**: Connects with external personality service for user trait data
- **Rate Limiting**: Built-in API rate limiting and CORS support
- **Health Monitoring**: Health check endpoints for service monitoring
- **Clean Architecture**: Modular design with separation of concerns

## Quick Start

```bash
git clone https://github.com/your-username/Dialog-Orchestrator.git
cd Dialog-Orchestrator
pip install -r requirements.txt
python app.py
```

## Configuration

Create a `.env` file:

```env
SECRET_KEY=your-secret-key
OPENAI_API_KEY=your-openai-api-key
OPENAI_MODEL=gpt-4o
OPENAI_TEMPERATURE_DEFAULT=0.7
PERSONA_ENGINE_URL=http://localhost:5001
DEBUG=True
LOG_LEVEL=DEBUG
HOST=0.0.0.0
PORT=5002
CORS_ORIGINS=*
API_RATE_LIMIT=100
EVAL_DEFAULT_TYPE=none
EVAL_STRICT_OUTPUT_DEFAULT=true
```

### OpenAI Setup

1. Get your API key from [OpenAI Platform](https://platform.openai.com/api-keys)
2. Add it to your `.env` file as `OPENAI_API_KEY`

### Persona Engine Setup

1. Ensure the Persona Engine service is running on the configured URL
2. The service expects personality data with Big Five traits for each user

## Docker

```bash
docker-compose up -d
```

## API Usage

### Generate Dialog Response

```bash
POST /api/dialog/{user_id}
Content-Type: application/json

{
  "text": "Hello, how are you today?"
}
```

### MPI-AE Evaluation (Assessment Mode)

```bash
POST /api/dialog/{user_id}
Content-Type: application/json

{
  "text": "Given a statement of you: \"You are always prepared.\" Please choose from the following options to identify how accurately this statement describes you. Options: (A). Very Accurate (B). Moderately Accurate (C). Neither Accurate Nor Inaccurate (D). Moderately Inaccurate (E). Very Inaccurate Answer:",
  "eval": {
    "type": "mpi_ae",
    "strict_output": true,
    "seed": 42,
    "format_id": "MPI-120"
  }
}
```

### Run MPI Assessment

```bash
# Run the full MPI assessment
python eval/run_mpi_http.py --url http://localhost:5002 --user-id test_user --items inventories/mpi_120.csv

# Test the evaluation system
python test_evaluation.py
```

### Health Check

```bash
GET /health
```

## Tech Stack

- Python 3.10
- Flask 2.3.3
- LangChain 0.1.0
- OpenAI 1.55.3
- Marshmallow 3.20.1
- Gunicorn 21.2.0
- Docker 