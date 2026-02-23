def make_cron_context_id() -> str:
    import uuid

    return f"cron:task:{uuid.uuid4()}"


def is_cron_context_id(context_id: str) -> bool:
    return context_id.startswith("cron:task:")
