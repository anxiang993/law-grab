import requests
from bs4 import BeautifulSoup
import re
import os
import time

# --- 配置区 ---
DATA_DIR = "./integrated_laws"  # 整合后的库路径
HISTORY_FILE = "processed_links.txt"
os.makedirs(DATA_DIR, exist_ok=True)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

# --- 核心逻辑 1：识别“母法”名称 ---
def get_base_law_name(title):
    # 提取书名号内容，如《中华人民共和国公司法》
    match = re.search(r'《([^》]+)》', title)
    if match:
        name = match.group(1)
        # 进一步精简，提取核心法律名
        core_match = re.search(r'关于适用(.+?)的', name)
        return core_match.group(1) if core_match else name
    # 兜底：去掉常见行政词汇，取前15个字
    clean_title = re.sub(r'关于|的通知|的意见|的公告|的规定|的办法', '', title)
    return clean_title[:15].strip()

# --- 核心逻辑 2：抓取特定网页的正文 ---
def fetch_full_text(url):
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.encoding = 'utf-8'
        soup = BeautifulSoup(resp.text, 'html.parser')
        # 兼容政府网和最高法的常见正文标签
        body = soup.select_one('#p_content') or soup.select_one('.pages_content') or soup.select_one('.txt_con') or soup.select_one('#UCAP-CONTENT')
        if body:
            # 移除脚本和样式
            for s in body(['script', 'style']): s.decompose()
            return body.get_text(separator="\n\n").strip()
        return "无法自动提取正文，请点击链接查阅原文。"
    except Exception as e:
        return f"抓取异常: {str(e)}"

# --- 核心逻辑 3：抓取政府网最新政策 ---
def fetch_gov_laws():
    url = "https://www.gov.cn/zhengce/zuixin.htm"
    results = []
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.encoding = 'utf-8'
        soup = BeautifulSoup(resp.text, 'html.parser')
        items = soup.select('.list.list_1.list_2 li')
        for item in items:
            link_tag = item.find('a')
            if not link_tag: continue
            title = link_tag.text.strip()
            date = item.find('span').text.strip() if item.find('span') else "0000-00-00"
            link = "https://www.gov.cn" + link_tag['href'] if link_tag['href'].startswith('/') else link_tag['href']
            
            # 宽松过滤：包含 法律、条例、规定、办法、意见、通知、解释 的都抓取
            if any(kw in title for kw in ["法律", "条例", "规定", "办法", "意见", "通知", "解释"]):
                results.append({
                    'title': title, 'date': date, 'link': link, 'category': '政策法规'
                })
    except Exception as e:
        print(f"政府网抓取失败: {e}")
    return results

# --- 核心逻辑 4：整合合并文件 ---
def integrate_content(law_item):
    base_name = get_base_law_name(law_item['title'])
    file_path = os.path.join(DATA_DIR, f"{base_name}.md")
    
    # 识别废止信号
    if any(kw in law_item['title'] for kw in ["废止", "失效"]):
        if os.path.exists(file_path):
            os.rename(file_path, file_path + f".bak_已失效_{law_item['date']}")
            return

    full_text = fetch_full_text(law_item['link'])
    
    # 构建新区块
    new_section = f"\n\n## [{law_item['date']}] {law_item['category']}: {law_item['title']}\n"
    new_section += f"原文链接: {law_item['link']}\n\n"
    new_section += f"{full_text}\n"
    new_section += "\n---\n"

    # 如果文件已存在，则追加内容；不存在则创建
    if os.path.exists(file_path):
        with open(file_path, 'a', encoding='utf-8') as f:
            f.write(new_section)
    else:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(f"# {base_name} 集成库\n" + new_section)

# --- 主程序 ---
def main():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, 'r') as f:
            history = set(f.read().splitlines())
    else:
        history = set()

    print("🚀 开始扫描最新法律法规...")
    laws = fetch_gov_laws()
    
    count = 0
    for law in laws:
        if law['link'] not in history:
            print(f"正在同步: {law['title']}")
            integrate_content(law)
            with open(HISTORY_FILE, 'a') as f:
                f.write(law['link'] + "\n")
            count += 1
            time.sleep(1) # 礼貌抓取
            
    print(f"✅ 同步完成，本次更新 {count} 条内容。")

if __name__ == "__main__":
    main()
