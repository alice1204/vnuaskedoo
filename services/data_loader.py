from pathlib import Path

import yaml


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"


def load_yaml(filename: str):
    path = DATA_DIR / filename

    with open(path, "r", encoding="utf-8") as file:
        return yaml.safe_load(file)


def load_students():
    return load_yaml("students.yaml")


def load_curriculum(cohort: str = "K68"):
    filename = f"curriculum_{cohort.lower()}.yaml"
    return load_yaml(filename)


def load_opened_courses():
    return load_yaml("opened_courses.yaml")