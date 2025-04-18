import pandas as pd
from .google_chat import (
    format_text_to_google_chat,
    format_json_to_google_chat,
    dataframe_to_google_chat
)

def translate_response(response):
    """
    Translate various response types to properly formatted Google Chat messages
    
    Args:
        response: The response to translate (can be list, DataFrame, or string)
        
    Returns:
        dict: A Google Chat message with text and formattedText
    """
    if response is None:
        return {
            "text": "Nenhum resultado encontrado.",
            "formattedText": "Nenhum resultado encontrado."
        }
    
    if isinstance(response, list):
        return format_json_to_google_chat(response)
    
    if isinstance(response, pd.DataFrame):
        return dataframe_to_google_chat(response)

    # For text responses
    return format_text_to_google_chat(response) 