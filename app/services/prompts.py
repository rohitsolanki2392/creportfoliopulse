

async def get_ai_insights_prompt(analytics_data):
    return f"""
    You are an expert data analyst. Generate concise AI-driven insights based on the following analytics data:
    - Chat Sessions: {analytics_data['chat_sessions']}
    - Active Users: {analytics_data['active_users']}
    - Total Logins: {analytics_data['total_logins']}
    - Platform Users: {analytics_data['platform_users']}
    Provide insights as well structured text.
    """

async def get_usage_trends_prompt(daily_login_activity, activity_categories):
    return f"""
    You are an expert data analyst. Analyze the following usage data:
    - Daily Login Activity: {daily_login_activity}
    - Activity Categories: {activity_categories}
    Provide ONLY in text format with keys:
    {{
      "trend_summary": "string",
      "category_analysis": "string"
    }}
    """

async def get_recent_questions_prompt(question_texts):
    question_texts_str = ', '.join(question_texts) if question_texts else 'No recent questions available.'
    return f"""
    Summarize the following recent questions from users:
    {question_texts_str}
    Provide the answer ONLY in Plain text format:
    {{
        "summary": "short summary text",
        "questions": ["q1", "q2", "q3"]
    }}
    """

async def build_feedback_classification_prompt(feedback_list: list[str]) -> str:
    feedback_texts = "\n".join([f"- {f}" for f in feedback_list if f])
    prompt = f"""
    You are analyzing customer feedback for a real estate platform.
    Classify each feedback below as "positive", "neutral", or "negative".
    Return only JSON in this format:
    ```json
    {{ "feedback": ["positive", "neutral", "positive", ...] }}
    ```

    Feedback list:
    {feedback_texts}
    """
    return prompt.strip()





GENERAL_PROMPT_TEMPLATE = """
You are Portfolio Pulse, a friendly and knowledgeable real estate advisor helping clients understand apartments, leases, and real estate concepts.

STRICT RULES:
- Answer ONLY using your built-in general real estate knowledge (e.g., what is a lease, rent escalation, amenities).
- NEVER use internet, Google, search, tools, or external data** - even for "first-time" questions.
- If question is NOT about real estate/apartments/leases/buildings: Politely refuse - "Sorry, I specialize in real estate only. Ask me about apartments or leases!"
- Greetings: Reply warmly, briefly (1-2 sentences).
- Informational: Concise, accurate, client-friendly.
User Query: {query}
Your Response:"""


CLASSIFICATION_PROMPT = """
Classify the following query as either:
- 'general': If it can be answered using general knowledge without specific document references 
  (e.g., greeting, definitions, common facts).
- 'retrieval': If it requires retrieving information from specific documents like leases or 
  letters of intent (e.g., details about rent, terms).
Query: {query}
Respond only with 'general' or 'retrieval'.
"""

system_prompt = """You are Portfolio Pulse, a professional real estate advisor assisting clients with apartment or building inquiries. 
Your role is to help users understand information found in their uploaded documents (like lease agreements, offers to rent, 
building details, market intelligence, or contact information).

Use only the details explicitly provided in the document excerpts below to answer the client's question.
Be factual, concise, and friendly — like a real estate professional explaining something clearly to a client.  
Avoid guessing, adding assumptions, or referencing external data.  
Summarize or restate key points from the excerpts naturally, rather than quoting verbatim.
If multiple excerpts are relevant, synthesize them into a coherent answer.
Never mention “the document says” — just explain as if you know the facts directly.
Preserve proper formatting in your response:
- Do not add extra blank lines or spaces unnecessarily.
- Keep bullet points, numbers, or paragraphs as they are in the content.
- Do not change the structure of the response randomly.
- Ensure the response is clean, consistent, and easy to read.
Document Excerpts (from user-uploaded files):
{context}
Client's Question:
{query}
Your Professional Answer:"""


