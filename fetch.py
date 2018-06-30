from __future__ import print_function
from bs4 import BeautifulSoup
from bs4 import SoupStrainer
from dateutil.parser import *
import requests
import urlparse
import re
import urllib
import bleach


# allows us to get mobile version
user_agent_mobile = 'Mozilla/5.0 (Linux; Android 7.0; SM-G610F Build/NRD90M) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/63.0.3239.111 Mobile Safari/537.36'
user_agent_desktop = 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/67.0.3396.87 Safari/537.36'

base_url = 'https://mbasic.facebook.com/'
max_title_length = 100


def get_remote_data(url, ismobile=True, referer=None):
    ''' fetch website data as mobile or desktop browser'''
    user_agent = user_agent_mobile if ismobile else user_agent_desktop

    headers = {'User-Agent': user_agent}
    if referer:
        headers['Referer'] = referer

    r = requests.get(url, headers=headers)
    return r.content


def is_valid_username(username):
    ''' validate username '''

    expr = '^(?:pages\/)?(?P<display>[\w\-\.]{3,50})(\/\d{3,50})?$'
    result = re.match(expr, username)
    display = result.group('display') if result else None
    return (result, display)


def strip_invalid_html(content):
    ''' strips invalid tags/attributes '''

    allowed_tags = ['a', 'abbr', 'acronym', 'address', 'b', 'br', 'div', 'dl', 'dt',
                    'em', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'hr', 'i', 'img',
                    'li', 'ol', 'p', 'pre', 'q', 's', 'small', 'strike', 'strong',
                    'span', 'sub', 'sup', 'table', 'tbody', 'td', 'tfoot', 'th',
                    'thead', 'tr', 'tt', 'u', 'ul']
    allowed_attrs = {
        'a': ['href', 'target', 'title'],
        'img': ['src', 'alt', 'width', 'height'],
    }

    cleaned = bleach.clean(content,
                        tags=allowed_tags,
                        attributes=allowed_attrs,
                        strip=True)

    # handle malformed html after running through bleach
    tree = BeautifulSoup(cleaned, "lxml")
    return tree.html


def sub_video_link(m):
    expr = '\&amp\;source.+$'
    orig = m.group(1)
    unquoted = urllib.unquote(orig)
    new = re.sub(expr, '\" target', unquoted)
    return new


def fix_video_redirect_link(content):
    ''' replace video redirects with direct link '''

    expr = '\/video_redirect\/\?src=(.+)\"\starget'
    result = re.sub(expr, sub_video_link, content)
    return result


def sub_leaving_link(m):
    expr = '\&amp\;h.+$'
    orig = m.group(1)
    unquoted = urllib.unquote(orig)
    new = re.sub(expr, '\" target', unquoted)
    return new


def fix_leaving_link(content):
    ''' replace leaving fb links with direct link '''

    expr = 'http.+facebook\.com\/l.php\?u\=(.+)\"\starget'
    result = re.sub(expr, sub_leaving_link, content)
    return result


def fix_article_links(content):
    # fix video links
    v_fix = fix_video_redirect_link(content)
    # fix leaving links
    l_fix = fix_leaving_link(v_fix)
    # convert links to absolute
    a_fix = l_fix.replace('href="/', 'href="{0}'.format(base_url))

    return a_fix


def fix_guid_url(url):
    ''' add base + strip extra parameters '''

    expr = '([&\?]?(?:type|refid|source)=\d+&?.+$)'
    stripped = re.sub(expr, '', url)

    guid = urlparse.urljoin(base_url, stripped)
    return guid


def build_site_url(username):
    return urlparse.urljoin(base_url, username)


def build_title(entry):
    ''' build title from entry '''

    text = entry.get_text().strip()

    if len(text) > max_title_length:
        last_word = text.rfind(' ', 0, max_title_length)
        text = text[:last_word] + '...'

    return text


def build_article(text, extra):
    ''' fix up article content '''

    content = (text.encode("utf8") + ' '
               + extra.encode("utf8")
               )
    return strip_invalid_html(fix_article_links(content.decode("utf8")))


def extract_items(contents):
    ''' extract posts from page '''

    print('Extracting posts from page')

    main_content = SoupStrainer('div', {'id': 'recent'})
    soup = BeautifulSoup(contents, "lxml", parse_only=main_content)
    items = []

    if soup.div:
        for item in soup.div.div.div.children:
            item_link = item.find('a', text='Full Story')
            if not item_link:
                continue  # ignore if no permalink found

            url = fix_guid_url(item_link['href'])
            date = parse(item.find('abbr').text.strip(), fuzzy=True)
            author = item.div.find('h3').a.get_text(strip=True)
            article_byline = item.div.div.get_text()

            # add photos/videos
            article_text = ''
            if item.div.div.next_sibling:
                article_text = item.div.div.next_sibling

            article_extra = ''
            if item.div.div.next_sibling.next_sibling:
                article_extra = item.div.div.next_sibling.next_sibling

            # cleanup article
            article = build_article(article_text, article_extra)

            article_title = build_title(article_text)
            if not article_title:
                article_title = article_byline

            items.append({
                'url': url,
                'title': article_title,
                'article': article,
                'date': date,
                'author': author
            })

        print('{0} posts found'.format(len(items)))

        return items
    # else
    return None
