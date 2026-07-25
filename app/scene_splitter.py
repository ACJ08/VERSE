import re

def split_into_scenes(text: str):
    pattern = r"(?=INT\.|EXT\.|INT\./EXT\.)"
    scenes = re.split(pattern, text)
    return [scene.strip() for scene in scenes if scene.strip()]
    