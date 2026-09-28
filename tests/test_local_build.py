"""Build orchestration checks with isolated fake toolchains, no Docker or network."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class LocalBuildTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'scripts').mkdir()
        shutil.copy(ROOT / 'scripts/build-local.sh', self.root / 'scripts/build-local.sh')
        self.executable('scripts/generate-local-config.sh', '#!/bin/sh\necho config > biblios.local.yml\n')
        self.executable('python', '#!/bin/sh\nexit "${PYTHON_FAILURE:-0}"\n')
        self.executable('jdk/bin/java', '''#!/bin/sh
if [ "$1" = -version ]; then
  echo 'openjdk version "25.0.3"' >&2
elif [ "$4" = --help ]; then
  [ "${OLD_JAR:-0}" = 0 ] && echo --use-local-working-tree || echo old-version
else
  [ "${BUILD_FAILURE:-0}" = 0 ] || exit 9
  mkdir -p build/site
  echo html > build/site/index.html
  echo '[]' > build/site/search-index.json
fi
''')
        (self.root / 'thoth.jar').write_text('fixture')
        self.env = {**os.environ, 'JAVA_HOME': str(self.root / 'jdk'),
                    'PYTHON': str(self.root / 'python'), 'THOTH_JAR': str(self.root / 'thoth.jar')}

    def executable(self, name, content):
        target = self.root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content)
        target.chmod(0o755)

    def run_build(self, **env):
        return subprocess.run([str(self.root / 'scripts/build-local.sh')], cwd=self.root,
                              env={**self.env, **env}, capture_output=True, text=True)

    def test_success_generates_config_and_site(self):
        result = self.run_build()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((self.root / 'biblios.local.yml').exists())
        self.assertTrue((self.root / 'build/site/search-index.json').exists())

    def test_missing_jar_fails_before_config(self):
        result = self.run_build(THOTH_JAR=str(self.root / 'missing.jar'))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Thoth-JAR fehlt', result.stderr)
        self.assertFalse((self.root / 'biblios.local.yml').exists())

    def test_old_jar_fails_before_config(self):
        result = self.run_build(OLD_JAR='1')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('unterstützt', result.stderr)
        self.assertFalse((self.root / 'biblios.local.yml').exists())

    def test_missing_pyyaml_fails_before_config(self):
        result = self.run_build(PYTHON_FAILURE='1')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('PyYAML', result.stderr)
        self.assertFalse((self.root / 'biblios.local.yml').exists())

    def test_failed_build_does_not_accept_stale_artifacts(self):
        self.assertEqual(self.run_build().returncode, 0)
        self.assertNotEqual(self.run_build(BUILD_FAILURE='1').returncode, 0)
