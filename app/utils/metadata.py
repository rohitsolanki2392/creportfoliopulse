import json
import logging
from app.config import MODEL
import google.generativeai as genai
import logging
from app.utils.llm_client import invoke_llm_async

logger = logging.getLogger("app")


async def extract_metadata_llm(text: str) -> dict:
    if not text.strip():
        logger.info("DEBUG: Empty text, returning _empty()")
        return await _empty()

    detect_prompt = f"""Classify the document into ONE of:
    building_info | tenant_data | lease_agreement | general_text

    Text (≤1500 chars):
    {text[:1500]}"""
    
    try:
        doc_type_resp = await invoke_llm_async(detect_prompt, expect_json=False)
        doc_type = doc_type_resp.strip().lower()
        logger.info(f"DEBUG: doc_type detected: {doc_type}")
        if doc_type not in {"building_info", "tenant_data", "lease_agreement", "general_text"}:
            doc_type = "general_text"
    except Exception as e:
        logger.info(f"WARNING: Doc-type detection failed: {e}")
        doc_type = "general_text"

    core = {
        "tenant_name": "company / person renting the space",
        "building": "full address or property name",
        "floor": "suite / level (e.g. '11th Floor', 'Suite 100')",
        "landlord": "owner / leasing entity",
    }

    extra = {}
    if doc_type == "building_info":
        extra = {
            "owner": "owner of the building",
            "year_built": "year the building was constructed",
            "total_sf": "total rentable square footage",
            "floors": "total number of floors",
            "ceiling_height": "slab-to-slab height",
            "freight_elevator": "capacity + dimensions",
            "cleaning": "who provides cleaning",
        }
    elif doc_type == "tenant_data":
        extra = {
            "sq_ft": "leased square footage",
            "rent_per_sf": "starting rent $/SF",
        }

    schema = {**core, **extra}
    schema_json = json.dumps(schema, indent=2)

    prompt = f"""Return **only** valid JSON that exactly matches this schema.
        Leave a field empty ("") if the information is not present.

        Schema:
        {schema_json}

        Text (≤2500 chars):
        {text[:2500]}
    """

    try:
        data = await invoke_llm_async(prompt, expect_json=True, fallback={})
        logger.info(f"DEBUG: parsed data type: {type(data)}")
    except Exception as e:
        logger.error(f"WARNING: Metadata extraction failed: {e}")
        data = {}

    if not isinstance(data, dict):
        logger.info(f"ERROR: Expected dict from LLM, got {type(data)}. Returning empty metadata.")
        return await _empty()

    tenant_name = (data.get("tenant_name") or "").strip()
    building    = (data.get("building") or "").strip()
    floor       = (data.get("floor") or "").strip()
    landlord    = (data.get("landlord") or "").strip()

    parts = []
    if building:
        parts.append(building)
    if floor:
        parts.append(f"Floor {floor}")
    if tenant_name:
        parts.append(tenant_name)

    identifier = " – ".join(parts) if parts else " "

    result = {
        "tenant_name": tenant_name,
        "building": building,
        "floor": floor,
        "landlord": landlord,
        "document_type": doc_type,
        "identifier": identifier,
        **{k: (v or "").strip() for k, v in data.items() if k not in core},
    }

    logger.info(f"DEBUG: Final metadata result: {result}")
    return result


async def _empty() -> dict:
    return {
        "tenant_name": "", "building": "", "floor": "", "landlord": "",
        "document_type": "", "identifier": ""
    }