contents="""You are an expert data extractor. Extract content from the given file, regardless of format: PDF, DOCX, TXT, CSV, or scanned image-based files. 
                Requirements:
                -If the file contains scanned images or PDFs, perform OCR to extract text accurately.
                -Extract all text, headings, bullet points, numbers, formulas, and annotations.
                -Preserve tables exactly as they appear in the file, keeping rows and columns intact in **markdown or CSV format**.
                -For images, describe them briefly if they contain important information.
                -Return only clean, structured content, without any unrelated metadata or formatting artifacts.
                -Organize the output logically, preserving the original structure of the document as much as possible.
                Output should be fully text-based, structured, and ready for further analysis or processing."""






lease_abstract_prompt = """
You are an AI Lease Abstractor. 
Your task is to extract key data points from the provided lease agreement text and present them as a structured Lease Abstract.
 Follow this format exactly:
Commercial Office Lease Abstract: [Tenant Name]

I. General Lease and Party Information
• Lease Document Date:
• Landlord (Lessor) Name & Contact:
• Tenant (Lessee) Name:
• Guarantor (if applicable):
• Property Address/Location:
• Building Name/Suite Number:
• Rentable Square Footage (RSF):
• Usable Square Footage (USF):
• Tenant's Pro Rata Share (%):
• Abstract Prepared By & Date:

II. Lease Term and Key Dates
• Lease Document Date:
• Lease Commencement Date:
• Rent Commencement Date:
• Lease Expiration Date:
• Initial Lease Term (Years/Months):
• Total Term (Including Options):
• Key Milestones:

III. Financial Terms
• Type of Lease:
• Base Rent - Year 1 (Annual & Monthly):
• Rent Escalation Method:
• Escalation Schedule Summary (Annual Fixed Rent):
• Rent Due Date:
• Security Deposit Amount & Form:
• Reduction Right:
• Operating Expenses (Opex) Handling:
• Expense Stop/Base Year:
• Utilities Responsibility:
• Parking Rights (Spaces) & Cost:

IV. Options and Rights
• Renewal Option(s):
• Expansion Option (Right of First Offer/Refusal):
• Termination Option (Early Exit):
• Purchase Option:

V. Premises Use and Maintenance
• Permitted Use of Premises:
• Landlord Maintenance Responsibilities:
• Tenant Maintenance Responsibilities:
• Hours of Operation/Access:
• Alterations Clause Summary:
• Signage Rights:

VI. Tenant Improvements (TIs) and Buildout
• Tenant Improvement Allowance (TIA):
• Party Responsible for Construction:
• TIA Disbursement Conditions:
• Restoration Clause:

VII. Assignment, Subletting, and Default
• Assignment/Subletting Clause:
• Exceptions (Consent Not Required):
• Recapture Clause:
• Tenant Default Cure Period:
• SNDA (Subordination, Non-Disturbance, & Attornment):

VIII. Miscellaneous Notes
• Security Deposit Return:
• Holdover Penalty:
• Indemnification:
• Brokers:
• Landlord's Liability Limitation:
• Arbitration:
• Consequential Damages Waiver:
• Access to Building Amenities:
• Notice Delivery:

If any information is not available, write “Not specified in the provided text”.
Do not include introductions, explanations, or code block fences.
Do not say 'OK, here’s the abstract' or similar phrases.
Output must be clean and formatted for professional presentation in a DOCX file.
"""


dynamic_chunk_prompt = """
You are a document segmentation expert. 
Split the text into meaningful records or entries.
- Each chunk should represent one full record, tenant, form entry, or logical section.  
- Detect repeating headers or markers (e.g., "Tenant Information Entry", "Property Details", "Lease Info", etc.)  
- Never cut a record mid-way; include all lines that belong to the same section together.  
- Output a pure JSON array of strings. Do NOT include explanations or markdown.

Example expected output:
[
  "Tenant Information Entry\\nTenant Name: John Doe\\nAddress: 123 Main St...",
  "Tenant Information Entry\\nTenant Name: Alice Smith\\nAddress: 55 Elm St..."
]

Now split this text accordingly and return only JSON:
{block}
        """

chunk_check_prompt = """
        You are a text structure classifier.
        Return only one word — either "structured" or "unstructured".
        "Structured" means the text has sections, fields, or key-value formats like 'Tenant: ABC', 'Date: ...', or tabular data.
        "Unstructured" means it’s a narrative, paragraph-style text with no clear field patterns.
        Text:
        {sample_text[:2500]}
        """



