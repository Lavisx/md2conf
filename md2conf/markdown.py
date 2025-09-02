"""
Publish Markdown files to Confluence wiki.

Copyright 2022-2025, Levente Hunyadi

:see: https://github.com/hunyadi/md2conf
"""

import xml.etree.ElementTree
from typing import Any, Optional

import markdown


def _emoji_generator(
    index: str,
    shortname: str,
    alias: Optional[str],
    uc: Optional[str],
    alt: str,
    title: Optional[str],
    category: Optional[str],
    options: dict[str, Any],
    md: markdown.Markdown,
) -> xml.etree.ElementTree.Element:
    """
    Custom generator for `pymdownx.emoji`.
    """

    name = (alias or shortname).strip(":")
    emoji = xml.etree.ElementTree.Element("x-emoji", {"data-shortname": name})
    if uc is not None:
        emoji.attrib["data-unicode"] = uc

        # convert series of Unicode code point hexadecimal values into characters
        emoji.text = "".join(chr(int(item, base=16)) for item in uc.split("-"))
    else:
        emoji.text = alt

    return emoji


def _verbatim_formatter(
    source: str,
    language: str,
    css_class: str,
    options: dict[str, Any],
    md: markdown.Markdown,
    classes: Optional[list[str]] = None,
    id_value: str = "",
    attrs: Optional[dict[str, str]] = None,
    **kwargs: Any,
) -> str:
    """
    Custom formatter for `pymdownx.superfences`.

    Used by language `math` (a.k.a. `pymdownx.arithmatex`) and pseudo-language `csf` (Confluence Storage Format pass-through).
    """

    if classes is None:
        classes = [css_class]
    else:
        classes.insert(0, css_class)

    html_id = f' id="{id_value}"' if id_value else ""
    html_class = ' class="{}"'.format(" ".join(classes))
    html_attrs = " " + " ".join(f'{k}="{v}"' for k, v in attrs.items()) if attrs else ""

    return f"<div{html_id}{html_class}{html_attrs}>{source}</div>"


_CONVERTER = markdown.Markdown(
    extensions=[
        "admonition",
        "footnotes",
        "markdown.extensions.tables",
        "md_in_html",
        "pymdownx.arithmatex",
        "pymdownx.caret",
        "pymdownx.emoji",
        "pymdownx.highlight",  # required by `pymdownx.superfences`
        "pymdownx.magiclink",
        "pymdownx.mark",
        "pymdownx.superfences",
        "pymdownx.tilde",
        "sane_lists",
    ],
    extension_configs={
        "footnotes": {"BACKLINK_TITLE": ""},
        "pymdownx.arithmatex": {"generic": True, "preview": False, "tex_inline_wrap": ["", ""], "tex_block_wrap": ["", ""]},
        "pymdownx.emoji": {"emoji_generator": _emoji_generator},
        "pymdownx.highlight": {
            "use_pygments": False,
        },
        "pymdownx.superfences": {
            "custom_fences": [
                {"name": "math", "class": "arithmatex", "format": _verbatim_formatter},
                {"name": "csf", "class": "csf", "format": _verbatim_formatter},
            ]
        },
    },
)


def _preprocess_list_indentation(content: str) -> str:
    """
    Preprocesses markdown content to handle 2-space indentation for nested lists.
    Converts 2-space based indentation to 4-space based indentation:
    - 0 spaces → 0 spaces (no change)
    - 2 spaces → 4 spaces (level 1) 
    - 4 spaces → 8 spaces (level 2)
    - 6 spaces → 12 spaces (level 3)
    - 8 spaces → 16 spaces (level 4)
    etc.
    """
    lines = content.split('\n')
    processed_lines = []
    in_admonition = False
    in_code_block = False
    
    for i, line in enumerate(lines):
        # Skip empty lines
        if not line.strip():
            processed_lines.append(line)
            continue
            
        stripped = line.lstrip()
        
        # Detect code block start/end
        if line.strip().startswith(('```', '~~~')):
            in_code_block = not in_code_block
            processed_lines.append(line)
            continue
        
        # Skip processing if we're in a code block
        if in_code_block:
            processed_lines.append(line)
            continue
        
        # Detect admonition start
        if stripped.startswith('!!!'):
            in_admonition = True
            processed_lines.append(line)
            continue
        
        # Check if we're no longer in an admonition (next non-indented, non-empty line)
        if in_admonition and len(line) - len(stripped) == 0 and stripped:
            in_admonition = False
        
        # Count leading spaces
        leading_spaces = len(line) - len(line.lstrip())
        
        # Skip lines that don't have indentation or are special syntax elements
        if (leading_spaces == 0 or 
            stripped.startswith(('`', '#', '>')) or
            in_admonition):
            processed_lines.append(line)
            continue
        
        # Check if this looks like it's using 2-space indentation system
        # We detect this by checking if the line uses even spacing that's not already 4-space based
        if (leading_spaces % 2 == 0 and  # Even number of spaces
            _is_likely_2space_system(lines, i) and  # Appears to be using 2-space system
            (stripped.startswith(('* ', '- ', '+ ')) or  # List markers
             (stripped and stripped[0].isdigit() and '. ' in stripped[:10]) or  # Numbered list
             _is_list_continuation(lines, i))):  # Continuation of list content
            
            # Convert 2-space indentation to 4-space indentation
            # Each level of 2 spaces becomes 4 spaces
            indent_level = leading_spaces // 2
            new_indent = ' ' * (indent_level * 4)
            processed_lines.append(new_indent + stripped)
        else:
            # Don't modify other indented content (already properly formatted)
            processed_lines.append(line)
    
    return '\n'.join(processed_lines)


def _is_likely_2space_system(lines: list[str], current_index: int) -> bool:
    """
    Determines if the content around the current line appears to use 2-space indentation system.
    """
    # Look at a window of lines around the current position
    start = max(0, current_index - 5)
    end = min(len(lines), current_index + 5)
    
    space_counts = []
    for i in range(start, end):
        line = lines[i]
        if line.strip() and line.lstrip().startswith(('* ', '- ', '+ ')):
            spaces = len(line) - len(line.lstrip())
            if spaces > 0:
                space_counts.append(spaces)
    
    # If we find indentation levels that are odd multiples of 2 (2, 6, 10) 
    # or small even numbers that suggest 2-space system, it's likely 2-space based
    if not space_counts:
        return False
    
    # Check if we see characteristic 2-space patterns like 2, 4, 6, 8
    has_2space_pattern = any(spaces % 4 != 0 for spaces in space_counts if spaces % 2 == 0)
    return has_2space_pattern


def _is_list_continuation(lines: list[str], current_index: int) -> bool:
    """
    Determines if the current line is a continuation of list content.
    """
    if current_index == 0:
        return False
    
    # Look backwards to see if we're in a list context
    for i in range(current_index - 1, max(-1, current_index - 5), -1):
        line = lines[i]
        if line.strip():
            stripped = line.lstrip()
            if stripped.startswith(('* ', '- ', '+ ')):
                return True
            # If we hit a non-list, non-indented line, we're not in a list
            if len(line) - len(stripped) == 0:
                return False
    
    return False


def markdown_to_html(content: str) -> str:
    """
    Converts a Markdown document into XHTML with Python-Markdown.

    :param content: Markdown input as a string.
    :returns: XHTML output as a string.
    :see: https://python-markdown.github.io/
    """

    _CONVERTER.reset()
    # Preprocess content to handle 2-space list indentation
    preprocessed_content = _preprocess_list_indentation(content)
    html = _CONVERTER.convert(preprocessed_content)
    return html
