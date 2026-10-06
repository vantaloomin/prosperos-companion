"""Reading a link the user pastes, on this computer (PRD X1-X3).

A link in the user's message is its own trigger: the app, not the model, fetches it. Reddit posts are
read through Reddit's public JSON view, X posts through X's oEmbed endpoint, YouTube videos through
YouTube's oEmbed endpoint, and other pages by pulling the readable text out of their HTML.

Only public addresses are fetched: a link that names or resolves to this computer, the local network
or another private address is refused, and every redirect is checked the same way. Responses are
bounded in time and size, and the result is plain text that is quoted to the companion as outside
information, never followed as instructions.
"""
import asyncio
import html
import ipaddress
import json
import re
import socket
from html.parser import HTMLParser
from urllib.parse import quote, urljoin, urlsplit

import httpx

from companion.mcp.client import ToolFailure

URL = re.compile(r'\bhttps?://[^\s<>"\'`]+', re.I)
TRAILING = '.,;:!?)]}\'"'
MAX_LINKS = 2
MAX_URL = 2000
MAX_BYTES = 1_500_000
MAX_REDIRECTS = 4
TIMEOUT = 6.0
MAX_TEXT = 6000
USER_AGENT = 'Mozilla/5.0 (compatible; ProsperoCompanion/1.0; reads links the user shares)'
TEXT_TYPES = ('text/html', 'application/xhtml+xml', 'text/plain', 'application/json', 'text/markdown')

REDDIT_HOSTS = {'reddit.com', 'www.reddit.com', 'old.reddit.com', 'new.reddit.com', 'np.reddit.com', 'm.reddit.com'}
X_HOSTS = {'x.com', 'www.x.com', 'twitter.com', 'www.twitter.com', 'mobile.twitter.com', 'mobile.x.com'}
YOUTUBE_HOSTS = {'youtube.com', 'www.youtube.com', 'm.youtube.com', 'music.youtube.com', 'youtu.be'}
X_STATUS = re.compile(r'^/([A-Za-z0-9_]{1,15})/status(?:es)?/(\d{1,25})')
REDDIT_POST = re.compile(r'^/(?:r/[^/]+/)?comments/[A-Za-z0-9]+')
REDDIT_SUBREDDIT = re.compile(r'^/r/([A-Za-z0-9_]{2,21})/?$')


def find(text: str) -> list[str]:
    """The first links in a message, in order, without trailing punctuation or repeats."""
    found = []
    for match in URL.finditer(text or ''):
        url = match.group(0)
        while url and url[-1] in TRAILING:
            # Keep a closing bracket that belongs to the address, as in Wikipedia titles.
            if url[-1] == ')' and url.count('(') >= url.count(')'):
                break
            url = url[:-1]
        if url and len(url) <= MAX_URL and url not in found:
            found.append(url)
        if len(found) == MAX_LINKS:
            break
    return found


def host_of(url: str) -> str:
    return (urlsplit(url).hostname or '').lower()


def resolve(host: str, port: int) -> list[str]:
    return [item[4][0] for item in socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)]


def public(address: str) -> bool:
    ip = ipaddress.ip_address(address.split('%')[0])
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped:
        ip = ip.ipv4_mapped
    return ip.is_global and not ip.is_multicast


