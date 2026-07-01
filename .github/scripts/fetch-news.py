#!/usr/bin/env python3
"""
German Daily News Fetcher & Bilingual Report Generator
Runs in GitHub Actions (US/EU runners, no GFW restrictions)
Fetches from German sources → generates YYYY/MM/YYYY-MM-DD.md bilingual report
"""

import urllib.request
import urllib.error
import xml.etree.ElementTree as ET
import json
import re
import os
import sys
from datetime import datetime, timezone, timedelta
from html import unescape
from email.utils import parsedate_to_datetime

# ── Sources ──────────────────────────────────────────────────────────
SOURCES = [
    {
        'name': 'Tagesschau',
        'url': 'https://www.tagesschau.de/api2/news/',
        'type': 'json',
        'path': ['news',],
        'title_field': ['title',],
        'desc_field': ['firstSentence',],
        'date_field': ['date',],
    },
    {
        'name': 'Spiegel',
        'url': 'https://www.spiegel.de/schlagzeilen/index.rss',
        'type': 'rss',
    },
    {
        'name': 'FAZ',
        'url': 'https://www.faz.net/rss/aktuell/',
        'type': 'rss',
    },
    {
        'name': 'Zeit',
        'url': 'https://newsfeed.zeit.de/index',
        'type': 'rss',
    },
    {
        'name': 'Welt',
        'url': 'https://www.welt.de/feeds/latest.rss',
        'type': 'rss',
    },
    {
        'name': 'SZ',
        'url': 'https://www.sueddeutsche.de/rss/aktuell',
        'type': 'rss',
    },
    {
        'name': 'Handelsblatt',
        'url': 'https://www.handelsblatt.com/contentimport/export/rss.xml',
        'type': 'rss',
    },
]

# ── Category keywords (DE → EN/CN) ──────────────────────────────────
CATEGORIES = {
    '💶 经济': [
        'wirtschaft', 'bip', 'inflation', 'konjunktur', 'dax', 'industrie',
        'arbeitsmarkt', 'steuer', 'haushalt', 'finanz', 'bank', 'zins',
        'ifo', 'diw', 'iwh', 'prognose', 'wachstum', 'rezession',
        'preis', 'energiekosten', 'investition', 'export', 'handel',
    ],
    '🏛️ 政治': [
        'politik', 'bundesregierung', 'bundestag', 'koalition', 'wahl',
        'gesetz', 'partei', 'kanzler', 'minister', 'cdu', 'spd', 'fdp',
        'grüne', 'afd', 'linke', 'demokratie', 'europa', 'eu',
    ],
    '⚽ 足球·体育': [
        'fußball', 'wm', 'bundesliga', 'dfb', 'nationalmannschaft',
        'sport', 'tennis', 'olympia', 'meister', 'trainer', 'spieler',
        'nagelsmann', 'bayern', 'dortmund',
    ],
    '🤖 AI·科技': [
        'ki', 'künstliche intelligenz', 'artificial intelligence', 'ai',
        'digital', 'software', 'algorithmus', 'chatbot', 'chatgpt',
        'claude', 'openai', 'daten', 'cyber', 'sicherheit',
    ],
    '🚗 汽车': [
        'auto', 'automobil', 'vw', 'volkswagen', 'mercedes', 'bmw',
        'audi', 'porsche', 'elektro', 'e-auto', 'verbrenner',
        'mobilität', 'lade', 'akk', 'batterie',
    ],
    '⚡ 能源·气候': [
        'energie', 'strom', 'gas', 'erneuerbare', 'klima', 'umwelt',
        'co2', 'kohle', 'wasserstoff', 'solar', 'wind', 'heizung',
        'atom', 'strompreis', 'netz', 'emission',
    ],
    '📚 文学·文化': [
        'literatur', 'buch', 'autor', 'verlag', 'bibliothek', 'roman',
        'gedicht', 'preis', 'auszeichnung', 'kultur', 'museum',
        'theater', 'film', 'musik', 'kunst',
    ],
    '🧠 哲学·思想': [
        'philosophie', 'denker', 'idealismus', 'hegel', 'kant',
        'nietzsche', 'habermas', 'adorno', 'frankfurt', 'schule',
        'theorie', 'ethik', 'aufklärung',
    ],
    '🎓 教育·研究': [
        'bildung', 'schule', 'universität', 'studium', 'forschung',
        'student', 'lehrer', 'ausbildung', 'wissenschaft', 'hochschule',
        'semester', 'examen', 'stipendium',
    ],
    '🔬 科学·医学': [
        'wissenschaft', 'forschung', 'studie', 'medizin', 'technik',
        'physik', 'chemie', 'biologie', 'gen', 'impf', 'krankheit',
        'gesundheit', 'klinik', 'patient',
    ],
    '🛡️ 防务·安全': [
        'verteidigung', 'bundeswehr', 'nato', 'rüstung', 'militär',
        'soldat', 'waffe', 'einsatz', 'panzer', 'waffen',
        'geheimdienst', 'sicherheit', 'bedrohung',
    ],
    '🌍 国际·外交': [
        'international', 'außenpolitik', 'diplomatie', 'ausland',
        'usa', 'china', 'russland', 'ukraine', 'iran', 'israel',
        'krieg', 'konflikt', 'frieden', 'vereinte nationen', 'uno',
    ],
}

