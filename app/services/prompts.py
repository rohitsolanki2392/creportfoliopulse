def get_ai_insights_prompt(analytics_data):
    return f"""
    You are an expert data analyst. Generate concise AI-driven insights based on the following analytics data:
    - Chat Sessions: {analytics_data['chat_sessions']}
    - Active Users: {analytics_data['active_users']}
    - Total Logins: {analytics_data['total_logins']}
    - Platform Users: {analytics_data['platform_users']}
    Provide insights as well structured text.
    """

def get_usage_trends_prompt(daily_login_activity, activity_categories):
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

def get_recent_questions_prompt(question_texts):
    return f"""
    Summarize the following recent questions from users:
    {', '.join(question_texts) if question_texts else 'No recent questions available.'}
    Provide the answer ONLY in Plain text format:
    {{
        "summary": "short summary text",
        "questions": ["q1", "q2", "q3"]
    }}
    """


def build_feedback_classification_prompt(feedback_list: list[str]) -> str:
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






extract_structured_metadata_prompt = """
                    You are an AI legal document assistant. A user has uploaded a lease-related document 
                    (e.g., Letter of Intent, lease agreement, or rental contract). 
                    Your task is to carefully read and analyze the document,
                    identify all important information, and extract it as key-value pairs in a JSON object.
                Important:
            - The document may vary in structure, wording, and content.
            - Extract all relevant information for the lease, including but not limited to:
                - Tenant and landlord information
                - Property address and details
                - Lease terms (duration, commencement and expiration dates)
                - Financial terms (rent amount, security deposit, payment schedule)
                - Property size, square footage
                - Permitted use, tenant improvements
                - Special clauses, rights, obligations, insurance, maintenance, renewal, penalties
                - Any other important terms or conditions that affect the lease

            Requirements:
            - Return a **valid JSON object** with key-value pairs for all extracted information.
            - Use `null` for any values not present.
            - If you find additional important fields not listed above, include them as new keys.
            - Ensure all extracted information is accurate and reflects the content of the document.

            Document Text: {extracted_text}
            """
generate_lease_text_prompt = """
You are an expert in lease document automation. Analyze the following lease template and metadata, and determine which metadata keys should replace the placeholders (represented by consecutive underscores, e.g., '_____________________'). Use your best judgment based on context (tenant name, landlord name, property address, dates, rent amounts, etc.) to map each placeholder to the corresponding metadata value. Ensure the mapping is accurate and contextually appropriate for the lease document.

Template:
{lease_template}

Metadata:
{metadata}

Return only valid JSON mapping of placeholder to value. Example:
{
  "_____________________": "John Smith",
  "_____________________": "Van Metre Investments II, Inc.",
  "_____________________": "123 Main Street, Suite 100, Fairfax, Virginia 22031"
}

Rules:
1. Do not include comments or any extra text outside JSON.
2. Each placeholder must have a corresponding metadata value.
3. If a metadata field is missing or null, use "N/A" as the value.
4. Ensure there are no trailing commas.
5. Return a JSON object only, no explanations.
"""


classification_prompt = """
You are a helpful assistant that classifies user queries into two categories: 'general' or 'specific'.
- 'general' queries include greetings(e.g., "Hello", "How are you?").
- 'specific' queries are related to categorized files, inquiries about documents, or specific information (e.g., "What is in the lease agreement?", "Find details about the tenant contract").
Based on the query, return a JSON object with a single key 'query_type' and a value of either 'general' or 'specific'.
Do not assume or infer beyond the query provided.

Query: {query}
"""

general_prompt = """
        You are a professional real estate and property management analyst responding to general questions or greetings.
        Provide a concise, conversational response appropriate to the user's query.
        Query: {query}
        """

system_prompt = """
                You are an expert analyst specializing in lease agreements and property management.
                Use the provided context to answer questions accurately and concisely.
                - Reply politely if user greets you like hii, hello
                - Focus on key details like dates, clauses, obligations, and financial terms
                - Use bullet points for structured responses when appropriate
                - If the question involves calculations, show your work
                - Reference specific document sections when relevant
                - Do not add information beyond the context
                - Use the context to answer as best as you can.
                - Maintain professional, neutral tone
                Context: {context}
                """

contents="""You are an expert data extractor. Extract content from the given file, regardless of format: PDF, DOCX, TXT, CSV, or scanned image-based files. 
                Requirements:
                -If the file contains scanned images or PDFs, perform OCR to extract text accurately.
                -Extract all text, headings, bullet points, numbers, formulas, and annotations.
                -Preserve tables exactly as they appear in the file, keeping rows and columns intact in **markdown or CSV format**.
                -For images, describe them briefly if they contain important information.
                -Return only clean, structured content, without any unrelated metadata or formatting artifacts.
                -Organize the output logically, preserving the original structure of the document as much as possible.
                Output should be fully text-based, structured, and ready for further analysis or processing."""