class Reader:
    """Fetches one link. `resolver` and `client` are replaceable for tests."""

    def __init__(self, client: httpx.AsyncClient | None = None, resolver=resolve):
        self.client = client
        self.resolver = resolver

    async def read(self, url: str) -> dict:
        """{'title', 'text', 'kind', 'url'} or a ToolFailure with a reason fit to show."""
        owns = self.client is None
        client = self.client or httpx.AsyncClient(timeout=TIMEOUT, follow_redirects=False,
                                                  headers={'User-Agent': USER_AGENT})
        try:
            return await asyncio.wait_for(self.follow(client, url), TIMEOUT + 1)
        except TimeoutError as error:
            raise ToolFailure('timeout', 'The page took too long to load.') from error
        finally:
            if owns:
                await client.aclose()

    async def follow(self, client, url: str) -> dict:
        for _hop in range(MAX_REDIRECTS + 1):
            await self.check(url)
            special = await self.special(client, url)
            if special is not None:
                return special
            response = await self.get(client, url)
            if response['redirect']:
                url = response['redirect']
                continue
            return page(url, response)
        raise ToolFailure('redirects', 'The link redirected too many times.')

    async def check(self, url: str):
        parts = urlsplit(url)
        if parts.scheme not in {'http', 'https'} or not parts.hostname:
            raise ToolFailure('address', 'Only web links can be read.')
        if parts.username or parts.password:
            raise ToolFailure('address', 'Links with a user name or password are not read.')
        try:
            port = parts.port or (443 if parts.scheme == 'https' else 80)
        except ValueError as error:
            raise ToolFailure('address', 'The link is not a valid address.') from error
        try:
            addresses = await asyncio.to_thread(self.resolver, parts.hostname, port)
        except OSError as error:
            raise ToolFailure('not_found', 'The site could not be found.') from error
        if not addresses or not all(public(address) for address in addresses):
            raise ToolFailure('private', 'Links to this computer or a private network are not read.')

    async def get(self, client, url: str, accept: str = 'text/html,application/xhtml+xml,text/plain;q=0.9,*/*;q=0.5'):
        try:
            async with client.stream('GET', url, headers={'Accept': accept}) as response:
                if response.status_code in {301, 302, 303, 307, 308}:
                    location = response.headers.get('location')
                    if not location:
                        raise ToolFailure('http', 'The site sent a broken redirect.')
                    return {'redirect': urljoin(url, location)}
                if response.status_code != 200:
                    raise failure_for(response.status_code)
                kind = response.headers.get('content-type', '').split(';')[0].strip().lower()
                if kind and not kind.startswith(TEXT_TYPES):
                    raise ToolFailure('unsupported', unsupported_reason(kind))
                body = bytearray()
                async for chunk in response.aiter_bytes():
                    body.extend(chunk)
                    if len(body) > MAX_BYTES:
                        break
                return {'redirect': None, 'kind': kind, 'body': bytes(body[:MAX_BYTES]),
                        'encoding': response.charset_encoding or 'utf-8'}
        except httpx.TimeoutException as error:
            raise ToolFailure('timeout', 'The page took too long to load.') from error
        except httpx.HTTPError as error:
            raise ToolFailure('transport', 'The site could not be reached.') from error

    async def get_json(self, client, url: str):
        await self.check(url)
        response = await self.get(client, url, accept='application/json')
        if response['redirect']:
            raise ToolFailure('unavailable', 'The post is not available.')
        try:
            return json.loads(response['body'].decode(response['encoding'], errors='replace'))
        except ValueError as error:
            raise ToolFailure('unreadable', 'The site sent an unreadable answer.') from error

    async def special(self, client, url: str) -> dict | None:
        """Sites whose pages need a browser, read through their public data endpoints instead."""
        parts, host = urlsplit(url), host_of(url)
        if host in REDDIT_HOSTS and REDDIT_POST.match(parts.path):
            path = parts.path.rstrip('/')
            data = await self.get_json(client, f'https://www.reddit.com{path}.json?limit=8&depth=1&raw_json=1')
            return reddit_post(url, data)
        if host in REDDIT_HOSTS and (match := REDDIT_SUBREDDIT.match(parts.path)):
            data = await self.get_json(client, f'https://www.reddit.com/r/{match.group(1)}/hot.json?limit=8&raw_json=1')
            return reddit_listing(url, match.group(1), data)
        if host in X_HOSTS:
            match = X_STATUS.match(parts.path)
            if not match:
                raise ToolFailure('sign_in', 'X only shows posts, not profiles or searches, without signing in.')
            canonical = f'https://twitter.com/{match.group(1)}/status/{match.group(2)}'
            data = await self.get_json(client, 'https://publish.twitter.com/oembed?omit_script=true&dnt=true&url='
                                       + quote(canonical, safe=''))
            return x_post(url, data)
        if host in YOUTUBE_HOSTS and (host == 'youtu.be' or parts.path.startswith(('/watch', '/shorts/', '/live/'))):
            data = await self.get_json(client, 'https://www.youtube.com/oembed?format=json&url=' + quote(url, safe=''))
            return youtube_video(url, data)
        return None


def failure_for(status: int) -> ToolFailure:
    if status in {401, 403}:
        return ToolFailure('refused', f'The site refused to show the page (HTTP {status}).')
    if status in {404, 410}:
        return ToolFailure('not_found', 'The page was not found; it may have been deleted.')
    if status == 429:
        return ToolFailure('rate_limited', 'The site asked the app to slow down (HTTP 429).')
    return ToolFailure('http', f'The site answered with HTTP {status}.')