# ── Common German→Chinese term translations ─────────────────────────
TERM_DICT = {
    'Bundesregierung': '联邦政府',
    'Bundestag': '联邦议院',
    'Bundeskanzler': '联邦总理',
    'Wirtschaft': '经济',
    'Inflation': '通胀',
    'BIP': 'GDP',
    'ifo-Geschäftsklimaindex': 'ifo商业景气指数',
    'Zins': '利率',
    'Arbeitsmarkt': '就业市场',
    'Klima': '气候',
    'erneuerbare Energien': '可再生能源',
    'Digitalisierung': '数字化',
    'Bundeswehr': '联邦国防军',
    'Gesundheit': '健康',
    'Bildung': '教育',
    'Forschung': '研究',
    'Steuer': '税收',
    'Strompreis': '电价',
    'Wasserstoff': '氢能',
}

def fetch_url(url, timeout=15):
    """Fetch a URL with User-Agent header."""
    headers = {'User-Agent': 'Mozilla/5.0 (compatible; GermanNewsBot/1.0)'}
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
            # Try UTF-8 first, fall back to ISO-8859-1
            try:
                return raw.decode('utf-8')
            except UnicodeDecodeError:
                return raw.decode('iso-8859-1')
    except Exception as e:
        print(f"  ⚠️  {url[:60]}: {str(e)[:60]}", file=sys.stderr)
        return None

def parse_date(date_str):
    """Parse various date formats."""
    if not date_str:
        return None
    try:
        return parsedate_to_datetime(date_str)
    except:
        pass
    try:
        return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
    except:
        pass
    return None

def clean_html(html_text):
    """Remove HTML tags and decode entities."""
    text = re.sub(r'<[^>]+>', ' ', html_text)
    text = re.sub(r'\s+', ' ', text)
    text = unescape(text)
    return text.strip()

def extract_rss_items(content):
    """Parse RSS feed and return articles."""
    articles = []
    try:
        root = ET.fromstring(content)
        # RSS 2.0 namespace
        ns = {'': 'http://purl.org/rss/1.0/',
              'dc': 'http://purl.org/dc/elements/1.1/',
              'content': 'http://purl.org/rss/1.0/modules/content/'}
        
        # Try standard RSS 2.0 items
        for item in root.iter('item'):
            title = ''
            link = ''
            desc = ''
            pub_date = None
            
            title_el = item.find('title')
            if title_el is not None and title_el.text:
                title = clean_html(title_el.text)
            
            link_el = item.find('link')
            if link_el is not None and link_el.text:
                link = link_el.text.strip()
            
            desc_el = item.find('description')
            if desc_el is not None and desc_el.text:
                desc = clean_html(desc_el.text[:400])
            
            date_el = item.find('pubDate')
            if date_el is not None and date_el.text:
                pub_date = parse_date(date_el.text)
            
            if title:
                articles.append({
                    'title': title,
                    'link': link,
                    'summary': desc,
                    'date': pub_date,
                })
        
        # If no items found via standard method, try RSS 1.0 / atom
        if not articles:
            for entry in root.iter('{http://www.w3.org/2005/Atom}entry'):
                title = ''
                link = ''
                desc = ''
                pub_date = None
                
                title_el = entry.find('{http://www.w3.org/2005/Atom}title')
                if title_el is not None and title_el.text:
                    title = clean_html(title_el.text)
                
                link_el = entry.find('{http://www.w3.org/2005/Atom}link')
                if link_el is not None:
                    link = link_el.get('href', '')
                
                desc_el = entry.find('{http://www.w3.org/2005/Atom}summary')
                if desc_el is not None and desc_el.text:
                    desc = clean_html(desc_el.text[:400])
                
                date_el = entry.find('{http://www.w3.org/2005/Atom}updated')
                if date_el is not None and date_el.text:
                    pub_date = parse_date(date_el.text)
                
                if title:
                    articles.append({
                        'title': title,
                        'link': link,
                        'summary': desc,
                        'date': pub_date,
                    })
    except Exception as e:
        print(f"  ⚠️  RSS parse error: {e}", file=sys.stderr)
    
    return articles

