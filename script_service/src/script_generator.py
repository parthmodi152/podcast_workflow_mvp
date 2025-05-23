import os
import json
import httpx
import logging
from typing import List, Dict, Any
from langchain.chains import LLMChain
from langchain_openai import ChatOpenAI
from langchain.output_parsers import ResponseSchema, StructuredOutputParser

from .langchain_prompts import (
    get_base_system_prompt,
    get_interview_prompt_template,
    get_roundtable_prompt_template,
    get_article_discussion_prompt_template,
)

# Configure logging
logger = logging.getLogger(__name__)

# Get the OpenAI API key from environment variables
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")


# Initialize the LLM
def get_llm():
    """Returns a LangChain LLM instance."""
    return ChatOpenAI(model="gpt-4o", temperature=0.7, api_key=OPENAI_API_KEY)


def format_questionnaire_summary(questionnaire_answers):
    """Extract the direct text content from questionnaire answers."""
    # Since the frontend now sends survey responses as direct text,
    # just extract and return the content without formatting
    if questionnaire_answers and len(questionnaire_answers) > 0:
        return questionnaire_answers[0]["answer"]
    return "No survey responses provided."


def extract_article_summary(article_url):
    """
    Extract and summarize the content of an article from its URL.
    For now, we're just returning the URL as a placeholder.
    In a production environment, you would integrate with a web scraping
    or article extraction service.
    """
    # Placeholder - in a real implementation, you'd extract and summarize the article
    return f"Article at {article_url}"


async def generate_interview_script(
    title: str,
    host_info: Dict[str, str],
    guest_info: Dict[str, str],
    questionnaire_answers: List[Dict[str, str]],
    length_minutes: int,
) -> List[Dict[str, str]]:
    """Generate a script for a two-person interview podcast format."""
    # Format the questionnaire answers
    questionnaire_summary = format_questionnaire_summary(questionnaire_answers)

    logger.info(f"Generating interview script: {title}")
    logger.info(f"Host: {host_info['name']}, Guest: {guest_info['name']}")
    logger.info(f"Length: {length_minutes} minutes")
    logger.info(f"Survey responses content: {questionnaire_summary[:200]}...")

    # Get the prompt template for interviews
    prompt_template = get_interview_prompt_template()

    # Set up the LLM chain
    llm = get_llm()
    chain = LLMChain(llm=llm, prompt=prompt_template)

    # Prepare inputs for logging
    inputs = {
        "base_prompt": get_base_system_prompt("interview", length_minutes),
        "questionnaire_summary": questionnaire_summary,
        "host_name": host_info["name"],
        "guest_name": guest_info["name"],
    }

    logger.info("OpenAI Request Inputs:")
    logger.info(f"Base prompt: {inputs['base_prompt'][:300]}...")
    logger.info(f"Questionnaire summary: {inputs['questionnaire_summary'][:300]}...")
    logger.info(f"Host name: {inputs['host_name']}")
    logger.info(f"Guest name: {inputs['guest_name']}")

    # Run the chain with our inputs
    response = await chain.arun(**inputs)

    logger.info(f"OpenAI Response (first 500 chars): {response[:500]}...")

    # Parse the JSON response
    try:
        # The response might be a string representation of a JSON array
        # or it might include some explanatory text before/after the JSON
        script_lines = json.loads(response)

        # Validate the structure
        for line in script_lines:
            if not all(key in line for key in ["speaker_role", "speaker_name", "text"]):
                raise ValueError(f"Invalid line structure: {line}")

        return script_lines
    except json.JSONDecodeError:
        # Try to find and extract the JSON array if it's embedded in text
        import re

        json_match = re.search(r"\[\s*{.*}\s*\]", response, re.DOTALL)
        if json_match:
            try:
                script_lines = json.loads(json_match.group(0))
                return script_lines
            except json.JSONDecodeError:
                raise ValueError(f"Could not parse JSON from response: {response}")
        else:
            raise ValueError(f"Could not find JSON array in response: {response}")


async def generate_roundtable_script(
    title: str,
    host_info: Dict[str, str],
    guest_infos: List[Dict[str, str]],
    questionnaire_answers: List[Dict[str, str]],
    length_minutes: int,
) -> List[Dict[str, str]]:
    """Generate a script for a roundtable podcast format with multiple guests."""
    # Format the questionnaire answers
    questionnaire_summary = format_questionnaire_summary(questionnaire_answers)

    # Format the guest names for the prompt
    guest_names = [guest["name"] for guest in guest_infos]
    guest_names_str = ", ".join(guest_names)

    logger.info(f"Generating roundtable script: {title}")
    logger.info(f"Host: {host_info['name']}, Guests: {guest_names_str}")
    logger.info(f"Length: {length_minutes} minutes")
    logger.info(f"Survey responses content: {questionnaire_summary[:200]}...")

    # Get the prompt template for roundtable discussions
    prompt_template = get_roundtable_prompt_template()

    # Set up the LLM chain
    llm = get_llm()
    chain = LLMChain(llm=llm, prompt=prompt_template)

    # Prepare inputs for logging
    inputs = {
        "base_prompt": get_base_system_prompt("roundtable", length_minutes),
        "questionnaire_summary": questionnaire_summary,
        "host_name": host_info["name"],
        "guest_names": guest_names_str,
        "guest_names_list": guest_names_str,
    }

    logger.info("OpenAI Request Inputs (Roundtable):")
    logger.info(f"Base prompt: {inputs['base_prompt'][:300]}...")
    logger.info(f"Questionnaire summary: {inputs['questionnaire_summary'][:300]}...")
    logger.info(f"Host name: {inputs['host_name']}")
    logger.info(f"Guest names: {inputs['guest_names']}")

    # Run the chain with our inputs
    response = await chain.arun(**inputs)

    logger.info(f"OpenAI Response (first 500 chars): {response[:500]}...")

    # Parse the JSON response (same as in the interview function)
    try:
        script_lines = json.loads(response)

        # Validate the structure
        for line in script_lines:
            if not all(key in line for key in ["speaker_role", "speaker_name", "text"]):
                raise ValueError(f"Invalid line structure: {line}")

        return script_lines
    except json.JSONDecodeError:
        # Try to find and extract the JSON array if it's embedded in text
        import re

        json_match = re.search(r"\[\s*{.*}\s*\]", response, re.DOTALL)
        if json_match:
            try:
                script_lines = json.loads(json_match.group(0))
                return script_lines
            except json.JSONDecodeError:
                raise ValueError(f"Could not parse JSON from response: {response}")
        else:
            raise ValueError(f"Could not find JSON array in response: {response}")