def unsupported_reason(kind: str) -> str:
    if kind == 'application/pdf':
        return 'PDFs are not read on this computer.'
    if kind.startswith(('image/', 'video/', 'audio/')):
        return 'The link is an image, video or sound file, which cannot be read as text.'
    return f'The link is a file ({kind}), not a page.'


def squeeze(text: str) -> str:
    text = re.sub(r'[ \t\r\f\v]+', ' ', text)
    text = re.sub(r' *\n *', '\n', text)
    return re.sub(r'\n{3,}', '\n\n', text).strip()


def bounded(text: str, limit: int = MAX_TEXT) -> str:
    return text if len(text) <= limit else text[:limit - 1].rstrip() + '…'


def reddit_post(url: str, data) -> dict:
    try:
        post = data[0]['data']['children'][0]['data']
        comments = [item['data'] for item in data[1]['data']['children'] if item.get('kind') == 't1']
    except (KeyError, IndexError, TypeError) as error:
        raise ToolFailure('unreadable', 'Reddit sent an answer the app could not read.') from error
    title = str(post.get('title') or '')
    lines = [f"Reddit post in {post.get('subreddit_name_prefixed', 'a subreddit')} by u/{post.get('author', '?')} "
             f"({post.get('score', 0)} points, {post.get('num_comments', 0)} comments): {title}"]
    if post.get('selftext'):
        lines.append(bounded(squeeze(post['selftext']), 3000))
    if post.get('url') and not post.get('is_self') and post['url'] != url:
        lines.append(f"Links to: {post['url']}")
    if post.get('over_18'):
        lines.append('(Marked NSFW.)')
    if comments:
        lines.append('Top comments:')
        lines += [f"- u/{item.get('author', '?')} ({item.get('score', 0)} points): "
                  f"{bounded(squeeze(str(item.get('body') or '')), 400)}" for item in comments[:5]]
    return {'url': url, 'kind': 'reddit', 'title': title, 'text': bounded('\n'.join(lines))}


def reddit_listing(url: str, subreddit: str, data) -> dict:
    try:
        posts = [item['data'] for item in data['data']['children']]
    except (KeyError, TypeError) as error:
        raise ToolFailure('unreadable', 'Reddit sent an answer the app could not read.') from error
    if not posts:
        raise ToolFailure('empty', 'The subreddit has no posts the app can see.')
    lines = [f'Popular posts in r/{subreddit} right now:']
    lines += [f"- {post.get('title', '')} ({post.get('score', 0)} points, {post.get('num_comments', 0)} comments)"
              for post in posts[:8]]
    return {'url': url, 'kind': 'reddit', 'title': f'r/{subreddit}', 'text': bounded('\n'.join(lines))}


class Blocks(HTMLParser):
    """The readable text of a page: title, description and paragraph-like blocks, without navigation."""
    SKIP = {'script', 'style', 'noscript', 'svg', 'nav', 'footer', 'header', 'aside', 'form', 'iframe', 'template',
            'button', 'select', 'canvas', 'dialog'}
    BLOCK = {'p', 'h1', 'h2', 'h3', 'h4', 'li', 'blockquote', 'pre', 'figcaption', 'td', 'dd', 'dt'}
    VOID = {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'source', 'track', 'wbr'}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.skipping = 0
        self.main = 0
        self.title, self.in_title = '', False
        self.meta: dict[str, str] = {}
        self.blocks: list[tuple[bool, str]] = []
        self.current: list[str] | None = None

    def handle_starttag(self, tag, attrs):
        values = {key: value or '' for key, value in attrs}
        if tag == 'meta':
            key = (values.get('property') or values.get('name') or '').lower()
            if key in {'description', 'og:description', 'og:title', 'og:site_name', 'twitter:description',
                       'article:published_time'} and values.get('content'):
                self.meta.setdefault(key, values['content'])
            return
        if tag in self.VOID:
            return
        if tag in self.SKIP:
            self.skipping += 1
        elif tag in {'article', 'main'}:
            self.main += 1
        elif tag == 'title':
            self.in_title = True
        elif tag in self.BLOCK and not self.skipping:
            self.flush()
            self.current = []

    def handle_endtag(self, tag):
        if tag in self.SKIP:
            self.skipping = max(self.skipping - 1, 0)
        elif tag in {'article', 'main'}:
            self.main = max(self.main - 1, 0)
        elif tag == 'title':
            self.in_title = False
        elif tag in self.BLOCK:
            self.flush()

    def handle_data(self, data):
        if self.in_title:
            self.title += data
        elif self.current is not None and not self.skipping:
            self.current.append(data)

    def flush(self):
        if self.current is not None:
            text = ' '.join(''.join(self.current).split())
            if len(text) > 1:
                self.blocks.append((self.main > 0, text))
        self.current = None


