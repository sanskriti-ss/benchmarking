import csv
import requests
from typing import List, Dict, Callable
import os
from dotenv import load_dotenv

# Define LLM API call functions (modular, customizable)
def call_openai(prompt: str, api_key: str) -> str:
    url = "https://api.openai.com/v1/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    data = {
        "model": "gpt-3.5-turbo",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 100
    }
    response = requests.post(url, headers=headers, json=data)
    return response.json()["choices"][0]["message"]["content"]

def call_anthropic(prompt: str, api_key: str) -> str:
    url = "https://api.anthropic.com/v1/messages"
    headers = {"x-api-key": api_key, "Content-Type": "application/json"}
    data = {
        "model": "claude-2.1",
        "max_tokens": 100,
        "messages": [{"role": "user", "content": prompt}]
    }
    response = requests.post(url, headers=headers, json=data)
    return response.json()["choices"][0]["message"]["content"]

# Add more LLMs here if we get credits

LLM_FUNCTIONS = {
    "openai": call_openai,
    "anthropic": call_anthropic,
    # Add more as needed
}


# Load API keys from .env file
load_dotenv()
API_KEYS = {
    "openai": os.getenv("OPENAI_API_KEY"),
    "anthropic": os.getenv("ANTHROPIC_API_KEY"),
    # Add more as needed
}

def ask_llms(questions: List[str], llms: List[str], api_keys: Dict[str, str]) -> List[Dict[str, str]]:
    results = []
    for q in questions:
        row = {"question": q}
        for llm in llms:
            func = LLM_FUNCTIONS[llm]
            row[llm] = func(q, api_keys[llm])
        results.append(row)
    return results

def main():
    # Read questions
    with open("questions.csv", "r") as f:
        reader = csv.DictReader(f)
        questions = [row["question"] for row in reader]

    llms = list(LLM_FUNCTIONS.keys())
    responses = ask_llms(questions, llms, API_KEYS)

    # Write responses
    with open("responses.csv", "w", newline="") as f:
        fieldnames = ["question"] + llms
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in responses:
            writer.writerow(row)

if __name__ == "__main__":
    # Ensure .env is set up
    if not API_KEYS["openai"] or not API_KEYS["anthropic"]:
        print("Please set your API keys in the .env file.")
    else:
        main()
