
# Import our AI service function.
from ai_service import generate_insight


# Send a sample incorrect answer to Gemini.
result = generate_insight(
    question="What is the capital of France?",
    selected_answer="London",
    correct_answer="Paris"
)


# Display the AI-generated insight.
print(result["insight"])