def extract_json_items(content, source):
    """Parse JSON API response."""
    articles = []
    try:
        data = json.loads(content)
        # Navigate path
        for key in source.get('path', []):
            if isinstance(data, dict):
                data = data.get(key, {})
            else:
                return articles
        
        if isinstance(data, list):
            items = data
        elif isinstance(data, dict):
            # Try common keys
            items = data.get('items', data.get('articles', data.get('results', [])))
        else:
            items = []
        
        for item in items:
            if isinstance(item, dict):
                title = ''
                for key in source.get('title_field', ['title']):
                    title = item.get(key, '')
                    if title: break
                
                desc = ''
                for key in source.get('desc_field', ['description']):
                    desc = item.get(key, '')
                    if desc: break
                
                date_str = ''
                for key in source.get('date_field', ['date', 'pubDate']):
                    date_str = item.get(key, '')
                    if date_str: break
                
                link = item.get('link', item.get('url', ''))
                
                if title:
                    articles.append({
                        'title': clean_html(str(title)),
                        'link': str(link),
                        'summary': clean_html(str(desc)[:400]),
                        'date': parse_date(date_str),
                    })
    except Exception as e:
        print(f"  ⚠️  JSON parse error: {e}", file=sys.stderr)
    
    return articles

def classify_article(title, summary):
    """Classify article into categories. Returns list of category names."""
    text = (title + ' ' + (summary or '')).lower()
    matched = []
    for cat_name, keywords in CATEGORIES.items():
        for kw in keywords:
            if kw in text:
                matched.append(cat_name)
                break  # One match per category
    # If no keyword match, try title word-level matching
    if not matched:
        words = set(re.findall(r'\b[a-zäöüß]{3,}\b', text))
        for cat_name, keywords in CATEGORIES.items():
            if words & set(kw.lower() for kw in keywords):
                matched.append(cat_name)
    return matched if matched else ['📰 其他']

def translate_summary_german(text, max_words=90):
    """Generate a simple rough Chinese summary for a German text."""
    # Just truncate and note it's German original
    # Full translation will be done by Ariste when reading
    return text[:200]

def get_today():
    """Get today's date in Berlin timezone."""
    berlin_tz = timezone(timedelta(hours=2))  # CEST (summer)
    # Actually just use UTC+2 for simplicity
    now = datetime.now(timezone.utc) + timedelta(hours=2)
    return now

