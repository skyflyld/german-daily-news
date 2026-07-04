#!/usr/bin/env python3
"""Lithium Data — 锂产业价格及动态采集
GitHub Actions US/EU runners → access to TradingEconomics & global data sources.
Output: lithium-data/YYYY/MM/YYYY-MM-DD.md
"""
import urllib.request
import json
import os
from datetime import datetime

def fetch_json(url, timeout=15):
    try:
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0',
            'Accept': 'application/json'
        })
        resp = urllib.request.urlopen(req, timeout=timeout)
        return resp.read().decode('utf-8', errors='replace')
    except Exception as e:
        return None

def fetch_tradingeconomics():
    """Fetch lithium price from TradingEconomics scrape page"""
    try:
        req = urllib.request.Request(
            'https://tradingeconomics.com/commodity/lithium',
            headers={'User-Agent': 'Mozilla/5.0'}
        )
        resp = urllib.request.urlopen(req, timeout=15)
        html = resp.read().decode('utf-8', errors='replace')
        
        # Try to extract price from common patterns
        import re
        # Pattern: price in a table cell near "Lithium"
        price_match = re.search(r'(\d[\d,]+\.?\d*)\s*(CNY|USD|元)', html[:50000])
        change_match = re.search(r'([+-]?\d+\.?\d*%?)', html[5000:6000])
        
        result = {'source': 'TradingEconomics'}
        if price_match:
            result['price'] = price_match.group(1)
        return result
    except Exception as e:
        return {'source': 'TradingEconomics', 'error': str(e)}

def fetch_google_finance():
    """Fetch lithium-related financial data"""
    try:
        # Use a public API for lithium price data
        req = urllib.request.Request(
            'https://www.gfmag.com/commodities/lithium',
            headers={'User-Agent': 'Mozilla/5.0'}
        )
        resp = urllib.request.urlopen(req, timeout=15)
        html = resp.read().decode('utf-8', errors='replace')
        return {'source': 'GFMag', 'fetched': True}
    except Exception as e:
        return {'source': 'GFMag', 'error': str(e)}

def fetch_investing_com():
    """Try investing.com lithium data"""
    try:
        req = urllib.request.Request(
            'https://www.investing.com/commodities/lithium-carbonate-futures',
            headers={'User-Agent': 'Mozilla/5.0', 'Accept': 'text/html'}
        )
        resp = urllib.request.urlopen(req, timeout=15)
        html = resp.read().decode('utf-8', errors='replace')
        return {'source': 'Investing.com', 'fetched': True}
    except Exception as e:
        return {'source': 'Investing.com', 'error': str(e)}

def generate_markdown(sources, today):
    lines = []
    lines.append(f'# ⚡ 锂产业数据 — {today.strftime("%Y年%m月%d日")}')
    lines.append(f'# Lithium Market Data — {today.strftime("%A, %B %d, %Y")}')
    lines.append('')
    lines.append('---')
    lines.append('')
    
    lines.append('## 📊 数据源状态')
    lines.append('')
    for name, data in sources.items():
        status = '✅' if 'error' not in data else '❌'
        detail = data.get('price', data.get('fetched', data.get('error', '?')))
        lines.append(f'| {status} | {name} | {detail} |')
    lines.append('')
    lines.append('---')
    lines.append('')
    
    lines.append('## 📈 核心数据')
    lines.append('')
    lines.append('| 品种 | 价格 | 变动 | 数据源 |')
    lines.append('|------|------|------|--------|')
    lines.append(f'| 碳酸锂 99.5% Li₂CO₃ | — | — | TradingEconomics (采集确认中) |')
    lines.append(f'| 碳酸锂期货 | — | — | Investing.com (采集确认中) |')
    lines.append('')
    lines.append('---')
    lines.append(f'*📡 自动采集于 {today.strftime("%Y-%m-%d %H:%M UTC")}*')
    lines.append('')
    return '\n'.join(lines)

def main():
    today = datetime.utcnow()
    year = today.strftime('%Y')
    month = today.strftime('%m')
    day = today.strftime('%d')
    
    out_dir = f'lithium-data/{year}/{month}'
    os.makedirs(out_dir, exist_ok=True)
    out_path = f'{out_dir}/{year}-{month}-{day}.md'
    
    print(f'⚡ Fetching lithium data for {year}-{month}-{day}...')
    
    sources = {
        'TradingEconomics': fetch_tradingeconomics(),
        'GFMag': fetch_google_finance(),
        'Investing.com': fetch_investing_com(),
    }
    
    for name, data in sources.items():
        if 'error' in data:
            print(f'  ❌ {name}: {data["error"]}')
        elif 'price' in data:
            print(f'  ✅ {name}: price={data["price"]}')
        else:
            print(f'  ✅ {name}: fetched')
    
    md = generate_markdown(sources, today)
    
    with open(out_path, 'w') as f:
        f.write(md)
    print(f'✅ Written to {out_path} ({len(md)} chars)')

if __name__ == '__main__':
    main()
