import os
import requests
from dotenv import load_dotenv


def main():
    load_dotenv()
    api_key = os.environ.get("OPENROUTER_API_KEY")

    response = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": "google/gemma-4-26b-a4b-it:free",
            "messages": [
                {"role": "user", "content": "write a fonction python fibonacci, be concise only code"}
            ],
            "max_tokens": 500,
        }
    )

    data = response.json()
    if "error" in data:
        print("Erreur API:", data["error"])
    else:
        print(data["choices"][0]["message"]["content"])
    # print(data)
    # print(data["choices"][0]["message"]["content"])


if __name__ == "__main__":
    main()
