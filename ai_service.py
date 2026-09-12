
import os

from dotenv import load_dotenv
from google import genai


# ---------------------------------------------------------
# Load environment variables
# ---------------------------------------------------------

load_dotenv()


# ---------------------------------------------------------
# Read Gemini API key
# ---------------------------------------------------------

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")


# ---------------------------------------------------------
# Create Gemini client only when a key exists
# ---------------------------------------------------------

client = None

if GEMINI_API_KEY:

    try:

        client = genai.Client(
            api_key=GEMINI_API_KEY
        )

        print("Gemini AI client initialized.")

    except Exception as error:

        print(
            "Gemini AI initialization failed:",
            error
        )

        client = None

else:

    print(
        "Gemini API key not configured. "
        "AI features will remain disabled."
    )


# ---------------------------------------------------------
# Individual incorrect-answer analysis
# ---------------------------------------------------------

def generate_insight(
    question,
    selected_answer,
    correct_answer
):

    # AI is optional.
    # If Gemini is unavailable, PKT continues normally.
    if client is None:

        return {
            "insight":
                "AI analysis is currently unavailable. "
                "The test result has been saved successfully."
        }


    prompt = f"""
You are an assessment analyst.

Analyze the following incorrect test answer.

Question:
{question}

Candidate selected:
{selected_answer}

Correct answer:
{correct_answer}

Provide:

1. A short explanation of why the selected answer is incorrect.
2. A simple explanation of the correct answer.
3. A practical suggestion to help the candidate avoid
   this mistake in the future.

Keep the explanation clear and concise.
"""


    try:

        response = client.models.generate_content(

            # Use the currently configured Gemini model.
            model="gemini-3.6-flash",

            contents=prompt
        )

        return {
            "insight": response.text
        }


    except Exception as error:

        print(
            "Gemini AI error:",
            error
        )

        return {
            "insight":
                "AI analysis is currently unavailable. "
                "The test result has been saved successfully."
        }


# ---------------------------------------------------------
# Overall Dashboard AI Insights
# ---------------------------------------------------------

def generate_overall_insight(
    assessment_data
):

    # AI is optional.
    if client is None:

        return {
            "insight":
                "Overall AI insights are currently "
                "unavailable because Gemini is not connected."
        }


    prompt = f"""
You are an assessment analyst.

Analyze the following completed assessment data.

Assessment data:
{assessment_data}

Provide an overall assessment containing:

1. Overall performance summary.
2. Performance strengths.
3. Common mistakes or weak areas.
4. Important patterns visible in the results.
5. Practical recommendations for improvement.

Keep the analysis clear, professional and concise.

Use only the information provided.
Do not invent facts or results.
"""


    try:

        response = client.models.generate_content(

            model="gemini-3.6-flash",

            contents=prompt
        )

        return {
            "insight": response.text
        }


    except Exception as error:

        print(
            "Gemini overall insight error:",
            error
        )

        return {
            "insight":
                "Overall AI insights are currently "
                "unavailable. The assessment results "
                "remain available."
        }
