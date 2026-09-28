#!/usr/bin/env python3
"""Smoke-test a built image directly and behind a temporary prefix-stripping proxy.

Uses only its own containers/network; requires Docker and Python 3.
"""
import argparse
import json
import subprocess
import tempfile
import time
import uuid
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.urls = []

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        for key in ('href', 'src'):
            if key in values:
                self.urls.append(values[key])


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args):
        return None


def run(*args):
    return subprocess.check_output(args, text=True).strip()


def request(url, headers=None):
    try:
        response = build_opener(NoRedirect).open(Request(url, headers=headers or {}), timeout=10)
    except HTTPError as error:
        response = error
    with response:
        return response.code, response.headers, response.read()


def verify_site(base):
    status, headers, home = request(base)
    assert status == 200 and b'<html' in home.lower(), (base, status)
    assert headers.get('Cache-Control') == 'no-cache'
    parser = Links()
    parser.feed(home.decode())
    # Exercise actual generated links, not a synthetic test site.
    assets = [urljoin(base, p) for p in parser.urls if 'site-assets/' in p]
    assert assets, 'No generated assets found'
    for url in assets:
        assert url.startswith(base), ('Asset escaped the prefix', url)
        assert request(url)[0] == 200, url
    status, _, index = request(base + 'search-index.json')
    assert status == 200
    assert json.loads(index), 'Empty search index'
    assert request(base + 'search/')[0] == 200
    # These sections are part of the documentation's configured content contract.
    for section in ('architektur', 'betrieb', 'datenpublikation'):
        chapter = base + section + '/main/'
        status, _, body = request(chapter)
        assert status == 200, (chapter, status)
        links = Links()
        links.feed(body.decode())
        for link in links.urls:
            if link.startswith(('https:', 'http:', 'mailto:', 'data:', '#', '//')):
                continue
            target = urljoin(chapter, link)
            assert target.startswith(base), ('Link escaped the prefix', target)
            assert request(target)[0] == 200, target
        status, headers, _ = request(chapter.rstrip('/') + '?test=1')
        assert status == 308, (chapter, status)
        assert headers['Location'] == urlsplit(chapter).path + '?test=1', headers['Location']
    for missing in ('not-a-page', 'not-a-page/', 'site-assets/missing.js'):
        assert request(base + missing)[0] == 404, missing
    print('PASS: pages, assets, SVGs, search index, redirects and 404 at', base)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--image', default='datenportal-dokumentation:test')
    args = parser.parse_args()
    scope = 'datenportal-docs-test-' + uuid.uuid4().hex[:10]
    containers = []
    network_created = False
    try:
        run('docker', 'network', 'create', scope)
        network_created = True
        docs = scope + '-docs'
        run('docker', 'run', '-d', '--name', docs, '--network', scope, '--network-alias', 'docs',
            '-p', '127.0.0.1::8080', args.image)
        containers.append(docs)
        direct = 'http://' + run('docker', 'port', docs, '8080/tcp') + '/'
        for _ in range(30):
            try:
                if request(direct)[0] == 200:
                    break
            except (URLError, ConnectionError):
                pass
            time.sleep(1)
        else:
            raise AssertionError('Documentation container did not become ready')
        assert run('docker', 'exec', docs, 'id', '-u') != '0', 'Runtime must not be root'
        verify_site(direct)
        for prefix in ('https://evil.example', '//evil.example', '/bad prefix'):
            status, headers, _ = request(direct + 'betrieb/main', {'X-Forwarded-Prefix': prefix})
            assert status == 308 and headers['Location'] == '/betrieb/main/'
        with tempfile.TemporaryDirectory(prefix='datenportal-docs-proxy-') as directory:
            config = Path(directory) / 'default.conf'
            config.write_text('''server {
    listen 8080;
    absolute_redirect off;
    location = /dokumentation { return 308 /dokumentation/$is_args$args; }
    location /dokumentation/ {
        proxy_set_header X-Forwarded-Prefix /dokumentation;
        proxy_pass http://docs:8080/;
    }
    location / { return 404; }
}
''')
            proxy = scope + '-proxy'
            run('docker', 'run', '-d', '--name', proxy, '--network', scope,
                '-p', '127.0.0.1::8080', '-v', str(config) + ':/etc/nginx/conf.d/default.conf:ro', args.image)
            containers.append(proxy)
            proxied = 'http://' + run('docker', 'port', proxy, '8080/tcp')
            for _ in range(30):
                try:
                    if request(proxied + '/dokumentation/')[0] == 200:
                        break
                except (URLError, ConnectionError):
                    pass
                time.sleep(1)
            else:
                raise AssertionError('Prefix proxy did not become ready')
            status, headers, _ = request(proxied + '/dokumentation?test=1')
            assert status == 308 and headers['Location'] == '/dokumentation/?test=1'
            verify_site(proxied + '/dokumentation/')
        # Image healthcheck must also work, independently of the proxy checks.
        for _ in range(20):
            health = run('docker', 'inspect', '--format', '{{.State.Health.Status}}', docs)
            if health == 'healthy':
                break
            time.sleep(1)
        assert health == 'healthy', health
        print('PASS: non-root runtime and image healthcheck')
    finally:
        for name in reversed(containers):
            subprocess.run(['docker', 'rm', '-f', name], check=False, stdout=subprocess.DEVNULL)
        if network_created:
            subprocess.run(['docker', 'network', 'rm', scope], check=False, stdout=subprocess.DEVNULL)


if __name__ == '__main__':
    main()
