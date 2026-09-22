# datenportal-dokumentation

Dieses Repository ist das zentrale Thoth-Biblios-Projekt für die Datenportal-
Dokumentation. Es enthält die Website-Konfiguration und führt eigenständige
Dokumentations- und Code-Repositories zusammen. Auch das Glossar liegt in einem
eigenen Quellrepo. Die sichtbaren Startseitenbereiche werden unter
`content.sources` in `biblios.yml` gepflegt.

## Voraussetzungen

- Java 25 (wie in CI) und ein gebautes Thoth-Biblios-All-JAR.
- Git; für Remote-Quellen Netzwerkzugriff und gegebenenfalls Git-Zugriffsrechte.
- Für die lokale Konfiguration: Python 3 mit PyYAML.

Im Root dieses Repositories eine lokale Python-Umgebung einrichten:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install PyYAML
```

## Lokale Vorschau

Die Quellrepos liegen normalerweise als Schwesterverzeichnisse neben diesem
Repository. Der Generator leitet deren Verzeichnisnamen aus den Remote-URLs ab.

```bash
PYTHON=.venv/bin/python ./scripts/generate-local-config.sh
java -jar ../thoth/thoth-biblios/build/libs/thoth-biblios-0.0.1-SNAPSHOT-all.jar serve \
  --config biblios.local.yml --port 8091 --use-local-working-tree
```

Die Vorschau ist unter <http://localhost:8091/> erreichbar. Java bei Bedarf über
den Pfad einer Java-25-Installation aufrufen; den JAR-Pfad an die lokale
Installation anpassen.

`biblios.local.yml` ist generiert und wird nicht versioniert. Vorhandene lokale
Quellen verwenden ihren ausgecheckten Branch statt der zentral konfigurierten
Versionen. `--use-local-working-tree` macht dort auch uncommittete Inhalte
sichtbar. Nach einem Branchwechsel den Generator erneut ausführen und die
Vorschau neu starten. Detached HEAD wird abgelehnt. Fehlende Schwesterrepos
bleiben Remote-Quellen; der Generator zeigt dies ausdrücklich an.

Für einen anderen gemeinsamen Quellordner:

```bash
PYTHON=.venv/bin/python ./scripts/generate-local-config.sh --sources-root /pfad/zu/quellen
```

Der Generator schreibt absolute `file://`-Adressen nur in die ignorierte lokale
Datei, weil Biblios sie auch für den ersten lokalen Git-Clone benötigt. Nach einem
Umzug der Repositories die Datei neu erzeugen. Die Ausgabe liegt neben
`biblios.yml`, damit übrige relative Biblios-Pfade ihre Bedeutung behalten. Die
zentrale Konfiguration wird niemals überschrieben. Hilfe: `./scripts/generate-local-config.sh --help`.

## Remote-Build und Veröffentlichung

`biblios.yml` enthält ausschliesslich Remote-Quellen und ist die Grundlage für CI:

```bash
java -jar ../thoth/thoth-biblios/build/libs/thoth-biblios-0.0.1-SNAPSHOT-all.jar build \
  --config biblios.yml
```

Ein Remote-Build verwendet die bereitgestellten Git-Stände, keine lokalen
Änderungen. Neue Architektur-Inhalte müssen zuerst im Architektur-Remote unter
`main` vorhanden sein, bevor der vollständige Remote-Build erfolgreich sein kann.

Bestehende Forgejo- und GitHub-Actions bauen und veröffentlichen die Website bei
Pushes auf `main` dieses Repositories oder bei manuellem Workflow-Start:

- [Codeberg Pages](https://edigonzales.codeberg.page/datenportal-dokumentation/)
- [GitHub Pages](https://edigonzales.github.io/datenportal-dokumentation/)

Änderungen allein in Quellrepos lösen diese Workflows nicht aus. Die konfigurierte
produktive Zieladresse ist `https://daten.so.ch/dokumentation`; dies bestätigt
keinen bereits erfolgten Produktiv-Rollout. Automatische Quellrepo-Trigger und
das Festlegen einer Biblios-Version sind separate Aufgaben.

## Generator prüfen

Die Tests verwenden ausschliesslich temporäre Git-Repositories. Sie prüfen
lokale Branches, fehlende Quellen, Detached HEAD und den Erhalt der Biblios-Werte
`on`/`off` sowie der zentralen Konfiguration:

```bash
.venv/bin/python -m unittest discover -s tests -v
```
