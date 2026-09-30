# API Formatters

This module provides utilities for formatting responses to be displayed in different platforms, like Google Chat and Microsoft Teams, with rich formatting.

## Components

1. **google_chat.py** - Contains functions for formatting different types of data into Google Chat format
   - `format_text_to_google_chat` - Formats text content with rich markdown
   - `format_json_to_google_chat` - Formats JSON data in a readable block
   - `format_inline_markdown` - Helper for converting markdown to Google Chat markdown
   - `dataframe_to_google_chat` - Formats pandas DataFrame data

2. **teams.py** - Contains functions for formatting different types of data into Microsoft Teams format
   - `format_text_to_teams` - Formats text content
   - `format_json_to_teams` - Formats JSON data in a readable block
   - `dataframe_to_teams` - Formats pandas DataFrame data as markdown tables

3. **response_translator.py** - Provides the main entry point for translation
   - `translate_response` - Detects response type and applies the appropriate formatter depending on the `platform` argument.

## Usage

```python
from api.formatters.response_translator import translate_response

# Your response could be text, DataFrame, or list (JSON)
my_response = "This is a *formatted* text with _italics_ and `code`"

# Translate to Google Chat format (default)
chat_message = translate_response(my_response, platform="google_chat")

# Translate to Microsoft Teams format
teams_message = translate_response(my_response, platform="teams")

# Return to client
return chat_message
``` 