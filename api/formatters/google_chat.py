import re
import json
import pandas as pd

def format_text_to_google_chat(text):
    """
    Convert a text response to a Google Chat formatted message.
    
    Args:
        text (str): The text to format
        
    Returns:
        dict: A Google Chat formatted message with text and formattedText
    """
    # Keep original text
    original_text = text
    
    # Format the text according to Google Chat markdown rules
    formatted_text = format_inline_markdown(text)
    
    # Return the simple JSON format
    return {
        "text": original_text,
        "formattedText": formatted_text
    }

def format_inline_markdown(text):
    """
    Format inline markdown elements to Google Chat's supported formatting
    
    Args:
        text (str): The text with markdown formatting
        
    Returns:
        str: Text with Google Chat formatting
    """
    # Convert markdown headings (# Heading) to bold + italic
    lines = text.split('\n')
    for i, line in enumerate(lines):
        heading_match = re.match(r'^(#{1,6})\s+(.+)$', line)
        if heading_match:
            # Extract the heading level and content
            heading_content = heading_match.group(2).strip()
            # Convert heading to bold + italic (Google Chat: *_text_*)
            lines[i] = f"*_{heading_content}_*"
    
    # Rejoin lines after heading processing
    text = '\n'.join(lines)
    
    # Replace bold (**text** or *text*) with *text* (Google Chat bold)
    formatted = re.sub(r'\*\*([^*]+)\*\*|\*([^*]+)\*', r'*\1\2*', text)
    
    # Replace italics (_text_) with _text_ (Google Chat italic)
    formatted = re.sub(r'_([^_]+)_', r'_\1_', formatted)
    
    # Replace strikethrough (~~text~~) with ~text~ (Google Chat strikethrough)
    formatted = re.sub(r'~~([^~]+)~~', r'~\1~', formatted)
    
    # Replace inline code (`text`) with `text` (Google Chat monospace)
    formatted = re.sub(r'`([^`]+)`', r'`\1`', formatted)
    
    # Format bullet points to use asterisks for Google Chat
    lines = formatted.split('\n')
    for i, line in enumerate(lines):
        if line.strip().startswith(('- ', '* ')):
            lines[i] = '* ' + line[2:].strip()
    
    # Rejoin the lines
    formatted = '\n'.join(lines)
    
    return formatted

def format_json_to_google_chat(json_data):
    """
    Format JSON data as a Google Chat message
    
    Args:
        json_data (list/dict): The JSON data to format
        
    Returns:
        dict: A Google Chat formatted message with text and formattedText
    """
    # Create plain text representation
    text = json.dumps(json_data, indent=2)
    
    # Format as monospace block (triple backticks) for Google Chat
    formatted_text = f"```\n{text}\n```"
    
    return {
        "text": text,
        "formattedText": formatted_text
    }

def dataframe_to_google_chat(df):
    """
    Format a pandas DataFrame as a Google Chat message
    
    Args:
        df (pandas.DataFrame): The DataFrame to format
        
    Returns:
        dict: A Google Chat formatted message with text and formattedText
    """
    # Create plain text representation
    text_lines = []
    for _, row in df.iterrows():
        text_lines.append("- " + ", ".join([f"{col}: {row[col]}" for col in df.columns]))
    
    text = "\n".join(text_lines)
    
    # Create formatted text with bullet points
    formatted_lines = []
    for _, row in df.iterrows():
        formatted_lines.append("* " + ", ".join([f"{col}: {row[col]}" for col in df.columns]))
    
    formatted_text = "\n".join(formatted_lines)
    
    return {
        "text": text,
        "formattedText": formatted_text
    } 