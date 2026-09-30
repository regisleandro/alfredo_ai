import json
import pandas as pd

def format_text_to_teams(text):
    """
    Convert a text response to a Microsoft Teams formatted message.
    Teams supports standard Markdown.
    
    Args:
        text (str): The text to format
        
    Returns:
        dict: A Teams formatted message with type and text
    """
    return {
        "type": "message",
        "text": text
    }

def format_json_to_teams(json_data):
    """
    Format JSON data as a Microsoft Teams message
    
    Args:
        json_data (list/dict): The JSON data to format
        
    Returns:
        dict: A Teams formatted message with type and text
    """
    # Create plain text representation
    text = json.dumps(json_data, indent=2)
    
    # Format as monospace block (triple backticks) for Teams
    formatted_text = f"```json\n{text}\n```"
    
    return {
        "type": "message",
        "text": formatted_text
    }

def dataframe_to_teams(df):
    """
    Format a pandas DataFrame as a Microsoft Teams message
    
    Args:
        df (pandas.DataFrame): The DataFrame to format
        
    Returns:
        dict: A Teams formatted message with type and text
    """
    # Create markdown table representation
    if df.empty:
        return {
            "type": "message",
            "text": "*No data*"
        }
        
    # Markdown table header
    headers = " | ".join(df.columns)
    separator = " | ".join(["---"] * len(df.columns))
    
    rows = []
    for _, row in df.iterrows():
        rows.append(" | ".join([str(val) for val in row]))
        
    table = f"| {headers} |\n| {separator} |\n"
    for row in rows:
        table += f"| {row} |\n"
    
    return {
        "type": "message",
        "text": table
    }
