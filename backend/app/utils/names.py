def doctor_display_name(name: str) -> str:
    """Adds "Dr." unless the saved name already starts with it
    (patients often type "Dr. Anjali Thapa")."""
    stripped = name.strip()
    if stripped.lower().startswith(("dr.", "dr ")):
        return stripped
    return f"Dr. {stripped}"
