import os

from anthropic import AsyncAnthropic

client = AsyncAnthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

EXTRACTION_TOOL = {
    "name": "record_metadata",
    "description": "Record structured metadata extracted from a captured thought.",
    "input_schema": {
        "type": "object",
        "properties": {
            "type": {
                "type": "string",
                "enum": ["decision", "person_note", "insight", "meeting_debrief", "task", "other"],
            },
            "people": {"type": "array", "items": {"type": "string"}},
            "topics": {"type": "array", "items": {"type": "string"}},
            "action_items": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["type", "people", "topics", "action_items"],
    },
}


async def extract_metadata(text: str) -> dict:
    response = await client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=512,
        tools=[EXTRACTION_TOOL],
        tool_choice={"type": "tool", "name": "record_metadata"},
        messages=[
            {
                "role": "user",
                "content": f"Extract structured metadata from this captured thought:\n\n{text}",
            }
        ],
    )
    for block in response.content:
        if block.type == "tool_use":
            return block.input
    return {"type": "other", "people": [], "topics": [], "action_items": []}
