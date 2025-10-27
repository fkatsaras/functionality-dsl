"""Code formatting utilities."""


def format_python_code(code: str) -> str:
    """Format generated Python code with Black if available."""
    try:
        import black
        return black.format_str(code, mode=black.FileMode())
    except Exception:
        # black not installed or failed — return unformatted code
        return code
