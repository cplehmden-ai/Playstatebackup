
def normalize(path):
    if not path:
        return ""

    return path.replace("\\", "/").rstrip("/")