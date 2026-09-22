#!/usr/bin/env python3
"""Generate a local Biblios config without changing its remote source config."""
import argparse
import copy
from pathlib import Path
import subprocess
import sys
import re
from urllib.parse import unquote, urlparse

try:
    import yaml
except ImportError:
    sys.exit("PyYAML fehlt. Zuerst die Python-Umgebung gemäss README einrichten.")


class BibliosLoader(yaml.SafeLoader):
    """Keep YAML 1.2 on/off strings, as required by Biblios enum options."""


BibliosLoader.yaml_implicit_resolvers = copy.deepcopy(yaml.SafeLoader.yaml_implicit_resolvers)
for initial, resolvers in BibliosLoader.yaml_implicit_resolvers.items():
    BibliosLoader.yaml_implicit_resolvers[initial] = [
        (tag, pattern) for tag, pattern in resolvers if tag != "tag:yaml.org,2002:bool"
    ]
BibliosLoader.add_implicit_resolver(
    "tag:yaml.org,2002:bool", re.compile(r"^(?:true|True|TRUE|false|False|FALSE)$"), list("tTfF")
)


def generate(config_path, output_path, sources_root):
    if config_path.resolve() == output_path.resolve():
        raise ValueError("Ausgabe und zentrale Konfiguration müssen verschieden sein.")
    if config_path.parent.resolve() != output_path.parent.resolve():
        raise ValueError("Die lokale Konfiguration muss neben der zentralen liegen (relative Biblios-Pfade).")
    data = yaml.load(config_path.read_text(encoding="utf-8"), Loader=BibliosLoader)
    messages = []
    for source in data["content"]["sources"]:
        repo_name = Path(unquote(urlparse(source["url"]).path).rstrip("/")).name
        if repo_name.endswith(".git"):
            repo_name = repo_name[:-4]
        local = sources_root / repo_name
        if not local.exists():
            messages.append(f"Remote: {source['id']} (lokal fehlt: {local})")
            continue
        # Require this repository itself, not an enclosing repository.
        if not (local / ".git").exists():
            raise ValueError(f"Kein Git-Repository: {local}")
        result = subprocess.run(
            ["git", "-C", str(local), "symbolic-ref", "--quiet", "--short", "HEAD"],
            capture_output=True, text=True, check=False,
        )
        if result.returncode:
            raise ValueError(f"Kein ausgecheckter Branch (Detached HEAD oder Git-Fehler): {local}. Bitte einen Branch auschecken.")
        branch = result.stdout.strip()
        # Biblios also clones local sources before selecting the working tree.
        # Its Git resolver requires an absolute URI for a reliable first clone.
        source["url"] = local.resolve().as_uri()
        source["branches"] = [{"name": branch, "display_version": "Lokal"}]
        source["default_version"] = branch
        messages.append(f"Lokal: {source['id']} → {source['url']} ({branch})")
    # Prepare completely before writing: failures leave the previous output intact.
    rendered = "# Generiert durch scripts/generate-local-config.sh; nicht committen.\n"
    rendered += yaml.safe_dump(data, allow_unicode=True, sort_keys=False)
    output_path.write_text(rendered, encoding="utf-8")
    return messages


def main():
    root = Path(__file__).resolve().parent.parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=root / "biblios.yml")
    parser.add_argument("--output", type=Path, default=root / "biblios.local.yml")
    parser.add_argument("--sources-root", type=Path, default=root.parent)
    args = parser.parse_args()
    try:
        messages = generate(args.config, args.output, args.sources_root)
    except (OSError, ValueError, KeyError, TypeError, yaml.YAMLError) as error:
        parser.exit(1, f"Lokale Konfiguration nicht erzeugt: {error}\n")
    print("\n".join(messages))
    print(f"Geschrieben: {args.output}")


if __name__ == "__main__":
    main()
