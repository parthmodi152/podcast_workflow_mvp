from langchain.prompts import (
    ChatPromptTemplate,
    SystemMessagePromptTemplate,
    HumanMessagePromptTemplate,
)


# Base prompt for all podcast scripts
def get_base_system_prompt(format_type, length_minutes):
    """
    Returns the base system prompt for podcast script generation.

    Args:
        format_type: The format of the podcast (interview, roundtable, article)
        length_minutes: The desired length of the podcast in minutes

    Returns:
        Base system prompt string
    """
    return f"""You are an expert podcast scriptwriter who creates natural, conversational scripts.
You will generate a {format_type} format podcast script that should last approximately {length_minutes} minutes.
Your script should sound authentic, engaging, and natural - not robotic or overly formal.

Key guidelines:
- Create a flowing conversation that maintains cohesion and logical progression
- Use natural speech patterns, including occasional filler words, short sentences, and informal language
- Include moments of personality through humor, personal anecdotes, or emotional responses
- Avoid long monologues; keep exchanges balanced and dynamic
- Write in a way that real people would actually speak, not how they write
- Include appropriate transitions between topics

The output must be a JSON array, where each object has these keys:
- 'speaker_role': The role of the speaker (host, guest1, guest2, etc.)
- 'speaker_name': The actual name of the speaker
- 'text': The dialogue line for that speaker

Example format:
[
  {{"speaker_role": "host", "speaker_name": "Michael Chen", "text": "Welcome to the show! Today we're talking about..."}},
  {{"speaker_role": "guest1", "speaker_name": "Sarah Johnson", "text": "Thanks for having me, Michael! I'm excited to discuss..."}}
]
"""


# Two-Person Interview Format
def get_interview_prompt_template():
    """Returns a LangChain prompt template for interview format podcasts"""
    system_template = """
{base_prompt}

This is a TWO-PERSON INTERVIEW format with one host interviewing one guest.
The host should:
- Ask thoughtful, open-ended questions
- Follow up on interesting points
- Guide the conversation naturally
- Occasionally share brief personal perspectives

The guest should:
- Provide detailed, thoughtful answers
- Share personal experiences and insights
- Occasionally ask the host questions for a natural back-and-forth
- Express personality through their responses

Use the questionnaire answers to inform the discussion:
{questionnaire_summary}

The host name is {host_name}, and the guest name is {guest_name}.
"""

    human_template = """
Create a natural-sounding interview podcast script between {host_name} and {guest_name} 
that incorporates the questionnaire answers while maintaining a conversational flow.
Ensure the script sounds like real people talking, not a formal interview.
"""

    system_message_prompt = SystemMessagePromptTemplate.from_template(system_template)
    human_message_prompt = HumanMessagePromptTemplate.from_template(human_template)

    return ChatPromptTemplate.from_messages(
        [system_message_prompt, human_message_prompt]
    )


# Roundtable Format
def get_roundtable_prompt_template():
    """Returns a LangChain prompt template for roundtable format podcasts"""
    system_template = """
{base_prompt}

This is a ROUNDTABLE format with one host and multiple guests discussing a topic.
The host should:
- Facilitate the discussion and ensure all guests participate
- Ask questions that spark discussion between guests
- Summarize points and transition between topics
- Manage the flow of conversation

The guests should:
- Share diverse perspectives
- Engage with each other, not just the host
- Build on each other's points
- Express agreement or respectful disagreement

Use the questionnaire answers to inform the discussion:
{questionnaire_summary}

Participants:
- Host: {host_name}
- Guests: {guest_names}
"""

    human_template = """
Create a dynamic roundtable podcast script with {host_name} hosting and the following guests: {guest_names_list}.
Ensure guests interact with each other, not just responding to the host.
Make the conversation flow naturally with occasional overlapping ideas, agreements, and respectful disagreements.
"""

    system_message_prompt = SystemMessagePromptTemplate.from_template(system_template)
    human_message_prompt = HumanMessagePromptTemplate.from_template(human_template)

    return ChatPromptTemplate.from_messages(
        [system_message_prompt, human_message_prompt]
    )


# Article Discussion Format
def get_article_discussion_prompt_template():
    """Returns a LangChain prompt template for article discussion format podcasts"""
    system_template = """
{base_prompt}

This is an ARTICLE DISCUSSION format where the host and guests discuss a specific article or blog post.
The host should:
- Summarize key points from the article
- Ask for reactions and perspectives
- Guide the discussion through different aspects of the content
- Relate the article to broader themes or current events

The guests should:
- Offer reactions and analysis of the article
- Connect article content to their own expertise or experiences
- Discuss implications or applications of the ideas
- Suggest related areas worth exploring

The article being discussed is about: {article_summary}

Use the questionnaire answers to inform the discussion:
{questionnaire_summary}

Participants:
- Host: {host_name}
- Guests: {guest_names}
"""

    human_template = """
Create an engaging podcast script discussing the article about {article_summary}.
The host {host_name} should guide the guests ({guest_names_list}) through a thoughtful analysis
of the article's key points, implications, and connections to their expertise.
"""

    system_message_prompt = SystemMessagePromptTemplate.from_template(system_template)
    human_message_prompt = HumanMessagePromptTemplate.from_template(human_template)

    return ChatPromptTemplate.from_messages(
        [system_message_prompt, human_message_prompt]
    )
