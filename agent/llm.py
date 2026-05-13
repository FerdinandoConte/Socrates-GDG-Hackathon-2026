import os
from typing import Any, Type
from langchain_google_genai import ChatGoogleGenerativeAI


def get_llm() -> ChatGoogleGenerativeAI:
    return ChatGoogleGenerativeAI(
        model="gemini-3.1-flash-lite",
        google_api_key=os.getenv("GOOGLE_API_KEY"),
    )


def call_llm(system_prompt: str, user_message: str) -> str:
    llm = get_llm()
    response = llm.invoke([
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message},
    ])
    content = response.content
    # Gemini may return a list of content blocks instead of a plain string
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict) and "text" in block:
                parts.append(block["text"])
            elif isinstance(block, str):
                parts.append(block)
        return "\n".join(parts)
    return str(content)


def call_llm_structured(system_prompt: str, user_message: str, schema: Type[Any]) -> Any:
    llm = get_llm().with_structured_output(schema)
    return llm.invoke([
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message},
    ])
