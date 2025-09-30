import os
import json
import re
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from app.config import google_api_key
load_dotenv()



llm = ChatGoogleGenerativeAI(
    model="gemini-2.0-flash",
    google_api_key=google_api_key,
    temperature=0.2
)


def invoke_llm(prompt: str, expect_json: bool = True, fallback: dict = None):

    try:
        response = llm.invoke(prompt)
        content = getattr(response, "content", "").strip()

        if not expect_json:
            return content

        # Clean JSON if wrapped in code fences
        content = re.sub(r"^```(?:json)?|```$", "", content, flags=re.MULTILINE).strip()
        return json.loads(content)

    except Exception as e:
        return fallback or {"error": str(e), "raw": locals().get("content", "")}
