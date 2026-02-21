import requests
from bs4 import BeautifulSoup
import re
import os
import time

# --- 配置区 ---
# 最终生成的单个大文档名称
MEGA_LAW_FILE = "2026年度法律法规全集.md"
# 防止重复抓取的历史记录
HISTORY_FILE = "processed_links.txt"

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

def fetch_full_text(url):
    """解析各官方页面的正文"""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.encoding = 'utf-8'
        soup = BeautifulSoup(resp.text, 'html.parser')
        # 匹配多种可能的正文标签
        body = soup.select_one('#p_content') or soup.select_one('.pages_content') or \
               soup.select_one('.txt_con') or soup.select_one('#UCAP-CONTENT') or \
               soup.select_one('.article-content')
        if body:
            for s in body(['script', 'style']): s.decompose()
            return body.get_text(separator="\n\n").strip()
        return "无法自动提取正文，请查阅原链接。"
    except:
        return "抓取异常。"

def get_latest_data():
    """获取政府网和最高法的数据源"""
    tasks = [
        {"name": "中国政府网", "url": "https://www.gov.cn/zhengce/zuixin.htm", "prefix": "https://www.gov.cn"},
        {"name": "最高人民法院", "url": "https://www.court.gov.cn/fabu/gengduo/16.html", "prefix": "https://www.court.gov.cn"}
    ]
    
    laws_to_process = []
    
    for task in tasks:
        try:
            print(f"🔍 正在扫描: {task['name']}")
            resp = requests.get(task['url'], headers=HEADERS, timeout=15)
            resp.encoding = 'utf-8'
            soup = BeautifulSoup(resp.text, 'html.parser')
            
            # 兼容不同页面的列表提取逻辑
            links = soup.find_all('a', href=True)
            for link in links:
                title = link.get_text(strip=True)
                href = link['href']
                
                # 关键词筛选：法律、条例、规定、办法、意见、方案、解释、决定
                if any(kw in title for kw in ["法律", "条例", "规定", "办法", "意见", "方案", "解释", "决定"]):
                    full_url = href if href.startswith('http') else task['prefix'] + href
                    if "/zhengce/" in full_url or "/fabu/" in full_url: # 过滤无关链接
                        laws_to_process.append({'title': title, 'url': full_url, 'source': task['name']})
        except Exception as e:
            print(f"扫描 {task['name']} 出错: {e}")
            
    return laws_to_process

def main():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, 'r') as f:
            history = set(f.read().splitlines())
    else:
        history = set()

    laws = get_latest_data()
    new_sections = ""
    current_date = time.strftime("%Y-%m-%d")

    for law in laws:
        if law['url'] not in history:
            print(f"✨ 发现新内容: {law['title']}")
            text = fetch_full_text(law['url'])
            
            # 缝合区块格式
            section = f"\n# {law['title']}\n"
            section += f"- **抓取日期**: {current_date}\n"
            section += f"- **来源渠道**: {law['source']}\n"
            section += f"- **原文链接**: {law['url']}\n\n"
            section += f"{text}\n"
            section += "\n---\n"
            
            new_sections += section
            history.add(law['url'])
            # 写入历史防止下次重复
            with open(HISTORY_FILE, 'a') as f:
                f.write(law['url'] + "\n")
            time.sleep(1) # 礼貌间隔

    if new_sections:
        old_content = ""
        if os.path.exists(MEGA_LAW_FILE):
            with open(MEGA_LAW_FILE, 'r', encoding='utf-8') as f:
                old_content = f.read()
        
        # 将新抓到的缝合在最前面（置顶最新）
        with open(MEGA_LAW_FILE, 'w', encoding='utf-8') as f:
            f.write(f"# 法律法规动态更新索引（更新于 {current_date}）\n\n" + new_sections + old_content)
        print(f"✅ 缝合完成！已更新至 {MEGA_LAW_FILE}")
    else:
        print("☕ 今天暂无新发布的法规条文。")

if __name__ == "__main__":
    main()
