from student.code_parser import extract_code, tool_call_reformer, ToolCall
from openai import OpenAI, RateLimitError
from dotenv import load_dotenv
from typing import Any
import time
import os
import json


def load_model() -> OpenAI:
    load_dotenv()
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"),
                    base_url="https://openrouter.ai/api/v1")
    return client


def respond(llm: OpenAI, model: str, prompt: str) -> str | None:
    response = llm.chat.completions.create(
                model=model,
                messages=[
                    {"role": "user", "content": prompt}
                ]
    )
    return response.choices[0].message.content


def load_tasks() -> list[dict[str, Any]]:
    try:
        with open("./moulinette/moulinette/mbpp/data/sanitized_tasks.json") as file:
            tasks = json.load(file)
        return tasks
    except (FileNotFoundError, PermissionError, Exception) as e:
        print(e)
        return []


def get_task_from_id(tasks: list[dict[str, Any]], id: int) -> dict[str, Any]:
    for task in tasks:
        if task["task_id"] == id:
            return task
    return {}

if __name__ == "__main__":
    client = load_model()
    answered = False
    tasks = load_tasks()
    if not tasks:
        print("Error when loading tasks")
        exit()
    
    task = get_task_from_id(tasks, 14)
    if not task:
        print("Error when search for specific task")
        exit()
    
    prompt = task["task_definition"] + " Only give the function"
    while not answered:
        try:
            result = respond(client, "google/gemma-4-31b-it:free",
                             prompt)
            answered = True
        except RateLimitError:
            print("Retrying in 10 sec")
            time.sleep(10)
    code = extract_code(result)
    print(code)
