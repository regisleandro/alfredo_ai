import re
import json
import pandas as pd

def format_text_to_google_chat_card(text):
    """
    Convert a text response to a properly formatted Google Chat card.
    
    Args:
        text (str): The text to format
        
    Returns:
        dict: A Google Chat card formatted message
    """
    # Convert string response to a Google Chat card format
    paragraphs = text.split('\n\n')
    sections = []
    
    # Add a header if the text starts with a task-like description
    first_paragraph = paragraphs[0].strip() if paragraphs else ""
    card_header = None
    
    if first_paragraph.startswith("A tarefa") or "task" in first_paragraph.lower():
        # Extract a title for the card
        title_match = re.search(r'["""]*([^"""]+)["""]*', first_paragraph)
        if title_match:
            card_header = {
                "title": title_match.group(1),
                "imageUrl": "https://www.gstatic.com/images/icons/material/system/1x/check_circle_outline_black_48dp.png",
                "imageStyle": "IMAGE"
            }
        else:
            # Just use a generic header
            card_header = {
                "title": "Task Analysis",
                "imageUrl": "https://www.gstatic.com/images/icons/material/system/1x/check_circle_outline_black_48dp.png",
                "imageStyle": "IMAGE"
            }
        
        # Format the first paragraph as a text introduction
        formatted_intro = format_inline_markdown(first_paragraph)
        sections.append({
            "widgets": [
                {
                    "textParagraph": {
                        "text": formatted_intro
                    }
                }
            ]
        })
        
        # Skip the first paragraph in further processing
        paragraphs = paragraphs[1:]
    
    current_section = {"widgets": []}
    has_conclusion = False
    
    for paragraph in paragraphs:
        if not paragraph.strip():
            continue
        
        # Check if it's a numbered header (like "1. **Identification of Pending Points**:")
        is_section_header = re.search(r'^\d+\.\s+\*\*([^*]+)\*\*', paragraph.strip())
        
        if is_section_header:
            # If we had content in the current section, add it to sections
            if current_section["widgets"]:
                sections.append(current_section)
                current_section = {"widgets": []}
            
            # Add a section header
            section_title = is_section_header.group(1).strip()
            sections.append({
                "header": section_title,
                "widgets": []
            })
            
            # Process any remaining content after the header
            remaining_content = paragraph[is_section_header.end():].strip()
            if remaining_content:
                formatted_content = format_inline_markdown(remaining_content)
                current_section["widgets"].append({
                    "textParagraph": {
                        "text": formatted_content
                    }
                })
        
        # Check if the paragraph is a list (numbered or bulleted)
        elif any(paragraph.strip().startswith(prefix) for line in paragraph.strip().split('\n') 
                for prefix in ('1.', '2.', '3.', '- ', '* ')):
            list_items = paragraph.strip().split('\n')
            
            for item in list_items:
                if not item.strip():
                    continue
                    
                # Format the list item
                formatted_item = format_inline_markdown(item)
                current_section["widgets"].append({
                    "keyValue": {
                        "content": formatted_item,
                        "contentMultiline": True,
                        "icon": "DESCRIPTION" if item.strip().startswith(('-', '*', '•')) else None,
                        "bottomLabel": "" if item.strip().startswith(('-', '*', '•')) else None
                    }
                })
        # Check if this is a concluding paragraph (typically the last one)
        elif paragraph == paragraphs[-1] and "more details" in paragraph.lower():
            has_conclusion = True
            # Format as a footer note
            formatted_conclusion = format_inline_markdown(paragraph)
            sections.append({
                "widgets": [
                    {
                        "textParagraph": {
                            "text": f"<i>{formatted_conclusion}</i>"
                        }
                    }
                ]
            })
        else:
            # Handle regular paragraphs
            formatted_paragraph = format_inline_markdown(paragraph)
            current_section["widgets"].append({
                "textParagraph": {
                    "text": formatted_paragraph
                }
            })
    
    # Add the last section if it has content and wasn't a conclusion
    if current_section["widgets"] and not has_conclusion:
        sections.append(current_section)
    
    card_data = {
        "cards": [
            {
                "sections": sections
            }
        ]
    }
    
    # Add header if we found one
    if card_header:
        card_data["cards"][0]["header"] = card_header
        
    return card_data

