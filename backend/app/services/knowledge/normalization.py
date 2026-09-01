"""Text normalization utilities for extracted document content."""


def normalize_extracted_text(text: str) -> str:
    """Normalize extracted text without AI or external services.
    
    Rules:
    - Remove null characters
    - Collapse 3+ consecutive newlines to 2
    - Strip trailing whitespace per line
    - Preserve Unicode characters
    - Preserve paragraph structure (single newlines between paragraphs)
    - Limit pathological repeated characters (50+ same char -> 3)
    - Remove leading newline before first content
    """
    if not text:
        return text
    
    # Remove null characters
    text = text.replace("\x00", "")
    
    # Collapse 3+ consecutive newlines to 2
    import re
    text = re.sub(r"\n{3,}", "\n\n", text)
    
    # Strip trailing whitespace per line
    lines = text.split("\n")
    lines = [line.rstrip() for line in lines]
    text = "\n".join(lines)
    
    # Limit pathological repeated characters (50+ same char -> 3)
    # Handle both regular chars and special chars
    text = re.sub(r"(.)\1{49,}", r"\1\1\1", text)
    
    # Remove leading blank lines
    text = text.lstrip("\n")
    
    return text.strip()