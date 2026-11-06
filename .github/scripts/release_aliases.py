"""Allow mutable image aliases only at the newest stable tag in their series."""

import re
import subprocess
import sys


def alias_policy(version: str, tags: list[str]) -> dict[str, bool]:
    if not re.fullmatch(r"\d+\.\d+\.\d+", version):
        raise ValueError("Expected a stable X.Y.Z version")
    selected = tuple(map(int, version.split(".")))
    versions = {
        tuple(map(int, tag[1:].split(".")))
        for tag in tags
        if re.fullmatch(r"v\d+\.\d+\.\d+", tag)
    }
    if selected not in versions:
        raise ValueError("Release tag is missing")
    return {
        "latest": selected == max(versions),
        "major": selected == max(item for item in versions if item[0] == selected[0]),
        "minor": selected == max(item for item in versions if item[:2] == selected[:2]),
    }


if __name__ == "__main__":
    tags = subprocess.check_output(["git", "tag", "--list"], text=True).splitlines()
    for alias, eligible in alias_policy(sys.argv[1], tags).items():
        print(f"{alias}={str(eligible).lower()}")