def format_inline_markdown(text):
    """
    Format inline markdown elements to Google Chat's supported formatting
    
    Args:
        text (str): The text with markdown formatting
        
    Returns:
        str: Text with HTML formatting for Google Chat
    """
    # Replace bold (**text** or *text*) with <b>text</b>
    formatted = re.sub(r'\*\*([^*]+)\*\*|\*([^*]+)\*', r'<b>\1\2</b>', text)
    
    # Replace italics (_text_) with <i>text</i>
    formatted = re.sub(r'_([^_]+)_', r'<i>\1</i>', formatted)
    
    # Replace code blocks (`text`) with <code>text</code>
    formatted = re.sub(r'`([^`]+)`', r'<code>\1</code>', formatted)
    
    # Ensure bullet points are properly formatted
    if formatted.strip().startswith(('- ', '* ')):
        formatted = '• ' + formatted[2:].strip()
    
    # Format numbered list items
    numbered_match = re.match(r'^(\d+)\.\s+(.+)$', formatted.strip())
    if numbered_match:
        number, content = numbered_match.groups()
        formatted = f"{number}. {content}"
    
    return formatted

def format_json_to_google_chat_card(json_data):
    """
    Format JSON data as a Google Chat card
    
    Args:
        json_data (list/dict): The JSON data to format
        
    Returns:
        dict: A Google Chat card formatted message with JSON data
    """
    return {
        "cards": [
            {
                "header": {
                    "title": "JSON Response"
                },
                "sections": [
                    {
                        "widgets": [
                            {
                                "textParagraph": {
                                    "text": f"<pre>{json.dumps(json_data, indent=2)}</pre>"
                                }
                            }
                        ]
                    }
                ]
            }
        ]
    }

def dataframe_to_google_chat_card(df):
    """
    Format a pandas DataFrame as a Google Chat card
    
    Args:
        df (pandas.DataFrame): The DataFrame to format
        
    Returns:
        dict: A Google Chat card formatted message with DataFrame data
    """
    markdown_list = ""
    for _, row in df.iterrows():
        list_item = "- " + ", ".join([f"{col}: *{row[col]}*" for col in df.columns]) + "\n"
        markdown_list += list_item
    
    # Process the markdown list to a card format
    lines = markdown_list.split('\n')
    
    # Create widgets for each line
    widgets = []
    for line in lines:
        if line.strip():  # Ignore empty lines
            # Process basic markdown formatting
            # Replace *text* with <b>text</b> for bold
            formatted_line = line.replace('*', '<b>', 1)
            if '*' in formatted_line:
                formatted_line = formatted_line.replace('*', '</b>', 1)
                remaining_asterisks = formatted_line.count('*')
                for i in range(0, remaining_asterisks, 2):
                    if i < remaining_asterisks:
                        formatted_line = formatted_line.replace('*', '<b>', 1)
                    if i + 1 < remaining_asterisks:
                        formatted_line = formatted_line.replace('*', '</b>', 1)
            
            widgets.append({
                "keyValue": {
                    "content": formatted_line,
                    "contentMultiline": True,
                    "icon": "DESCRIPTION"
                }
            })
            
    card = {
        "cards": [
            {
                "header": {
                    "title": "Data Results",
                    "imageUrl": "https://www.gstatic.com/images/icons/material/system/1x/insert_chart_black_48dp.png",
                    "imageStyle": "IMAGE"
                },
                "sections": [
                    {
                        "widgets": widgets
                    }
                ]
            }
        ]
    }

    return card 