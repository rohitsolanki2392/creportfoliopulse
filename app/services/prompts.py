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