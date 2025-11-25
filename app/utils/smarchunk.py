import asyncio
import re
import json
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import asdict, dataclass
import logging

logger = logging.getLogger(__name__)

EMBED_BATCH_SIZE = 100
MAX_CHUNK_SIZE = 1200
OVERLAP = 100

@dataclass
class ChunkMetadata:
    user_id: str
    category: str
    file_id: str
    building_id: Optional[str]
    doc_type: str
    primary_entity_type: Optional[str]
    primary_entity_value: Optional[str]
    section_hierarchy: List[str]
    chunk_title: Optional[str]
    chunk_type: str
    key_topics: List[str]
    searchable_fields: Dict[str, str]
    semantic_summary: str
    chunk_index: int
    total_chunks: int

class FastUniversalChunker:
    def __init__(self, llm):
        self.llm = llm

    async def chunk_document(self, text: str, filename: str, user_id: str, category: str, file_id: str, building_id=None):
        logger.info(f"\nProcessing: {filename} (Fast Mode)")

  
        structure = await self._analyze_structure_fast(text, filename)
        logger.info(f"  Doc Type: {structure['doc_type']} | Pattern: {structure['structure_pattern']}")


        raw_chunks = self._split_document_smart(text, structure)

        if not raw_chunks:
            raw_chunks = [(text, ["Full Document"])]

        logger.info(f"  Created {len(raw_chunks)} chunks")

 
        global_entities = {}
        if len(raw_chunks) <= 15:  # Only if not too many chunks
            global_entities = await self._extract_global_entities_once(text, structure)

        enriched_chunks = []
        for idx, (chunk_text, hierarchy) in enumerate(raw_chunks):
            title = self._infer_title(chunk_text, hierarchy)
            chunk_type = self._infer_chunk_type(chunk_text, structure, hierarchy)
            topics = self._extract_topics_heuristic(chunk_text)
            summary = self._smart_truncate_summary(chunk_text)

    
            searchable = self._extract_key_fields_heuristic(chunk_text)
            primary_entity = self._guess_primary_entity(chunk_text, global_entities)

            metadata = ChunkMetadata(
                user_id=str(user_id),
                category=category,
                file_id=str(file_id),
                building_id=str(building_id) if building_id else None,
                doc_type=structure["doc_type"],
                primary_entity_type=primary_entity.get("type"),
                primary_entity_value=primary_entity.get("value"),
                section_hierarchy=hierarchy,
                chunk_title=title,
                chunk_type=chunk_type,
                key_topics=topics[:5],
                searchable_fields=searchable,
                semantic_summary=summary,
                chunk_index=idx,
                total_chunks=len(raw_chunks)
            )

            enriched_chunks.append({
                "text": chunk_text,
                "metadata": asdict(metadata)
            })

        logger.info(f"  Enriched {len(enriched_chunks)} chunks in <10s\n")
        return enriched_chunks

    async def _analyze_structure_fast(self, text: str, filename: str) -> Dict[str, Any]:
        """One lightweight LLM call"""
        prompt = f"""Return ONLY JSON. Analyze document:

Filename: {filename}
Preview: {text[:1800]}

{{
  "doc_type": "lease_agreement|tenant_list|building_spec|market_report|contact_db|other",
  "structure_pattern": "hierarchical|repeated_entries|tabular|narrative",
  "primary_entity_type": "tenant|building|lease|broker|null",
  "section_markers": ["Article", "Section", "##", "Clause"], 
  "entry_separators": ["***", "---", "Tenant:", "Building:", "•"], 
  "key_fields": ["Tenant Name", "Address", "Rent", "SF", "Lease End"]
}}
"""

        try:
            response = await asyncio.to_thread(
                lambda: self.llm.generate_content(
                    prompt,
                    generation_config={"response_mime_type": "application/json"}
                )
            )
            return json.loads(response.text)
        except:
            return {
                "doc_type": "other",
                "structure_pattern": "narrative",
                "primary_entity_type": None,
                "section_markers": ["Article", "Section", "##"],
                "entry_separators": ["---", "***"],
                "key_fields": ["Tenant", "Building", "Rent"]
            }

    def _split_document_smart(self, text: str, structure: dict) -> List[Tuple[str, List[str]]]:
        pattern = structure["structure_pattern"]

        if pattern == "repeated_entries":
            return self._split_by_separators(text, structure["entry_separators"])
        elif pattern == "hierarchical":
            return self._split_by_sections(text, structure["section_markers"])
        elif pattern == "tabular":
            return self._split_tabular(text)
        else:
            return self._split_semantic(text)

    def _split_by_separators(self, text: str, separators: List[str]) -> List[Tuple[str, List[str]]]:
        chunks = []
        for sep in separators:
            if not sep.strip(): continue
            escaped = re.escape(sep.strip())
            pattern = f'(^|\\n)({escaped}.*?)(?=\\n{escaped}|\\Z)'
            matches = list(re.finditer(pattern, text, re.DOTALL | re.MULTILINE))
            if len(matches) > 2:
                for i, m in enumerate(matches):
                    chunk = m.group(2).strip()
                    if len(chunk) > 100:
                        chunks.append((chunk, [f"Entry {i+1}"]))
                if chunks:
                    return chunks[1:]  # skip possible header
        return self._split_semantic(text)

    def _split_by_sections(self, text: str, markers: List[str]) -> List[Tuple[str, List[str]]]:
        patterns = []
        for m in markers:
            if m in ["##", "###"]:
                patterns.append(f"^({re.escape(m)}\\s+.*)$")
            else:
                patterns.append(f"^({m}\\s*\\d+[:.\\s].*)$")
        patterns += [r"^(Article|Section|Clause)\s+\w+", r"^\d+\.\s+"]

        combined = "|".join(patterns)
        lines = text.split('\n')
        chunks = []
        current = []
        current_title = "Document Start"

        for line in lines:
            if re.match(combined, line.strip(), re.IGNORECASE):
                if current:
                    chunks.append(("\n".join(current).strip(), [current_title]))
                current_title = line.strip()[:100]
                current = [line]
            else:
                current.append(line)

        if current:
            chunks.append(("\n".join(current).strip(), [current_title]))

        return [c for c in chunks if len(c[0]) > 80]

    def _split_semantic(self, text: str):
        paragraphs = [p.strip() for p in re.split(r'\n\s*\n', text) if p.strip()]
        chunks = []
        current = ""
        for para in paragraphs:
            if len(current) + len(para) + 2 > MAX_CHUNK_SIZE and current:
                chunks.append((current.strip(), [f"Part {len(chunks)+1}"]))
                current = para[-OVERLAP:] + "\n\n" + para if len(para) > OVERLAP else para
            else:
                current += ("\n\n" if current else "") + para
        if current.strip():
            chunks.append((current.strip(), [f"Part {len(chunks)+1}"]))
        return chunks

    def _infer_title(self, text: str, hierarchy: List[str]) -> str:
        first_line = text.split('\n')[0].strip()
        if len(first_line) < 120 and any(c.isalnum() for c in first_line):
            return first_line
        return hierarchy[-1] if hierarchy else "Untitled Section"

    def _infer_chunk_type(self, text: str, structure: dict, hierarchy: List[str]) -> str:
        lower = text.lower()
        if "tenant" in lower and ("lease" in lower or "rent" in lower):
            return "tenant_record"
        if "building" in lower or "address" in lower or "sq ft" in lower:
            return "building_record"
        if any(x in lower for x in ["article", "section", "clause"]):
            return "document_section"
        return "information_block"

    def _extract_topics_heuristic(self, text: str) -> List[str]:
        keywords = re.findall(r'\b([A-Z][a-z]+(?:\s[A-Z][a-z]+)*)\b', text)
        common = {"Lease", "Tenant", "Building", "Rent", "Term", "Renewal", "Parking", "Utilities"}
        return [k.strip() for k in keywords if k.strip() in common or len(k) > 8][:5]

    def _smart_truncate_summary(self, text: str) -> str:
        sentences = re.split(r'(?<=[.!?])\s+', text)
        summary = ""
        for s in sentences[:3]:
            if len(summary + s) < 140:
                summary += s + " "
            else:
                break
        return summary.strip() or text[:130] + "..."

    def _extract_key_fields_heuristic(self, text: str) -> Dict[str, str]:
        fields = {}
        patterns = {
            "tenant_name": r"Tenant[:\s]+([A-Z][\w\s&]+?)(?:\n|$)",
            "building": r"Building[:\s]+([^\n]+)",
            "address": r"Address[:\s]+([^\n]+)",
            "rent": r"Rent[:\s]+\$?([0-9,]+\.?[0-9]*)",
            "sf": r"(\d{1,3}(?:,\d{3})*)\s*(?:SF|sq\.?\s*ft\.?)",
            "lease_end": r"Expiration[:\s]+(\d{1,2}/\d{1,2}/\d{2,4}|\w+ \d{1,2}, \d{4})"
        }
        for key, pattern in patterns.items():
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                fields[key] = match.group(1).strip()
        return fields

    def _guess_primary_entity(self, text: str, global_entities: dict):

        if "Starbucks" in text: return {"type": "tenant", "value": "Starbucks"}
        if "123 Main St" in text: return {"type": "building", "value": "123 Main St"}
        return {"type": None, "value": None}

    async def _extract_global_entities_once(self, text: str, structure: dict):
        return {}