def page(url: str, response: dict) -> dict:
    text = response['body'].decode(response['encoding'], errors='replace')
    if response['kind'] in {'text/html', 'application/xhtml+xml'} or (not response['kind'] and '<html' in text[:500]):
        return html_page(url, text)
    body = squeeze(text)
    if not body:
        raise ToolFailure('empty', 'The page is empty.')
    return {'url': url, 'kind': 'page', 'title': '', 'text': bounded(body)}


def html_page(url: str, markup: str) -> dict:
    parser = Blocks()
    try:
        parser.feed(markup)
        parser.close()
    except Exception as error:  # noqa: BLE001 - html.parser rarely fails; a broken page reads as unreadable.
        raise ToolFailure('unreadable', 'The page could not be read.') from error
    parser.flush()
    in_main = [text for main, text in parser.blocks if main]
    blocks = in_main if sum(len(text) for text in in_main) >= 200 else [text for _main, text in parser.blocks]
    title = ' '.join((parser.meta.get('og:title') or parser.title).split())
    description = ' '.join((parser.meta.get('description') or parser.meta.get('og:description')
                            or parser.meta.get('twitter:description') or '').split())
    body = '\n'.join(blocks)
    if len(body) < 80 and not description:
        raise ToolFailure('needs_browser', 'The page only shows its content in a web browser.')
    head = [f"Page: {title}" + (f" ({parser.meta['og:site_name']})" if parser.meta.get('og:site_name') else '')]
    if parser.meta.get('article:published_time'):
        head.append(f"Published: {parser.meta['article:published_time'][:10]}")
    if description and description not in body:
        head.append(f'Description: {description}')
    return {'url': url, 'kind': 'page', 'title': title, 'text': bounded('\n'.join(head) + '\n\n' + body)}


class Quote(HTMLParser):
    """The text of X's embedded post markup: the post's paragraph and its date link."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.depth, self.text, self.after, self.anchor = 0, [], [], False

    def handle_starttag(self, tag, attrs):
        if tag == 'p':
            self.depth += 1
        elif tag == 'br' and self.depth:
            self.text.append('\n')
        elif tag == 'a':
            self.anchor = True

    def handle_endtag(self, tag):
        if tag == 'p':
            self.depth = max(self.depth - 1, 0)
        elif tag == 'a':
            self.anchor = False

    def handle_data(self, data):
        if self.depth:
            self.text.append(data)
        elif self.anchor:
            self.after.append(data)


def x_post(url: str, data) -> dict:
    if not isinstance(data, dict) or not data.get('html'):
        raise ToolFailure('unavailable', 'The post is not available; it may be private, deleted or age-restricted.')
    parser = Quote()
    parser.feed(data['html'])
    text = squeeze(''.join(parser.text))
    author = html.unescape(str(data.get('author_name') or ''))
    handle = urlsplit(str(data.get('author_url') or '')).path.strip('/')
    date = parser.after[-1].strip() if parser.after else ''
    if not text:
        raise ToolFailure('empty', 'The post has no text the app can read; it may be only a picture or video.')
    lines = [f"Post on X by {author}" + (f' (@{handle})' if handle else '') + (f', {date}' if date else '') + ':',
             text, 'Only the post itself is available, not replies or images.']
    return {'url': url, 'kind': 'x', 'title': f'Post by {author}', 'text': bounded('\n'.join(lines))}


def youtube_video(url: str, data) -> dict:
    if not isinstance(data, dict) or not data.get('title'):
        raise ToolFailure('unavailable', 'The video is not available; it may be private or removed.')
    title, channel = str(data['title']), str(data.get('author_name') or '')
    text = f'YouTube video "{title}"' + (f' by {channel}' if channel else '') + \
        '. Only the title and channel are available, not the video itself.'
    return {'url': url, 'kind': 'youtube', 'title': title, 'text': text}
