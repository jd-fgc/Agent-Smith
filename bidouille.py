# import os
# import requests
# from dotenv import load_dotenv
# import multiprocessing
# import io
# import sys
import asyncio


async def dire_coucou():
    print("Avant")
    await asyncio.sleep(1)
    print("Apres")


def main():
    asyncio.run(dire_coucou())
    # fake = io.StringIO()
    # sys.stdout = fake
    # print("hello")
    # print("world")
    # sys.stdout = sys.__stdout__

    # resultat = fake.getvalue()
    # print(f"Capturé : '{resultat}'")
    # code = "print('Hello')"
    # process = multiprocessing.Process(target=exec, args=(code,))
    # process.start()
    # process.join(timeout=30)

    # if process.is_alive():
    #     process.terminate()
    #     return "TIMEOUT"
    # namespace = {
    #     "__builtins__": {
    #         "print": print,
    #         "len": len,
    #         "range:": range
    #     }
    # }
    # exec("print(len([1,2,3]))", namespace)
    # exec("open('fichier.txt')", namespace)

    # load_dotenv()
    # api_key = os.environ.get("OPENROUTER_API_KEY")

    # response = requests.post(
    #     "https://openrouter.ai/api/v1/chat/completions",
    #     headers={
    #         "Authorization": f"Bearer {api_key}",
    #         "Content-Type": "application/json",
    #     },
    #     json={
    #         "model": "google/gemma-4-26b-a4b-it:free",
    #         "messages": [
    #             {"role": "user", "content": "write a fonction python fibonacci, be concise only code"}
    #         ],
    #         "max_tokens": 500,
    #     }
    # )

    # data = response.json()
    # if "error" in data:
    #     print("Erreur API:", data["error"])
    # else:
    #     print(data["choices"][0]["message"]["content"])
    # print(data)
    # print(data["choices"][0]["message"]["content"])


if __name__ == "__main__":
    main()
