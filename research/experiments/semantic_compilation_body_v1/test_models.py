import os
import json
import requests
import dotenv
from openai import OpenAI

dotenv.load_dotenv(r"C:\projects\model-gateway\.env")

print("--- 1. Testing AMD DeepSeek-V4-Flash ---")
try:
    amd_client = OpenAI(
        api_key=os.environ.get("AMD_API_KEY"),
        base_url="https://developer.amd.com.cn/radeon/api/v1"
    )
    res1 = amd_client.chat.completions.create(
        model="DeepSeek-V4-Flash",
        messages=[{"role": "user", "content": 'Output JSON: {"status": "ok", "model": "deepseek"}'}],
        max_tokens=60,
        response_format={"type": "json_object"}
    )
    print("AMD response:", res1.choices[0].message.content.strip())
except Exception as e:
    print("AMD error:", e)

print("--- 2. Testing Gemini 3.8 Flash ---")
try:
    g_key = os.environ.get("GOOGLE_API_KEY_1")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.8-flash:generateContent?key={g_key}"
    payload = {
        "contents": [{"parts": [{"text": 'Output JSON: {"status": "ok", "model": "gemini"}'}]}],
        "generationConfig": {"responseMimeType": "application/json"}
    }
    r2 = requests.post(url, json=payload, timeout=15)
    print("Gemini response:", r2.status_code, r2.json()["candidates"][0]["content"]["parts"][0]["text"].strip())
except Exception as e:
    print("Gemini error:", e)

print("--- 3. Testing GLM-4-flash ---")
try:
    glm_client = OpenAI(
        api_key=os.environ.get("GLM_API_KEY"),
        base_url="https://open.bigmodel.cn/api/paas/v4/"
    )
    res3 = glm_client.chat.completions.create(
        model="glm-4-flash",
        messages=[{"role": "user", "content": 'Output valid JSON only: {"status": "ok", "model": "glm"}'}],
        max_tokens=60
    )
    print("GLM response:", res3.choices[0].message.content.strip())
except Exception as e:
    print("GLM error:", e)
