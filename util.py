from multiprocessing.sharedctypes import Value


def get_id_from_tag(tag: str):
    try:
        return int(tag.strip().removeprefix("<@").removesuffix(">"))
    except ValueError:
        return None

