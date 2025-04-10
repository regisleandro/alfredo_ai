# Google Chat Formatters

This module provides utilities for formatting responses to be displayed in Google Chat with rich formatting.

## Components

1. **google_chat.py** - Contains functions for formatting different types of data into Google Chat card format
   - `format_text_to_google_chat_card` - Formats text content with rich markdown
   - `format_json_to_google_chat_card` - Formats JSON data in a readable card
   - `format_inline_markdown` - Helper for converting markdown to HTML
   - `dataframe_to_google_chat_card` - Formats pandas DataFrame data

2. **response_translator.py** - Provides the main entry point for translation
   - `translate_response` - Detects response type and applies the appropriate formatter

## Usage

```python
from api.formatters.response_translator import translate_response

# Your response could be text, DataFrame, or list (JSON)
my_response = "This is a *formatted* text with _italics_ and `code`"

# Translate to Google Chat format
chat_message = translate_response(my_response)

# Return to client
return chat_message
``` 