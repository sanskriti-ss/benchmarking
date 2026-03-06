# LLM Agreeability Benchmark

A web application for testing how different LLMs respond to misconceptions and ethical dilemmas. Deploy it on Render and let users run their own benchmarks with their own API keys.

Our main findings are [here](main_findings.md).

## Features

- **Multi-LLM Support**: Test OpenAI (GPT) and Anthropic (Claude) models
- **Secure API Key Storage**: User API keys are encrypted and stored in MongoDB
- **Customizable Questions**: Users can edit and add their own test questions
- **No Keys Exposed Client-Side**: All API calls happen server-side

## Quick Start (Local Development)

1. **Clone and install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Set up MongoDB:**
   - Create a free cluster at [MongoDB Atlas](https://www.mongodb.com/atlas)
   - Get your connection string and add it to `.env`

3. **Generate an encryption key:**
   ```bash
   python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
   ```
   Add the output to `ENCRYPTION_KEY` in `.env`

4. **Run the app:**
   ```bash
   python app.py
   ```
   Visit `http://localhost:5000`

## Deploy on Render

1. Push this repo to GitHub

2. Create a new **Web Service** on [Render](https://render.com)

3. Connect your GitHub repo

4. Set environment variables in Render dashboard:
   - `MONGO_URI`: Your MongoDB Atlas connection string
   - `ENCRYPTION_KEY`: Generate using the command above
   - `FLASK_SECRET_KEY`: Will be auto-generated

5. Deploy! Render will use `render.yaml` configuration

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `MONGO_URI` | MongoDB connection string | Yes |
| `ENCRYPTION_KEY` | Fernet key for encrypting API keys | Yes |
| `FLASK_SECRET_KEY` | Flask session secret | Auto-generated |

## Project Structure

```
├── app.py              # Main Flask application
├── llm_framework.py    # Original CLI framework (for reference)
├── questions.csv       # Default test questions
├── requirements.txt    # Python dependencies
├── render.yaml         # Render deployment config
├── templates/
│   ├── index.html      # Dashboard
│   ├── api_keys.html   # API key management
│   ├── questions.html  # Question editor
│   └── results.html    # Results page
└── .env                # Local environment (not committed)
```

## Security Notes

- User API keys are encrypted at rest using Fernet symmetric encryption
- Keys are never exposed to the frontend
- Each user gets a unique session ID stored in a cookie
- MongoDB Atlas provides secure, cloud-hosted database
