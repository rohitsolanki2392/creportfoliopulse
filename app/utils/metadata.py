import json

from app.utils.llm_client import llm

async def extract_metadata_llm(text: str) -> dict:

    prompt = f"""
You are an expert in reading lease and real estate documents.
From the text below, extract only the following three fields and return a JSON object exactly in this format:
{{
  "tenant_name": "",
  "building": "",
  "floor": ""
}}
Guidelines:
- "tenant_name" → refers to the tenant or company name occupying the premises.
- "building" → refers to the property address or lease location (like "62 West 45th Street").
- "floor" → refers to the floor number or level (like "11th Floor", "Ground Floor", etc.).
- If a field is not found, leave it empty ("").
Example:
Input:
"Document Label: Lease: 62 West 45th St, Utility NYC LLC, 11th Floor
Building: 62 West 45th Street
Tenant: UTILITY NYC LLC
Premises: entire eleventh (11th ) floor"
Output:
{{
  "tenant_name": "UTILITY NYC LLC",
  "building": "62 West 45th Street",
  "floor": "11th Floor"
}}
Now extract these three fields from this text (limit: first 2500 characters):
{text[:2500]}
"""

    try:
        response = await llm.ainvoke([{"role": "user", "content": prompt}])
        content = response.content.strip()

        # Clean JSON fences if present
        content = content.replace("```json", "").replace("```", "").strip()

        data = json.loads(content)
        print("Extracted Metadata:", data)
        print("____________________________________________")
        return {
            "tenant_name": data.get("tenant_name", "").strip(),
            "building": data.get("building", "").strip(),
            "floor": data.get("floor", "").strip()
        }

    except Exception as e:
        print(f"[Metadata Extraction Error] {e}")
        return {
            "tenant_name": "",
            "building": "",
            "floor": ""
        }
