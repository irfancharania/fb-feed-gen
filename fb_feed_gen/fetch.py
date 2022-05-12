from bs4 import BeautifulSoup
from bs4 import SoupStrainer
from dateutil.parser import *
import requests
import urllib.parse
import re
import urllib.request
import urllib.parse
import urllib.error
import bleach
import json
import datetime


# allows us to get mobile version
user_agent_mobile = 'Mozilla/5.0 (Linux; Android 7.0; SM-G610M) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.80 Mobile Safari/537.36'
user_agent_desktop = 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/71.0.3578.98 Safari/537.36'

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

    expr = r'^(?:pages\/)?(?P<display>[\w\-\.]{3,50})(\/\d{3,50})?$'
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
    return str(tree.html)


def sub_video_link(m):
    expr = r'\&amp\;source.+$'
    orig = m.group(1)
    unquoted = urllib.parse.unquote(orig)
    new = re.sub(expr, '\" target', unquoted)
    return new


def fix_video_redirect_link(content):
    ''' replace video redirects with direct link '''

    expr = r'\/video_redirect\/\?src=(.+)\"\starget'
    result = re.sub(expr, sub_video_link, content)
    return result


def sub_leaving_link(m):
    expr = r'\&amp\;h.+$'
    orig = m.group(1)
    unquoted = urllib.parse.unquote(orig)
    new = re.sub(expr, '\" target', unquoted)
    return new


def fix_leaving_link(content):
    ''' replace leaving fb links with direct link '''

    expr = r'https:\/\/lm\.facebook\.com\/l.php\?u\=([a-zA-Z0-9\=\%\&\;\.\-\_]+)\"\s'
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

    expr = r'([&\?]?(?:type|refid|source)=\d+&?.+$)'
    stripped = re.sub(expr, '', url)
    guid = urllib.parse.urljoin(base_url, stripped)
    return guid


def build_site_url(username):
    return urllib.parse.urljoin(base_url, username)


def build_title(entry):
    ''' build title from entry '''

    if entry:
        text = entry.get_text().strip()
        if text:

            if len(text) > max_title_length:
                last_word = text.rfind(' ', 0, max_title_length)
                text = text[:last_word] + '...'
            return text

    return 'Title not found'


def build_article(text, extra):
    ''' fix up article content '''

    content = str(text) + ' ' + str(extra)
    return strip_invalid_html(fix_article_links(content))


def parse_publish_time(json_string):
    ''' parse json data to get publish timestamp '''
    
    data = json.loads(json_string)

    page_insights = data['page_insights']
    if page_insights:
        
        for key in page_insights.keys():
            if ('post_context' in page_insights[key].keys()):

                publish_time = page_insights[key]['post_context']['publish_time']
                date = datetime.datetime.fromtimestamp(publish_time)

                return date


def extract_items(username, contents, logger):
    ''' extract posts from page '''

    #print('Extracting posts from page')

    main_content = SoupStrainer('div', {'id': 'recent'})
    soup = BeautifulSoup(contents, "lxml", parse_only=main_content)

    items = []

    if soup.div:
        for item in soup.div.div.div.children:
            item_link = item.find('a', text='Full Story')
            if not item_link:
                continue  # ignore if no permalink found

            url = fix_guid_url(item_link['href'])
            
            # try to parse from json
            date = parse_publish_time(item['data-ft'])
            if date is None:
                # fallback to parsing from html
                date = parse(item.find('abbr').text.strip(), fuzzy=True)

            article_byline = ''
            article_text = ''
            article_extra = ''
            article_author = username

            if item.div.div:
                article_byline = item.div.div.get_text()
                article_author = item.div.div.find('h3').a.get_text(strip=True)

                # add photos/videos
                if item.div.div.next_sibling:
                    article_text = item.div.div.next_sibling

                if item.div.div.next_sibling.next_sibling:
                    article_extra = item.div.div.next_sibling.next_sibling

            # cleanup article
            article = build_article(article_text, article_extra)

            article_title = article_byline
            if not article_title or article_title == article_author:
                article_title = build_title(article_text)
            # get event title
            elif 'an event' in article_title:
                article_title = article_extra.find('h3').get_text(strip=True)


            items.append({
                'url': url,
                'title': article_title,
                'article': article,
                'date': date,
                'author': article_author
            })

        logger.debug('%s posts found', len(items))

        return items
    # else
    return None
