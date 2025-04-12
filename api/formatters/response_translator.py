import pandas as pd
from .google_chat import (
    format_text_to_google_chat_card,
    format_json_to_google_chat_card,
    dataframe_to_google_chat_card
)

def translate_response(response):
    """
    Translate various response types to properly formatted Google Chat messages
    
    Args:
        response: The response to translate (can be list, DataFrame, or string)
        
    Returns:
        dict: A properly formatted Google Chat message
    """
    if response is None:
        return {
            "cards": [
                {
                    "sections": [
                        {
                            "widgets": [
                                {
                                    "textParagraph": {
                                        "text": "Nenhum resultado encontrado."
                                    }
                                }
                            ]
                        }
                    ]
                }
            ]
        }
    
    if isinstance(response, list):
        return format_json_to_google_chat_card(response)
    
    if isinstance(response, pd.DataFrame):
        return dataframe_to_google_chat_card(response)

    # For text responses
    return format_text_to_google_chat_card(response) 