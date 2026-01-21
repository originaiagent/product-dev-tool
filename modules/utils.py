"""
Utility functions for the application.
Includes robust JSON parsing for AI responses.
"""
import json
import ast
import re
import logging

# Configure logger
logger = logging.getLogger(__name__)

def parse_json_response(response_text: str):
    """
    Parses JSON from AI response text with multiple fallback strategies.
    
    Args:
        response_text: The raw text response from the AI.
        
    Returns:
        parsed_json: The parsed Python object (dict or list).
        
    Raises:
        ValueError: If parsing fails after all attempts.
    """
    if not response_text:
        raise ValueError("Empty response text")
        
    # Strategy 1: Attempt to extract from code blocks
    # Try ```json ... ``` or just ``` ... ```
    json_str = response_text
    match = re.search(r'```(?:json)?\s*(\{[\s\S]*\}|\[[\s\S]*\])\s*```', response_text)
    if match:
        json_str = match.group(1)
    else:
        # Strategy 2: Find the outermost {} or [] pair if no code blocks found
        # This handles cases where the AI replies with just the JSON or adds text around it without code blocks
        
        # Check for object or list
        start_brace = response_text.find('{')
        start_bracket = response_text.find('[')
        
        start = -1
        end = -1
        is_object = False
        
        # Determine if we are looking for an object or a list based on which comes first
        if start_brace != -1 and (start_bracket == -1 or start_brace < start_bracket):
            start = start_brace
            end = response_text.rfind('}')
            is_object = True
        elif start_bracket != -1:
            start = start_bracket
            end = response_text.rfind(']')
            is_object = False
            
        if start != -1 and end != -1 and end > start:
            json_str = response_text[start:end+1]
    
    # Clean up the string (remove potential newlines or spaces at start/end)
    json_str = json_str.strip()
    
    # Strategy 3: Standard JSON parsing
    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        pass
        
    # Strategy 4: Python literal evaluation (for single quotes, etc.)
    try:
        return ast.literal_eval(json_str)
    except (ValueError, SyntaxError):
        pass
        
    # If all fails, raise error with debug info
    raise ValueError(f"Failed to parse JSON from response. Extracted string start: {json_str[:50]}...")
