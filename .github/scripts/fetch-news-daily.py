#!/usr/bin/env python3
"""News Daily — 经济·科技·市场新闻采集
GitHub Actions US/EU runners → no GFW restrictions.
Output: news-daily/YYYY/MM/YYYY-MM-DD.md
"""
import urllib.request
import xml.etree.ElementTree as ET
import json
import os
from datetime import datetime
from html.parser import HTMLParser

class MLStripper(HTMLParser):
    def __init__(self):
        super().__init__()
        self.reset()
        self.strict = False
        self.convert_charrefs = True
        self.text = []
    def handle_data(self, d):
        self.text.append(d)
    def get_data(self):
        return ''.join(self.text)

def strip_html(html):
    s = MLStripper()
    s.feed(html)
    return s.get_data()

def fetch_rss(url, timeout=15):
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        resp = urllib.request.urlopen(req, timeout=timeout)
        return resp.read().decode('utf-8', errors='replace')
    except Exception as e:
        return None

def parse_rss_items(xml_text, max_items=10):
    if not xml_text:
        return []
    items = []
    try:
        root = ET.fromstring(xml_text)
        # RSS 2.0
        for item in root.iter('item'):
            title = item.findtext('title', '')
            link = item.findtext('link', '')
            desc = item.findtext('description', '')
            pubdate = item.findtext('pubDate', '')
            items.append({
                'title': strip_html(title).strip(),
                'link': link.strip(),
                'desc': strip_html(desc).strip()[:200],
                'date': pubdate
            })
            if len(items) >= max_items:
                break
        # Atom
        if not items:
            ns = {'atom': 'http://www.w3.org/2005/Atom'}
            for entry in root.iter('{http://www.w3.org/2005/Atom}entry'):
                title = entry.findtext('atom:title', '', ns)
                link_el = entry.find('atom:link', ns)
                link = link_el.get('href', '') if link_el is not None else ''
                summary = entry.findtext('atom:summary', '', ns)
                updated = entry.findtext('atom:updated', '', ns)
                items.append({
                    'title': strip_html(title).strip(),
                    'link': link.strip(),
                    'desc': strip_html(summary).strip()[:200],
                    'date': updated
                })
                if len(items) >= max_items:
                    break
    except ET.ParseError:
        pass
    return items

def fetch_all_news():
    sources = [
        ('📈 Bloomberg Markets', 'https://feeds.bloomberg.com/markets/news.rss'),
        ('🏢 Bloomberg Economics', 'https://feeds.bloomberg.com/economics/news.rss'),
        ('💻 Bloomberg Tech', 'https://feeds.bloomberg.com/technology/news.rss'),
        ('🌐 Reuters Top News', 'https://www.reutersagency.com/feed/?best-topics=business-finance&post_type=best'),
        ('📊 MarketWatch', 'https://feeds.marketwatch.com/marketwatch/topstories'),
        ('💰 Financial Times', 'https://www.ft.com/news-feed'),
        ('🔬 Ars Technica', 'https://feeds.arstechnica.com/arstechnica/index'),
    ]
    results = {}
    for name, url in sources:
        xml = fetch_rss(url)
        items = parse_rss_items(xml, max_items=8)
        results[name] = items
        if items:
            print(f'  ✅ {name}: {len(items)} items')
        else:
            print(f'  ❌ {name}: no data')
    return results

def generate_markdown(results, today):
    lines = []
    lines.append(f'# 📰 每日新闻摘要 — {today.strftime("%Y年%m月%d日")}')
    lines.append(f'# Daily News Digest — {today.strftime("%A, %B %d, %Y")}')
    lines.append('')
    lines.append('---')
    lines.append('')
    
    total_items = 0
    for source_name, items in results.items():
        if not items:
            continue
        lines.append(f'## {source_name}')
        lines.append('')
        for item in items[:8]:
            title = item['title'] or '(无标题)'
            lines.append(f'- **{title}**')
            if item['desc']:
                lines.append(f'  {item["desc"]}')
            lines.append('')
        total_items += len(items)
    
    lines.append('---')
    lines.append(f'*📡 自动采集于 {today.strftime("%Y-%m-%d %H:%M UTC")}*')
    lines.append(f'*📊 共 {total_items} 条*')
    lines.append('')
    return '\n'.join(lines)

def main():
    today = datetime.utcnow()
    year = today.strftime('%Y')
    month = today.strftime('%m')
    day = today.strftime('%d')
    
    out_dir = f'news-daily/{year}/{month}'
    os.makedirs(out_dir, exist_ok=True)
    out_path = f'{out_dir}/{year}-{month}-{day}.md'
    
    print(f'📰 Fetching news for {year}-{month}-{day}...')
    results = fetch_all_news()
    md = generate_markdown(results, today)
    
    with open(out_path, 'w') as f:
        f.write(md)
    print(f'✅ Written to {out_path} ({len(md)} chars)')

if __name__ == '__main__':
    main()
