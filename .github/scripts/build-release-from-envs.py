#!/usr/bin/env python3
import os, re, subprocess, sys

roots = ["Prod", "PreProd"]
rows = []            # (date, tag, env, project, path)
seen = set()         # dedupe by (env, project, tag)

def read_text(path):
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            data = f.read(20000)
        if "\x00" in data:  # skip binaries
            return ""
        return data
    except Exception:
        return ""

def first_match(patterns, text):
    flags = re.IGNORECASE | re.MULTILINE
    for pat in patterns:
        m = re.search(pat, text, flags)
        if m:
            return m.group(1).strip()
    return None

def last_commit_date(path):
    try:
        out = subprocess.check_output(
            ["git", "log", "-1", "--format=%as", "--", path],
            text=True
        ).strip()
        return out or "-"
    except Exception:
        return "-"

for env in roots:
    if not os.path.isdir(env):
        continue
    for root, _, files in os.walk(env):
        for name in files:
            path = os.path.join(root, name)

            # Restrict types if you want:
            # if not any(name.endswith(ext) for ext in (".yaml",".yml",".json",".properties",".env",".txt")):
            #     continue

            txt = read_text(path)
            if not txt:
                continue

            project = first_match([
                r'"project"\s*:\s*"([^"]+)"',                 # JSON
                r"^\s*project\s*[:=]\s*['\"]?([^#'\"\r\n]+)"  # YAML/properties
            ], txt)

            tag = first_match([
                r'"tag"\s*:\s*"([^"]+)"',
                r"^\s*tag\s*[:=]\s*['\"]?([^#'\"\r\n]+)",
                r'"version"\s*:\s*"([^"]+)"',
                r"^\s*version\s*[:=]\s*['\"]?([^#'\"\r\n]+)"
            ], txt)

            if not tag and not project:
                continue

            key = (env.lower(), (project or "-").lower(), (tag or "-").lower())
            if key in seen:
                continue
            seen.add(key)

            date = last_commit_date(path)
            rows.append((date, tag or "-", env, project or "-", path))

# Sort: newest date first, then Prod before PreProd, then project
rows.sort(key=lambda r: (0 if r[2].lower() == "prod" else 1, r[3].lower(), r[4].lower()))
rows.sort(key=lambda r: r[0], reverse=True)

# Write markdown table body to /tmp/release_body.md
os.makedirs("/tmp", exist_ok=True)
with open("/tmp/release_body.md","w",encoding="utf-8") as out:
    out.write("| Version | Date       | Description |\n")
    out.write("|---------|------------|-------------|\n")
    if rows:
        for date, tag, env, project, _ in rows:
            desc = f"{env} - {project}"
            out.write(f"| {tag} | {date} | {desc} |\n")
    else:
        out.write("| - | - | No releases yet |\n")