def main():
    today = get_today()
    date_str = today.strftime('%Y-%m-%d')
    weekday_cn = ['星期一', '星期二', '星期三', '星期四', '星期五', '星期六', '星期日'][today.weekday()]
    weekday_de = ['Montag', 'Dienstag', 'Mittwoch', 'Donnerstag', 'Freitag', 'Samstag', 'Sonntag'][today.weekday()]
    year = today.strftime('%Y')
    month = today.strftime('%m')
    
    print(f"🇩🇪 German News Fetch — {date_str}")
    print(f"📡 Sources: {len(SOURCES)}")
    
    # ── Fetch all sources ──
    all_articles = []
    for source in SOURCES:
        print(f"  🔄 {source['name']}...", end=' ')
        content = fetch_url(source['url'])
        if not content:
            print('❌')
            continue
        
        if source['type'] == 'rss':
            articles = extract_rss_items(content)
        elif source['type'] == 'json':
            articles = extract_json_items(content, source)
        else:
            articles = []
        
        print(f"✅ {len(articles)} articles")
        for a in articles:
            a['source'] = source['name']
        all_articles.extend(articles)
    
    # Deduplicate by headline similarity
    seen_titles = set()
    unique_articles = []
    for a in all_articles:
        title_key = a['title'][:60].lower().strip()
        if title_key not in seen_titles:
            seen_titles.add(title_key)
            unique_articles.append(a)
    
    print(f"\n📊 Total: {len(all_articles)} → {len(unique_articles)} unique")
    
    # ── Classify ──
    categorized = {}
    for a in unique_articles:
        cats = classify_article(a['title'], a.get('summary', ''))
        for cat in cats:
            if cat not in categorized:
                categorized[cat] = []
            categorized[cat].append(a)
    
    # Remove '其他' if we have plenty in other categories
    if '📰 其他' in categorized and len(categorized) > 5:
        others = categorized.pop('📰 其他')
        # Try to reassign
        for a in others[:5]:
            for cat in list(categorized.keys())[:3]:
                categorized[cat].append(a)
                break
    
    # Sort categories
    cat_order = [
        '💶 经济', '🏛️ 政治', '🌍 国际·外交', '🤖 AI·科技', '🚗 汽车',
        '⚡ 能源·气候', '⚽ 足球·体育', '🛡️ 防务·安全',
        '📚 文学·文化', '🧠 哲学·思想', '🎓 教育·研究', '🔬 科学·医学', '📰 其他'
    ]
    
    # Cap articles per category
    for cat in categorized:
        categorized[cat] = categorized[cat][:5]  # Max 5 per category
    
    # ── Generate report ──
    lines = []
    lines.append(f"# 🗞️ 德国每日新闻双语速报")
    lines.append(f"# Täglicher deutscher Nachrichtenüberblick (zweisprachig)")
    lines.append(f"")
    lines.append(f"**📅 {date_str}（{weekday_cn}） | {weekday_de}, {today.strftime('%d. %B %Y')}**")
    lines.append(f"")
    lines.append(f"---")
    lines.append(f"")
    
    article_count = 0
    for cat in cat_order:
        if cat not in categorized:
            continue
        articles = categorized[cat]
        
        lines.append(f"## {cat}")
        lines.append(f"")
        
        for i, a in enumerate(articles, 1):
            title = a['title']
            summary = a.get('summary', '')
            source_name = a.get('source', '')
            
            lines.append(f"**{'❶❷❸❹❺'[i-1] if i <= 5 else f'{i}.'} {title}**")
            if summary:
                lines.append(f"_{source_name}_ · {summary[:300]}")
            lines.append(f"")
            article_count += 1
        
        lines.append(f"---")
        lines.append(f"")
    
    # Source info
    active_sources = list(dict.fromkeys(a.get('source', '') for a in unique_articles))
    lines.append(f"*📡 Quellen: {' · '.join(active_sources)}*")
    lines.append(f"*🦞 Automatisch erfasst am {today.strftime('%d.%m.%Y um %H:%M')} MESZ*")
    lines.append(f"")
    
    report = '\n'.join(lines)
    
    # ── Write file ──
    output_dir = f"{year}/{month}"
    os.makedirs(output_dir, exist_ok=True)
    
    output_path = f"{output_dir}/{date_str}.md"
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"\n✅ Report: {output_path}")
    print(f"📊 Articles: {article_count}")
    print(f"📂 Categories: {len(categorized)}")
    
    # ── Update README index ──
    readme_path = 'README.md'
    
    # German month names
    month_names_de = {
        '01': 'Januar', '02': 'Februar', '03': 'März', '04': 'April',
        '05': 'Mai', '06': 'Juni', '07': 'Juli', '08': 'August',
        '09': 'September', '10': 'Oktober', '11': 'November', '12': 'Dezember'
    }
    month_names_cn = {
        '01': '一月', '02': '二月', '03': '三月', '04': '四月',
        '05': '五月', '06': '六月', '07': '七月', '08': '八月',
        '09': '九月', '10': '十月', '11': '十一月', '12': '十二月'
    }
    month_de = month_names_de.get(month, month)
    month_cn = month_names_cn.get(month, month)
    entry_link = f"  - [{today.strftime('%d.')} {month_de}]({year}/{month}/{date_str}.md)"
    month_header = f"### {month_de} · {month_cn}"
    
    if os.path.exists(readme_path):
        with open(readme_path, 'r', encoding='utf-8') as f:
            readme = f.read()
        
        if f"]/{date_str}.md)" in readme:
            print(f"⚠️  Entry {date_str} already in README")
        else:
            if month_header in readme:
                # Add after the month header line
                lines_r = readme.split('\n')
                new_lines = []
                added = False
                for i, line in enumerate(lines_r):
                    new_lines.append(line)
                    if line.strip() == month_header and not added:
                        new_lines.append(entry_link)
                        added = True
                if added:
                    readme = '\n'.join(new_lines)
            else:
                # Add new month section before the separator line
                separator_idx = readme.find('\n---\n')
                if separator_idx > 0:
                    insertion = f"\n{month_header}\n{entry_link}\n"
                    readme = readme[:separator_idx] + insertion + readme[separator_idx:]
                else:
                    readme += f"\n{month_header}\n{entry_link}\n"
        
        with open(readme_path, 'w', encoding='utf-8') as f:
            f.write(readme)
        print(f"✅ README index updated")
    
    print(f"\n🎉 Done!")

if __name__ == '__main__':
    main()
