from pathlib import Path


def read_env(path: str = ".env") -> dict:
    result = {}
    p = Path(path)
    if not p.exists():
        return result
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        result[k.strip()] = v.strip()
    return result


def write_env(values: dict, path: str = ".env") -> None:
    p = Path(path)
    lines = p.read_text(encoding="utf-8").splitlines() if p.exists() else []
    remaining = dict(values)
    out = []
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and "=" in stripped:
            key = stripped.partition("=")[0].strip()
            if key in values:
                out.append(f"{key}={values[key]}")
                remaining.pop(key, None)
                continue
        out.append(line)
    for key, val in remaining.items():
        out.append(f"{key}={val}")
    p.write_text("\n".join(out) + "\n", encoding="utf-8")
