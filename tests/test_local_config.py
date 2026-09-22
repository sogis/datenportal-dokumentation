"""Exercise local resolution against disposable Git repositories."""
import importlib.util
from pathlib import Path
from urllib.parse import unquote, urlparse
import subprocess
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/generate_local_config.py'
spec = importlib.util.spec_from_file_location('local_config', SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class LocalConfigTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='biblios-config-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.config = self.root / 'biblios.yml'
        self.output = self.root / 'biblios.local.yml'
        self.sources = self.root / 'sources with spaces'
        self.sources.mkdir()
        self.config.write_text('''ui:
  content_toc: off
  content_section_numbers: on
  show_edit_link: true
content:
  sources:
    - id: example
      url: https://example.org/team/example.git
      branches:
        - name: main
          display_version: Aktuell
      default_version: main
      sidebar_toc_numbers: on
''')
        self.original = self.config.read_bytes()

    def git(self, path, *args):
        return subprocess.run(['git', '-C', str(path), *args], check=True, capture_output=True, text=True)

    def make_repo(self):
        repo = self.sources / 'example'
        repo.mkdir()
        self.git(repo, 'init', '-b', 'docs/architecture')
        return repo

    def generate(self):
        messages = module.generate(self.config, self.output, self.sources)
        self.assertEqual(self.config.read_bytes(), self.original)
        return module.yaml.safe_load(self.output.read_text()), messages

    def test_local_branch_and_yaml_enum_strings(self):
        repo = self.make_repo()
        data, messages = self.generate()
        source = data['content']['sources'][0]
        self.assertEqual(Path(unquote(urlparse(source['url']).path)).resolve(), repo.resolve())
        self.assertEqual(source['branches'], [{'name': 'docs/architecture', 'display_version': 'Lokal'}])
        self.assertEqual(source['default_version'], 'docs/architecture')
        self.assertEqual(data['ui']['content_toc'], 'off')
        self.assertEqual(data['ui']['content_section_numbers'], 'on')
        self.assertIs(data['ui']['show_edit_link'], True)
        self.assertEqual(source['sidebar_toc_numbers'], 'on')
        self.assertIn('Lokal:', messages[0])

    def test_missing_source_remains_remote(self):
        data, messages = self.generate()
        source = data['content']['sources'][0]
        self.assertEqual(source['url'], 'https://example.org/team/example.git')
        self.assertEqual(source['default_version'], 'main')
        self.assertIn('Remote:', messages[0])

    def test_detached_head_preserves_previous_output(self):
        repo = self.make_repo()
        self.git(repo, '-c', 'user.name=Test', '-c', 'user.email=test@example.invalid', 'commit', '--allow-empty', '-m', 'fixture')
        self.git(repo, 'checkout', '--detach')
        self.output.write_text('previous output')
        with self.assertRaisesRegex(ValueError, 'Detached HEAD'):
            self.generate()
        self.assertEqual(self.output.read_text(), 'previous output')
        self.assertEqual(self.config.read_bytes(), self.original)

    def test_reject_overwriting_source_or_moving_config(self):
        with self.assertRaisesRegex(ValueError, 'verschieden'):
            module.generate(self.config, self.config, self.sources)
        with self.assertRaisesRegex(ValueError, 'neben'):
            module.generate(self.config, self.sources / 'local.yml', self.sources)
        self.assertEqual(self.config.read_bytes(), self.original)


if __name__ == '__main__':
    unittest.main()