async def generate_article_discussion_script(
    title: str,
    host_info: Dict[str, str],
    guest_infos: List[Dict[str, str]],
    questionnaire_answers: List[Dict[str, str]],
    article_url: str,
    length_minutes: int,
) -> List[Dict[str, str]]:
    """Generate a script for a podcast discussing an article or blog post."""
    # Format the questionnaire answers
    questionnaire_summary = format_questionnaire_summary(questionnaire_answers)

    # Get article summary
    article_summary = extract_article_summary(article_url)

    # Format the guest names for the prompt
    guest_names = [guest["name"] for guest in guest_infos]
    guest_names_str = ", ".join(guest_names)

    logger.info(f"Generating article discussion script: {title}")
    logger.info(f"Host: {host_info['name']}, Guests: {guest_names_str}")
    logger.info(f"Article URL: {article_url}")
    logger.info(f"Length: {length_minutes} minutes")
    logger.info(f"Survey responses content: {questionnaire_summary[:200]}...")

    # Get the prompt template for article discussions
    prompt_template = get_article_discussion_prompt_template()

    # Set up the LLM chain
    llm = get_llm()
    chain = LLMChain(llm=llm, prompt=prompt_template)

    # Prepare inputs for logging
    inputs = {
        "base_prompt": get_base_system_prompt("article discussion", length_minutes),
        "questionnaire_summary": questionnaire_summary,
        "article_summary": article_summary,
        "host_name": host_info["name"],
        "guest_names": guest_names_str,
        "guest_names_list": guest_names_str,
    }

    logger.info("OpenAI Request Inputs (Article Discussion):")
    logger.info(f"Base prompt: {inputs['base_prompt'][:300]}...")
    logger.info(f"Questionnaire summary: {inputs['questionnaire_summary'][:300]}...")
    logger.info(f"Article summary: {inputs['article_summary'][:200]}...")
    logger.info(f"Host name: {inputs['host_name']}")
    logger.info(f"Guest names: {inputs['guest_names']}")

    # Run the chain with our inputs
    response = await chain.arun(**inputs)

    logger.info(f"OpenAI Response (first 500 chars): {response[:500]}...")

    # Parse the JSON response (same as in the other functions)
    try:
        script_lines = json.loads(response)

        # Validate the structure
        for line in script_lines:
            if not all(key in line for key in ["speaker_role", "speaker_name", "text"]):
                raise ValueError(f"Invalid line structure: {line}")

        return script_lines
    except json.JSONDecodeError:
        # Try to find and extract the JSON array if it's embedded in text
        import re

        json_match = re.search(r"\[\s*{.*}\s*\]", response, re.DOTALL)
        if json_match:
            try:
                script_lines = json.loads(json_match.group(0))
                return script_lines
            except json.JSONDecodeError:
                raise ValueError(f"Could not parse JSON from response: {response}")
        else:
            raise ValueError(f"Could not find JSON array in response: {response}")


async def generate_script(
    format_type: str,
    title: str,
    speakers: List[Dict[str, str]],
    questionnaire_answers: List[Dict[str, str]],
    length_minutes: int,
    article_url: str = None,
) -> List[Dict[str, str]]:
    """
    Generate a podcast script based on the format type and provided information.

    Args:
        format_type: Type of podcast format (interview, roundtable, article)
        title: Title of the podcast
        speakers: List of speaker information dictionaries
        questionnaire_answers: List of question-answer dictionaries
        length_minutes: Desired length of the podcast in minutes
        article_url: URL of the article for article discussion format

    Returns:
        List of dictionaries representing script lines
    """
    # Extract host and guest information
    host_info = next((s for s in speakers if s["role"] == "host"), None)
    guest_infos = [s for s in speakers if s["role"] != "host"]

    if not host_info:
        raise ValueError("No host specified in speakers list")

    if format_type == "interview":
        if len(guest_infos) != 1:
            raise ValueError("Interview format requires exactly one guest")
        return await generate_interview_script(
            title, host_info, guest_infos[0], questionnaire_answers, length_minutes
        )
    elif format_type == "roundtable":
        if not guest_infos:
            raise ValueError("Roundtable format requires at least one guest")
        return await generate_roundtable_script(
            title, host_info, guest_infos, questionnaire_answers, length_minutes
        )
    elif format_type == "article":
        if not article_url:
            raise ValueError("Article URL is required for article discussion format")
        return await generate_article_discussion_script(
            title,
            host_info,
            guest_infos,
            questionnaire_answers,
            article_url,
            length_minutes,
        )
    else:
        raise ValueError(f"Unsupported format type: {format_type}")
