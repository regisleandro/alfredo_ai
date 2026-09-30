import pandas as pd
from .google_chat import (
    format_text_to_google_chat,
    format_json_to_google_chat,
    dataframe_to_google_chat
)
from .teams import (
    format_text_to_teams,
    format_json_to_teams,
    dataframe_to_teams
)

def translate_response(response, platform="google_chat"):
    """
    Translate various response types to properly formatted messages for the specified platform
    
    Args:
        response: The response to translate (can be list, DataFrame, or string)
        platform (str): The target platform, e.g. "google_chat" or "teams". Default is "google_chat".
        
    Returns:
        dict: A formatted message for the target platform
    """
    if platform == "teams":
        if response is None:
            return {
                "type": "message",
                "text": "Nenhum resultado encontrado."
            }
        
        if isinstance(response, list):
            return format_json_to_teams(response)
        
        if isinstance(response, pd.DataFrame):
            return dataframe_to_teams(response)

        # For text responses
        return format_text_to_teams(response)
    
    # Default: google_chat
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