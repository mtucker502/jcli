"""Token counting wrapper using tiktoken (cl100k_base).

Note: cl100k_base is an approximation of Claude's tokenizer. Exact token counts
will differ, but directional comparisons (MCP vs CLI overhead) remain valid.
"""

import tiktoken

_encoding = tiktoken.get_encoding("cl100k_base")


def count_tokens(text: str) -> int:
    """Count tokens in a string using cl100k_base encoding."""
    return len(_encoding.encode(text))
