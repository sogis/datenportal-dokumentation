#!/usr/bin/env bash
set -euo pipefail
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
sources_root="${REPO_DIR}/.."
while [[ $# -gt 0 ]]; do
  case "$1" in
    --sources-root)
      [[ $# -ge 2 && -n "$2" ]] || { echo '--sources-root benötigt einen Pfad.' >&2; exit 2; }
      sources_root="$2"; shift 2 ;;
    --help|-h)
      echo 'Usage: scripts/build-local.sh [--sources-root PATH]'
      echo 'Environment: JAVA_HOME, PYTHON, THOTH_REPO_DIR, THOTH_JAR'
      exit 0 ;;
    *) echo "Unbekannte Option: $1" >&2; exit 2 ;;
  esac
done
# Resolve caller-relative paths before changing directories.
sources_root="$(cd "$sources_root" && pwd)"
python="${PYTHON:-python3}"
if [[ -z "${PYTHON:-}" && -x "$REPO_DIR/.venv/bin/python" ]]; then
  python="$REPO_DIR/.venv/bin/python"
fi
python="$(command -v "$python")" || { echo 'Python fehlt; PYTHON setzen.' >&2; exit 1; }
if [[ "$python" == */* ]]; then
  python="$(cd "$(dirname "$python")" && pwd)/$(basename "$python")"
fi
java="${JAVA_HOME:+${JAVA_HOME}/bin/}java"
command -v git >/dev/null || { echo 'Git fehlt.' >&2; exit 1; }
java_version="$("$java" -version 2>&1)" || { echo 'Java 25 benötigt; JAVA_HOME setzen.' >&2; exit 1; }
if [[ ! "$java_version" =~ version[[:space:]]+\"25[.\"] ]]; then
  echo 'Java 25 benötigt; JAVA_HOME auf eine Java-25-Installation setzen.' >&2; exit 1
fi
"$python" -c 'import yaml' || { echo 'PyYAML fehlt; Python-Umgebung gemäss README einrichten.' >&2; exit 1; }
if [[ -n "${THOTH_JAR:-}" ]]; then
  jar="$(cd "$(dirname "$THOTH_JAR")" && pwd)/$(basename "$THOTH_JAR")"
else
  thoth="${THOTH_REPO_DIR:-${REPO_DIR}/../thoth}"
  [[ -x "$thoth/gradlew" ]] || { echo "Thoth-Checkout fehlt: $thoth" >&2; exit 1; }
  thoth="$(cd "$thoth" && pwd)"
  (cd "$thoth" && ./gradlew :thoth-biblios:fatJar)
  jars=("$thoth"/thoth-biblios/build/libs/*-all.jar)
  [[ ${#jars[@]} -eq 1 && -f "${jars[0]}" ]] || { echo 'Kein eindeutiges Biblios-All-JAR gefunden.' >&2; exit 1; }
  jar="${jars[0]}"
fi
[[ -s "$jar" ]] || { echo "Thoth-JAR fehlt: $jar" >&2; exit 1; }
help="$("$java" -jar "$jar" build --help)" || { echo "Thoth-JAR ungültig oder veraltet (build --help fehlt): $jar. Thoth aktualisieren und neu bauen." >&2; exit 1; }
[[ "$help" == *--use-local-working-tree* ]] || { echo 'Thoth-JAR unterstützt build --use-local-working-tree noch nicht. Thoth aktualisieren und neu bauen.' >&2; exit 1; }
cd "$REPO_DIR"
PYTHON="$python" ./scripts/generate-local-config.sh --sources-root "$sources_root"
"$java" -jar "$jar" build --config biblios.local.yml --use-local-working-tree
for artifact in index.html search-index.json; do
  [[ -s "build/site/$artifact" ]] || { echo "Buildartefakt fehlt: build/site/$artifact" >&2; exit 1; }
done
