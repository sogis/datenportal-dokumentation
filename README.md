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

Eine bestehende GitHub-Action baut und veröffentlicht die Website bei
Pushes auf `main` dieses Repositories oder bei manuellem Workflow-Start:

- [GitHub Pages](https://sogis.github.io/datenportal-dokumentation/)

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

## Statisches Containerimage

Das Image `ghcr.io/sogis/datenportal-dokumentation` liefert die bereits gebauten
HTML-Seiten mit `nginxinc/nginx-unprivileged:1.30.4-alpine-slim` aus. Der Prozess
läuft ohne Root auf Port 8080. Java und Thoth gehören nicht ins Runtime-Image;
die Inhalte sind ein fester Buildstand und werden nicht zur Laufzeit neu erzeugt.

Zuerst die HTML-Seiten mit dem oben beschriebenen Thoth-Build erzeugen, dann:

```bash
docker build -t datenportal-dokumentation:local .
python3 scripts/test-container.py --image datenportal-dokumentation:local
docker run --rm -p 127.0.0.1:8093:8080 datenportal-dokumentation:local
```

Der Container ist damit unter <http://localhost:8093/> erreichbar. Der Build
verlangt `build/site/index.html` und `build/site/search-index.json`. Die
`.dockerignore` lässt ausschliesslich Runtime-Konfiguration und `build/site/`
in den Buildkontext; Quellrepos, Secrets und die Thoth-Caches werden nicht
verpackt. Der Image-Healthcheck prüft die ausgelieferte Startseite.

Lokale Working-Trees inklusive uncommitteter Inhalte einmalig bauen:

```bash
./scripts/build-local.sh
docker build -t datenportal-dokumentation:local .
```

Der HTML-Build benötigt Java 25 (`JAVA_HOME`), Git und Python mit PyYAML.
Ohne `PYTHON` wird `.venv/bin/python`, danach `python3` verwendet.
Standardmässig baut er das All-JAR in `../thoth` per Gradle (`THOTH_REPO_DIR`
überschreibt den Checkout). `THOTH_JAR` verwendet stattdessen ein vorhandenes
All-JAR mit Unterstützung für `build --use-local-working-tree`.
`--sources-root /pfad/zu/quellen` wählt einen anderen gemeinsamen Quellordner.
Explizite relative Pfade werden vom Aufrufverzeichnis aus aufgelöst.
Vorhandene lokale Quellen verwenden ihren aktuellen Branch samt uncommitteter
Inhalte; fehlende Quellen bleiben mit Hinweis remote, Detached HEAD ist ein Fehler.
Ein fehlgeschlagener HTML-Build darf nicht durch einen Image-Build fortgesetzt werden.

Eine laufende Vorschau vor dem Build anhalten, damit sie nicht gleichzeitig
`build/site` verändert. CI verwendet weiterhin Remote-Quellen aus `biblios.yml`.
Im dev-stack übernimmt `./scripts/up.sh --local-docs` HTML- und Image-Build und
liefert das Ergebnis über APISIX unter `http://localhost:8081/dokumentation/` aus.
Ein abweichender `GARAGE_PUBLIC_PORT` wird vom Stack berücksichtigt.

### Hinter APISIX unter `/dokumentation/`

Das Image ist prefix-neutral: Seiten, Assets und Suche verwenden die relativen
Biblios-Links. APISIX muss `/dokumentation` mit HTTP 308 auf `/dokumentation/`
umleiten, bei `/dokumentation/*` den Prefix entfernen und
`X-Forwarded-Prefix: /dokumentation` setzen. Queryparameter bleiben erhalten.
NGINX verwendet diesen Header für Weiterleitungen auf Verzeichnisadressen mit
abschliessendem Slash. Ein ungültiger Header wird ignoriert. Das Image benötigt
keine HTML-Ersetzungen und keinen SPA-Fallback; unbekannte Dateien liefern 404.
Alle Antworten verwenden `Cache-Control: no-cache`, damit Browser Dateien bei
Neuveröffentlichung revalidieren. TLS endet am vorgelagerten Gateway/Router.

Der Containertest startet ausschliesslich eigene temporäre Container und ein
eigenes Netzwerk. Er prüft Startseite, Kapitel, Assets/SVGs, Suchindex,
Slash-Weiterleitungen und 404 sowohl direkt als auch unter `/dokumentation/`.
Danach räumt er seine Ressourcen auf. Die dauerhafte Dev-Stack-Einbindung verwendet dieselben Prefix-Regeln.

### Veröffentlichung mit GitHub Actions

`.github/workflows/biblios-build.yml` baut bei Push auf `main` oder manuellem
Start die Dokumentation einmal. Nach erfolgreichem Container-HTTP-Test wird
derselbe HTML-Stand für GitHub Pages und das Containerimage verwendet. Das
Image wird bei Läufen auf `main` für `linux/amd64` und `linux/arm64` mit denselben
Tags und demselben Digest in beide Registries veröffentlicht:

- GHCR: `ghcr.io/sogis/datenportal-dokumentation`
- Docker Hub: `sogis/datenportal-dokumentation`

GHCR verwendet den eingebauten `GITHUB_TOKEN` mit `packages: write` im
Veröffentlichungsjob. Für Docker Hub sind unter **Settings → Secrets and
variables → Actions** diese Repository-Secrets erforderlich:

| Secret | Inhalt |
|---|---|
| `DOCKERHUB_USERNAME` | Docker-Hub-Benutzer mit Schreibrecht auf `sogis/datenportal-dokumentation` |
| `DOCKERHUB_TOKEN` | Access-Token dieses Benutzers mit Schreibrecht |

Tokenwerte gehören ausschliesslich in die Secret-Verwaltung. Das Docker-Hub-
Repository muss öffentlich sein, damit der Dev-Stack es ohne Anmeldung beziehen
kann. Die Veröffentlichung wird nur nach erfolgreichem Login in beide Registries
versucht; bei einem späteren Registryfehler kann bereits eine der beiden
Kopien veröffentlicht sein. Workflow-Ergebnis und Digests dann abgleichen.

Tags:

- `latest`: letzter erfolgreich veröffentlichter Build auf `main`.
- `sha-<commit>`: Kurz-SHA des Aggregator-Commits.
- `0.1.<run_number>`: laufbezogener Versionstag analog zum Datenblatt-Editor.

Die Quellrepos und der Thoth-Snapshot können sich bei einem erneuten Lauf
ändern, auch wenn der Aggregator-Commit gleich bleibt. Für einen exakt fixierten
Stand deshalb den im Workflow-Ergebnis ausgegebenen **Image-Digest** verwenden;
ein SHA-Tag allein fixiert nicht alle Dokumentationsquellen. Der Workflow
protokolliert zusätzlich die aufgelöste Thoth-Snapshot-Version.

Nach der ersten Veröffentlichung in den GitHub-Paketeinstellungen von
`sogis/datenportal-dokumentation` die Sichtbarkeit auf **Public** setzen, sofern
sie noch privat ist. Neue GHCR-Pakete sind standardmässig privat, auch bei einem
öffentlichen Repository. Dafür sind Verwaltungsrechte am Paket nötig; der
Workflow verändert diese Einstellung nicht. Siehe
[GitHub: Container Registry](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry).
Der Workflow versucht für jede Registry einen Pull mit leerer Docker-Konfiguration
und meldet im Ergebnis getrennt, wenn der anonyme Abruf noch nicht funktioniert.

```bash
docker pull ghcr.io/sogis/datenportal-dokumentation:latest
docker run --rm -p 127.0.0.1:8093:8080 \
  ghcr.io/sogis/datenportal-dokumentation:latest
```

Alternativ von Docker Hub:

```bash
docker pull sogis/datenportal-dokumentation:latest
docker run --rm -p 127.0.0.1:8093:8080 sogis/datenportal-dokumentation:latest
```

Für Updates ein neues Image ziehen und den Container neu erzeugen. Änderungen
in einem Quellrepo lösen weiterhin keinen automatischen Aggregator-Build aus:
Quelländerungen zuerst pushen und danach den Workflow manuell starten.
