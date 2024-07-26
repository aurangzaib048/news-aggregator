import json
import sys


def verify_json(file_path):
    try:
        with open(file_path, "r") as f:
            json.load(f)
        print(f"{file_path} is valid JSON.")
    except json.JSONDecodeError as e:
        print(f"{file_path} is not valid JSON. Error: {e}")


if __name__ == "__main__":
    for arg in sys.argv[1:]:
        verify_json(arg)
