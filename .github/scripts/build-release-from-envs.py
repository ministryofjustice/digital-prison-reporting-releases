#!/usr/bin/env python3
import os, re, subprocess, json

# Try to load PyYAML if present
try:
    import yaml  # type: ignore
except Exception:
    yaml = None

roots = ["Prod", "PreProd"]
rows = []            # (date, tag, env, project, path)
seen = set()         # dedupe by (env, project, tag)

TEXT_EXTS = (".yaml", ".yml", ".json", ".properties", ".env", ".txt", ".conf", ".cfg")

def read_text(path):
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            data = f.read()
        if "\x00" in data:  # skip binaries
            return ""
        return data
    except Exception:
        return ""

def last_commit_date(path):
    try:
        out = subprocess.check_output(["git", "log", "-1", "--format=%as", "--", path], text=True).strip()
        return out or "-"
    except Exception:
        return "-"

def find_keys_anywhere(obj, keys):
    """Return dict of {key: first_value_found} by walking arbitrarily nested YAML/JSON."""
    found = {}
    lowkeys = {k.lower() for k in keys}
    def walk(x):
        if isinstance(x, dict):
            for k, v in x.items():
                lk = str(k).lower()
                if lk in lowkeys and lk not in found:
                    # normalize to string
                    found[lk] = str(v)
                walk(v)
        elif isinstance(x, list):
            for i in x:
                walk(i)
    walk(obj)
    return found

def parse_properties_lines(text):
    out = {}
    for line in text.splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        # key=value or key: value
        m = re.match(r"^([A-Za-z0-9_.-]+)\s*[:=]\s*(.+)$", s)
        if m:
            out[m.group(1).lower()] = m.group(2).strip().strip('"').strip("'")
    return out

def regex_fallback(text):
    """Very forgiving fallback for arbitrary text."""
    project = None
    tag = None
    # project
    m = re.search(r'"project"\s*:\s*"([^"]+)"', text, re.I)
    if not m:
        m = re.search(r"^\s*project\s*[:=]\s*['\"]?([^#'\"\r\n]+)", text, re.I | re.M)
    if m:
        project = m.group(1).strip()
    # tag / version
    for pat in [
        r'"tag"\s*:\s*"([^"]+)"',
        r"^\s*tag\s*[:=]\s*['\"]?([^#'\"\r\n]+)",
        r'"version"\s*:\s*"([^"]+)"',
        r"^\s*version\s*[:=]\s*['\"]?([^#'\"\r\n]+)",
    ]:
        m = re.search(pat, text, re.I | re.M)
        if m:
            tag = m.group(1).strip()
            break
    return project, tag

def extract_project_tag(path):
    # Prefer parsing by extension
    lower = path.lower()
    text = read_text(path)
    if not text:
        return None, None

    # JSON
    if lower.endswith(".json"):
        try:
            obj = json.loads(text)
            found = find_keys_anywhere(obj, {"project", "tag", "version"})
            project = found.get("project")
            tag = found.get("tag") or found.get("version")
            return project, tag
        except Exception:
            pass

    # YAML
    if lower.endswith((".yaml", ".yml")) and yaml is not None:
        try:
            obj = yaml.safe_load(text)
            found = find_keys_anywhere(obj, {"project", "tag", "version"})
            project = found.get("project")
            tag = found.get("tag") or found.get("version")
            return project, tag
        except Exception:
            pass

    # .properties / .env / .conf
    if lower.endswith((".properties", ".env", ".conf", ".cfg", ".txt")):
        d = parse_properties_lines(text)
        project = d.get("project")
        tag = d.get("tag") or d.get("version")
        if project or tag:
            return project, tag

    # Fallback regex for any other text file
    return regex_fallback(text)

# Walk Prod & PreProd
for env in roots:
    if not os.path.isdir(env):
        continue
    for root, _, files in os.walk(env):
        for name in files:
            path = os.path.join(root, name)
            # skip obvious binaries by extension
            if not name.lower().endswith(TEXT_EXTS):
                # still allow fallback regex on unknown text—comment next 2 lines to enable all files
                # txt = read_text(path)
                # if not txt: continue
                pass

            project, tag = extract_project_tag(path)
            if not project and not tag:
                continue

            key = (env.lower(), (project or "-").lower(), (tag or "-").lower())
            if key in seen:
                continue
            seen.add(key)
            date = last_commit_date(path)
            rows.append((date, tag or "-", env, project or "-", path))

# Sort newest date first, then Prod before PreProd, then project
rows.sort(key=lambda r: (0 if r[2].lower() == "prod" else 1, r[3].lower(), r[4].lower()))
rows.sort(key=lambda r: r[0], reverse=True)

# Write markdown body
os.makedirs("/tmp", exist_ok=True)
with open("/tmp/release_body.md","w",encoding="utf-8") as out:
    out.write("| Version | Date       | Description |\n")
    out.write("|---------|------------|-------------|\n")
    if rows:
        for date, tag, env, project, _ in rows:
            out.write(f"| {tag} | {date} | {env} - {project} |\n")
    else:
        out.write("| - | - | No releases yet |\n")

# Also write a tiny debug file so you can see what was found in CI logs if needed
with open("/tmp/release_debug.txt","w",encoding="utf-8") as dbg:
    for date, tag, env, project, path in rows:
        dbg.write(f"{date}\t{tag}\t{env}\t{project}\t{path}\n")
