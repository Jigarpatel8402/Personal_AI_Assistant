from openai import OpenAI

client = OpenAI(
    base_url="http://127.0.0.1:1234/v1",
    api_key="lm-studio"
)

conversation_history = []
MAX_TURNS = 4   # <-- only keep last 4 turns

def ask_local_llm(text):
    conversation_history.append({"role": "user", "content": text})
    if len(conversation_history) > MAX_TURNS * 2:
        conversation_history[:] = conversation_history[-MAX_TURNS * 2:]

    # build CLEAN prompt (short + structured)
    prompt = "You are Jarvis — calm, polite, and smart.\n\n"

    for msg in conversation_history:
        prompt += f"{msg['role'].capitalize()}: {msg['content']}\n"

    prompt += "Jarvis:\n"

    response = client.chat.completions.create(
        model = "mistral-7b-instruct-v0.2",
        messages = [{"role": "user", "content": prompt}],
        temperature = 0.7
    )

    answer = response.choices[0].message.content

    # store assistant reply
    conversation_history.append({"role": "assistant", "content": answer})

    return answer
