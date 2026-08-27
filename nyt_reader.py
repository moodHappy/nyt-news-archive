import requests
from bs4 import BeautifulSoup
import os
import json
import subprocess
from datetime import datetime, timezone, timedelta

BASE_DIR = "docs"
tz_utc_8 = timezone(timedelta(hours=8))
AUTO_PUSH_GITHUB = True  # 开启 Python 端自动 Push 到 GitHub 的功能

def fetch_nyt_news():
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }

    print("正在解析 纽约时报中文网 首页...")
    try:
        response = requests.get("https://cn.nytimes.com/", headers=headers, timeout=15)
        response.encoding = 'utf-8'
        soup = BeautifulSoup(response.text, 'html.parser')

        article_url = None
        for a_tag in soup.find_all('a', href=True):
            href = a_tag['href']
            if href.startswith('/') and len(href.split('/')) > 3:
                if not href.startswith('/video/') and not href.startswith('/podcasts/') and 'index.html' not in href:
                    article_url = "https://cn.nytimes.com" + href
                    break

        if not article_url:
            print("未找到文章链接。")
            return False

        record_file = "last_nyt_url.txt"
        last_url = ""
        if os.path.exists(record_file):
            with open(record_file, "r") as f:
                last_url = f.read().strip()

        if article_url == last_url:
            print("头条未更新，本次不生成新文章。")
            return False

        print(f"发现新突发头条: {article_url}")
        with open(record_file, "w") as f:
            f.write(article_url)

        art_res = requests.get(article_url, headers=headers, timeout=15)
        art_res.encoding = 'utf-8'
        art_soup = BeautifulSoup(art_res.text, 'html.parser')

        zh_title = ""
        en_title = ""

        title_tags = art_soup.find_all('h1')
        valid_h1s = [h for h in title_tags if 'logo' not in h.get('class', []) and len(h.text.strip()) > 2]

        if valid_h1s:
            zh_node = next((h for h in valid_h1s if 'en-title' not in h.get('class', [])), None)
            en_node = next((h for h in valid_h1s if 'en-title' in h.get('class', [])), None)

            if zh_node and en_node:
                zh_title = zh_node.text.strip()
                en_title = en_node.text.strip()
            elif len(valid_h1s) >= 2:
                zh_title = valid_h1s[0].text.strip()
                en_title = valid_h1s[1].text.strip()
            else:
                en_title = valid_h1s[0].text.strip()

        if not en_title:
            meta_og = art_soup.find('meta', property='og:title')
            if meta_og and meta_og.get('content'):
                en_title = meta_og['content'].strip()
            else:
                en_title = "NYT Chinese News"

        en_title = en_title.replace(' - 纽约时报中文网', '').strip()
        if zh_title:
            zh_title = zh_title.replace(' - 纽约时报中文网', '').strip()

        page_title = en_title
        display_h1 = f"{zh_title}<br>{en_title}" if zh_title else en_title

        now = datetime.now(tz_utc_8)
        current_time = now.strftime("%Y-%m-%d %H:%M")

        paragraphs = art_soup.find_all('p')
        content_paragraphs = []

        for p in paragraphs:
            text = p.text.strip()
            if len(text) <= 5: continue
            if "版权所有" in text and "纽约时报" in text: continue
            if "未经许可，" in text: continue
            if "欢迎在" in text and "关注我们" in text: continue
            content_paragraphs.append(text)

        if content_paragraphs:
            save_article(page_title, display_h1, content_paragraphs, current_time, article_url, now)
            return True
        else:
            print("未提取到有效正文段落。")
            return False

    except Exception as e:
        print(f"抓取错误: {e}")
        return False

def save_article(page_title, display_h1, paragraphs, pub_date, article_url, now_obj):
    year_str, month_str = str(now_obj.year), str(now_obj.month)

    target_dir = os.path.join(BASE_DIR, year_str, month_str)
    os.makedirs(target_dir, exist_ok=True)

    filename = f"{now_obj.year}_{now_obj.month}_{now_obj.day}_{now_obj.strftime('%H%M')}.html"
    html_path = os.path.join(target_dir, filename)

    p_tags = "\n".join([f"<p>{p}</p>" for p in paragraphs])

    html_content = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{page_title}</title>
    <style>
        :root {{ --bg: #fdfbf7; --card: #ffffff; --text: #333333; --muted: #888888; --accent: #1955a5; }}
        body {{ font-family: "Georgia", "Times New Roman", "Songti SC", "SimSun", serif; -webkit-font-smoothing: antialiased; text-align: left; font-size: 1.25rem; line-height: 1.8; color: var(--text); background: var(--bg); margin: 0; padding: 0; }}
        .container {{ max-width: 760px; margin: 0 auto; background: var(--card); padding: 50px 30px; min-height: 100vh; box-shadow: 0 4px 24px rgba(0,0,0,0.03); box-sizing: border-box; border-left: 1px solid #eaeaea; border-right: 1px solid #eaeaea; }}
        h1 {{ font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "Helvetica Neue", Arial, sans-serif; font-size: 1.9rem; margin-top: 0; padding-bottom: 20px; border-bottom: 2px solid #111; line-height: 1.4; color: #111; }}
        .meta {{ font-family: -apple-system, BlinkMacSystemFont, sans-serif; font-size: 0.9rem; color: var(--muted); margin-bottom: 35px; display: flex; flex-wrap: nowrap; gap: 10px; align-items: center; white-space: nowrap; overflow-x: auto; scrollbar-width: none; }}
        .meta::-webkit-scrollbar {{ display: none; }}
        .meta span {{ flex-shrink: 0; }}
        .meta a {{ color: var(--accent); text-decoration: none; background: #f4f8fc; padding: 6px 12px; border-radius: 4px; font-weight: 500; transition: background 0.2s; flex-shrink: 0; border: 1px solid #e1ebf5; }}
        .meta a:hover {{ background: #e1ebf5; }}
        p {{ margin-bottom: 1.5em; text-align: justify; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>{display_h1}</h1>
        <div class="meta">
            <span>📅 {pub_date}</span>
            <a href="{article_url}" target="_blank">🔗 阅读原文</a>
            <a href="../../index.html">🔙 返回日历</a>
        </div>
        <div class="content">
            {p_tags}
        </div>
    </div>
</body>
</html>"""

    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"文章已保存: {html_path}")

def generate_index():
    pinned_paths = set()
    archive_data = {}

    index_path = os.path.join(BASE_DIR, "index.html")
    if os.path.exists(index_path):
        try:
            with open(index_path, "r", encoding="utf-8") as f:
                content = f.read()
                start_marker = "/*DATA_START*/"
                end_marker = "/*DATA_END*/"
                start = content.find(start_marker)
                end = content.find(end_marker)
                if start != -1 and end != -1:
                    old_json_str = content[start+len(start_marker):end]
                    archive_data = json.loads(old_json_str)

                    for y_data in archive_data.values():
                        for m_data in y_data.values():
                            for d_data in m_data.values():
                                for item in d_data:
                                    if item.get("pinned"):
                                        pinned_paths.add(item["path"])
        except Exception as e:
            print(f"读取历史记录失败: {e}")

    if os.path.exists(BASE_DIR):
        years = [d for d in os.listdir(BASE_DIR) if d.isdigit() and os.path.isdir(os.path.join(BASE_DIR, d))]
        for year in years:
            y_key = str(int(year))
            if y_key not in archive_data:
                archive_data[y_key] = {}

            months = [d for d in os.listdir(os.path.join(BASE_DIR, year)) if d.isdigit() and os.path.isdir(os.path.join(BASE_DIR, year, d))]
            for month in months:
                m_key = str(int(month))
                if m_key not in archive_data[y_key]:
                    archive_data[y_key][m_key] = {}

                files = sorted([f for f in os.listdir(os.path.join(BASE_DIR, year, month)) if f.endswith('.html')], reverse=True)
                for file in files:
                    try:
                        parts = file.replace(".html", "").split('_')
                        if len(parts) >= 4:
                            day = parts[2]
                            d_key = str(int(day))
                            time_str = f"{parts[3][:2]}:{parts[3][2:4]}"
                            file_path = f"{year}/{month}/{file}"

                            local_title = "NYT 新闻"
                            try:
                                with open(os.path.join(BASE_DIR, year, month, file), 'r', encoding='utf-8') as f_html:
                                    content = f_html.read(2000)
                                    start = content.find('<title>')
                                    end = content.find('</title>')
                                    if start != -1 and end != -1:
                                        local_title = content[start+7:end]
                            except:
                                pass

                            if d_key not in archive_data[y_key][m_key]:
                                archive_data[y_key][m_key][d_key] = []

                            item_data = {
                                "time": time_str,
                                "path": file_path,
                                "title": local_title
                            }
                            if file_path in pinned_paths:
                                item_data["pinned"] = True

                            existing_list = archive_data[y_key][m_key][d_key]
                            idx = next((i for i, v in enumerate(existing_list) if v["path"] == file_path), -1)
                            if idx != -1:
                                existing_list[idx] = item_data
                            else:
                                existing_list.append(item_data)

                            archive_data[y_key][m_key][d_key] = sorted(existing_list, key=lambda x: x['time'], reverse=True)
                    except Exception:
                        pass

    json_data = json.dumps(archive_data, ensure_ascii=False)

    html_template = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>我的 NYT 中文新闻库</title>
    <style>
        :root { --bg: #f9f9f9; --text: #111; --muted: #777; --primary: #1955a5; --border: #e2e2e2; --card: #fff; }
        body { font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "Helvetica Neue", Arial, sans-serif; -webkit-font-smoothing: antialiased; background: var(--bg); margin: 0; padding: 0; color: var(--text); }
        
        .container { max-width: 600px; margin: 0 auto; background: var(--bg); min-height: 100vh; display: flex; flex-direction: column; }
        
        .header-brand { background: var(--card); padding: 15px 20px 15px 20px; font-weight: bold; font-family: "Georgia", serif; font-size: 1.2rem; border-bottom: 1px solid var(--border); text-align: center; letter-spacing: 1px; display: flex; justify-content: space-between; align-items: center;}
        
        /* 模态框配置面板样式 */
        .settings-btn { background: none; border: none; font-size: 20px; cursor: pointer; padding: 5px; outline: none; }
        .modal-overlay { display: none; position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.5); z-index: 100; justify-content: center; align-items: center; padding: 20px; }
        .modal-content { background: var(--card); border-radius: 16px; padding: 20px; width: 100%; max-width: 400px; box-shadow: 0 10px 30px rgba(0,0,0,0.1); }
        .modal-title { margin: 0 0 15px 0; font-size: 18px; font-weight: bold; }
        .form-group { margin-bottom: 15px; }
        .form-group label { display: block; font-size: 13px; color: var(--muted); margin-bottom: 5px; font-weight: bold; }
        .form-group input { width: 100%; box-sizing: border-box; padding: 10px; border: 1px solid #ddd; border-radius: 8px; font-size: 14px; outline: none; }
        .modal-actions { display: flex; justify-content: flex-end; gap: 10px; margin-top: 20px; }
        .btn { padding: 8px 16px; border-radius: 8px; border: none; font-size: 14px; font-weight: bold; cursor: pointer; }
        .btn-cancel { background: #eee; color: #333; }
        .btn-save { background: var(--primary); color: #fff; }

        #loadingBar { height: 3px; background: var(--primary); width: 0%; transition: width 0.3s; position: absolute; top: 0; left: 0; z-index: 30; }

        .controls { background: var(--card); padding: 15px 20px; display: flex; justify-content: center; align-items: center; gap: 8px; border-bottom: 1px solid var(--border); }
        .control-btn { background: #fff; color: var(--text); border: 1px solid var(--border); border-radius: 4px; padding: 6px 12px; font-size: 14px; cursor: pointer; }
        .control-btn:active { background: #f0f0f0; }
        .select-box { padding: 6px 10px; border: 1px solid var(--border); border-radius: 4px; font-size: 15px; background: #fff; outline: none; }
        
        .calendar-wrapper { background: var(--card); padding: 10px 15px 20px 15px; margin-bottom: 15px; box-shadow: 0 2px 5px rgba(0,0,0,0.02); }
        .weekdays { display: grid; grid-template-columns: repeat(7, 1fr); text-align: center; font-weight: bold; font-size: 12px; color: var(--muted); margin-bottom: 10px; padding-bottom: 10px; border-bottom: 1px solid #f0f0f0; }
        .days-grid { display: grid; grid-template-columns: repeat(7, 1fr); gap: 5px; }
        
        .day-cell { aspect-ratio: 1; display: flex; flex-direction: column; justify-content: center; align-items: center; font-size: 15px; font-weight: 500; border-radius: 4px; cursor: pointer; position: relative; transition: all 0.2s; }
        .day-cell.empty { visibility: hidden; }
        .day-cell.has-news { color: var(--text); font-weight: bold; }
        .day-cell.no-news { color: #dcdcdc; }
        
        .day-cell.selected { background: var(--primary); color: #fff; }
        .day-cell.today:not(.selected) { border: 1px solid var(--primary); color: var(--primary); }
        .dot { width: 4px; height: 4px; background-color: var(--primary); border-radius: 50%; position: absolute; bottom: 6px; display: none; }
        .day-cell.has-news:not(.selected) .dot { display: block; }
        .day-cell.selected .dot { background-color: #fff; display: block; }
        
        .news-section { flex: 1; padding: 0 15px 30px 15px; }
        
        .news-item-wrapper { display: flex; align-items: center; gap: 10px; margin-bottom: 10px; }
        .news-item { flex: 1; background: var(--card); border-radius: 6px; padding: 18px 15px; margin-bottom: 0; display: flex; justify-content: space-between; align-items: center; text-decoration: none; color: var(--text); box-shadow: 0 1px 3px rgba(0,0,0,0.05); overflow: hidden; border-left: 3px solid transparent; transition: border-left 0.2s; }
        .news-item:hover { border-left: 3px solid var(--primary); }
        .news-item.pinned-item { border-left: 3px solid #f5a623; }
        .news-time { font-size: 13px; font-family: "Georgia", serif; font-weight: 600; flex-shrink: 0; color: var(--primary); }
        .news-title { font-size: 15px; margin-left: 15px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; text-align: right; flex: 1; }
        
        .delete-btn { background: #d93025; color: white; border: none; border-radius: 4px; padding: 0 15px; height: 50px; font-size: 16px; cursor: pointer; display: none; transition: all 0.2s; flex-shrink: 0; }
        .pin-btn { background: #f5a623; color: white; border: none; border-radius: 4px; padding: 0 15px; height: 50px; font-size: 16px; cursor: pointer; display: none; transition: all 0.2s; flex-shrink: 0; }

        .empty-state { text-align: center; padding: 50px 20px; color: #aaa; font-style: italic; }

        .toast-msg { position: fixed; bottom: 30px; left: 50%; transform: translateX(-50%) translateY(20px); background: #333; color: #fff; padding: 12px 24px; border-radius: 4px; font-size: 14px; z-index: 1000; opacity: 0; pointer-events: none; transition: opacity 0.3s, transform 0.3s; white-space: nowrap; box-shadow: 0 4px 12px rgba(0,0,0,0.2); }
        .toast-msg.show { opacity: 1; transform: translateX(-50%) translateY(0); }
    </style>
</head>
<body>
    <div id="loadingBar"></div>
    <div id="toastMsg" class="toast-msg"></div>
    
    <div class="header-brand">
        <div style="width:24px;"></div>
        <span>T H E&nbsp;&nbsp;N E W&nbsp;&nbsp;Y O R K&nbsp;&nbsp;T I M E S</span>
        <button class="settings-btn" id="openSettingsBtn">⚙️</button>
    </div>

    <!-- 填补遗漏的 GitHub 配置面板 -->
    <div class="modal-overlay" id="settingsModal">
        <div class="modal-content">
            <h3 class="modal-title">GitHub 云端同步配置</h3>
            <p style="font-size:12px; color:#888; margin-top:-10px; margin-bottom:15px;">填写 Token 即可在网页端直接同步置顶和删除。</p>
            <div class="form-group"><label>GitHub Personal Access Token</label><input type="password" id="cfgGhToken" placeholder="留空或输入 ghp_..."></div>
            <div class="form-group"><label>GitHub 用户名</label><input type="text" id="cfgGhOwner" placeholder="留空或输入你的用户名"></div>
            <div class="form-group"><label>GitHub 仓库名</label><input type="text" id="cfgGhRepo" value="nyt-news-archive"></div>
            <div class="modal-actions">
                <button class="btn btn-cancel" id="closeSettingsBtn">取消</button>
                <button class="btn btn-save" id="saveSettingsBtn">保存配置</button>
            </div>
        </div>
    </div>

    <div class="container">
        <div class="controls">
            <button class="control-btn" id="prevBtn">&lt;</button>
            <select class="select-box" id="yearSelect"></select>
            <select class="select-box" id="monthSelect">
                <option value="1">01月</option><option value="2">02月</option><option value="3">03月</option>
                <option value="4">04月</option><option value="5">05月</option><option value="6">06月</option>
                <option value="7">07月</option><option value="8">08月</option><option value="9">09月</option>
                <option value="10">10月</option><option value="11">11月</option><option value="12">12月</option>
            </select>
            <button class="control-btn" id="nextBtn">&gt;</button>
            <button class="control-btn" id="todayBtn">今天</button>
        </div>

        <div class="calendar-wrapper">
            <div class="weekdays">
                <span>一</span><span>二</span><span>三</span><span>四</span><span>五</span><span>六</span><span>日</span>
            </div>
            <div class="days-grid" id="daysGrid"></div>
        </div>

        <div class="news-section">
            <div id="newsList"></div>
        </div>
    </div>

    <script>
        function showToast(msg, duration = 3000) {
            const toast = document.getElementById('toastMsg');
            toast.textContent = msg;
            toast.classList.add('show');
            setTimeout(() => { toast.classList.remove('show'); }, duration);
        }

        const loadingBar = document.getElementById('loadingBar');
        
        let archiveData = /*DATA_START*/REPLACEME_JSON_DATA/*DATA_END*/;
        const today = new Date();
        
        const AppState = {
            year: today.getFullYear(),
            month: today.getMonth() + 1,
            day: today.getDate(),
            deleteMode: false
        };

        // --- 设置面板交互逻辑 ---
        document.getElementById('openSettingsBtn').addEventListener('click', () => {
            document.getElementById('cfgGhToken').value = localStorage.getItem('GH_TOKEN_NYT') || '';
            document.getElementById('cfgGhOwner').value = localStorage.getItem('GH_OWNER_NYT') || '';
            document.getElementById('cfgGhRepo').value = localStorage.getItem('GH_REPO_NYT') || 'nyt-news-archive';
            document.getElementById('settingsModal').style.display = 'flex';
        });
        document.getElementById('closeSettingsBtn').addEventListener('click', () => { 
            document.getElementById('settingsModal').style.display = 'none'; 
        });
        document.getElementById('saveSettingsBtn').addEventListener('click', () => {
            localStorage.setItem('GH_TOKEN_NYT', document.getElementById('cfgGhToken').value.trim());
            localStorage.setItem('GH_OWNER_NYT', document.getElementById('cfgGhOwner').value.trim());
            localStorage.setItem('GH_REPO_NYT', document.getElementById('cfgGhRepo').value.trim());
            document.getElementById('settingsModal').style.display = 'none';
            showToast('✅ 配置已本地保存！');
        });

        // --- 安全 Base64 解析 ---
        function fromBase64Safe(b64) {
            const bin = atob(b64.replace(/\\s/g, ''));
            const bytes = new Uint8Array(bin.length);
            for (let i = 0; i < bin.length; i++) {
                bytes[i] = bin.charCodeAt(i);
            }
            return new TextDecoder().decode(bytes);
        }

        async function fetchRealTimeData() {
            const ghToken = localStorage.getItem('GH_TOKEN_NYT');
            const ghOwner = localStorage.getItem('GH_OWNER_NYT');
            const ghRepo = localStorage.getItem('GH_REPO_NYT');
            if (!ghToken || !ghOwner || !ghRepo) return;

            try {
                const res = await fetch(`https://api.github.com/repos/${ghOwner}/${ghRepo}/contents/docs/index.html?t=${Date.now()}`, {
                    headers: { 'Authorization': `token ${ghToken}` }, cache: 'no-store'
                });
                if (res.ok) {
                    const data = await res.json();
                    const content = fromBase64Safe(data.content);
                    const dataStart = content.indexOf('/*DATA_START*/') + 14;
                    const dataEnd = content.indexOf('/*DATA_END*/');
                    if (dataStart !== -1 && dataEnd !== -1) {
                        const remoteData = JSON.parse(content.substring(dataStart, dataEnd));
                        
                        if (JSON.stringify(remoteData) !== JSON.stringify(archiveData)) {
                            archiveData = remoteData;
                            forceRender();
                        }
                    }
                }
            } catch (err) {}
        }
        setTimeout(fetchRealTimeData, 500);

        function ensureYearExists(y) {
            const yearSelect = document.getElementById('yearSelect');
            if (!Array.from(yearSelect.options).some(opt => parseInt(opt.value, 10) === y)) {
                const opt = document.createElement('option');
                opt.value = y; 
                opt.textContent = y + ' 年';
                yearSelect.appendChild(opt);
                
                const options = Array.from(yearSelect.options);
                options.sort((a, b) => parseInt(b.value, 10) - parseInt(a.value, 10));
                yearSelect.innerHTML = '';
                options.forEach(o => yearSelect.appendChild(o));
            }
        }

        function initSelects() {
            const yearSelect = document.getElementById('yearSelect');
            yearSelect.innerHTML = '';
            
            const yearsSet = new Set(Object.keys(archiveData).map(Number));
            for (let i = 0; i <= 50; i++) {
                yearsSet.add(today.getFullYear() + i);
            }
            
            const years = Array.from(yearsSet).sort((a, b) => b - a);
            years.forEach(y => {
                const opt = document.createElement('option');
                opt.value = y; 
                opt.textContent = y + ' 年';
                yearSelect.appendChild(opt);
            });
        }

        function getAllPinnedNews() {
            let pinned = [];
            for (let y in archiveData) {
                for (let m in archiveData[y]) {
                    for (let d in archiveData[y][m]) {
                        archiveData[y][m][d].forEach(news => {
                            if (news.pinned) pinned.push(news);
                        });
                    }
                }
            }
            return pinned;
        }

        function forceRender() {
            ensureYearExists(AppState.year);
            
            const maxDay = new Date(AppState.year, AppState.month, 0).getDate();
            if (AppState.day > maxDay) AppState.day = maxDay;

            document.getElementById('yearSelect').value = AppState.year;
            document.getElementById('monthSelect').value = AppState.month;

            const daysGrid = document.getElementById('daysGrid');
            const newsList = document.getElementById('newsList');

            daysGrid.innerHTML = '';
            newsList.innerHTML = '';

            try {
                const firstDay = new Date(AppState.year, AppState.month - 1, 1).getDay();
                const startDay = firstDay === 0 ? 7 : firstDay;
                
                for (let i = 1; i < startDay; i++) {
                    const emptyCell = document.createElement('div');
                    emptyCell.className = 'day-cell empty';
                    daysGrid.appendChild(emptyCell);
                }
                
                let monthData = {};
                if (archiveData[AppState.year] && archiveData[AppState.year][AppState.month]) {
                    monthData = archiveData[AppState.year][AppState.month];
                }
                
                for (let day = 1; day <= maxDay; day++) {
                    const cell = document.createElement('div');
                    cell.className = 'day-cell';
                    cell.textContent = day;
                    
                    const dot = document.createElement('div');
                    dot.className = 'dot';
                    cell.appendChild(dot);
                    
                    if (monthData[day] && monthData[day].length > 0) cell.classList.add('has-news');
                    else cell.classList.add('no-news');
                    
                    if (AppState.year === today.getFullYear() && AppState.month === today.getMonth() + 1 && day === today.getDate()) cell.classList.add('today');
                    if (day === AppState.day) cell.classList.add('selected');
                    
                    cell.onclick = () => {
                        AppState.day = day;
                        forceRender();
                    };
                    daysGrid.appendChild(cell);
                }
            } catch (err) { console.error("日历渲染异常:", err); }

            try {
                const allPinned = getAllPinnedNews();
                let dayData = [];
                if (archiveData[AppState.year] && archiveData[AppState.year][AppState.month] && archiveData[AppState.year][AppState.month][AppState.day]) {
                    dayData = archiveData[AppState.year][AppState.month][AppState.day];
                }
                
                const currentDayUnpinned = (dayData || []).filter(n => !n.pinned);
                const itemsToRender = [...allPinned, ...currentDayUnpinned];
                
                if (itemsToRender.length > 0) {
                    itemsToRender.forEach((news, index) => {
                        const wrapper = document.createElement('div');
                        wrapper.className = 'news-item-wrapper';

                        const a = document.createElement('a');
                        a.href = news.path;
                        a.className = 'news-item' + (news.pinned ? ' pinned-item' : '');
                        
                        const pinEmoji = news.pinned ? '📌 ' : '';
                        a.innerHTML = `<span class="news-time">${news.time}</span><span class="news-title">${pinEmoji}${news.title}</span>`;
                        wrapper.appendChild(a);

                        const pinBtn = document.createElement('button');
                        pinBtn.className = 'pin-btn';
                        pinBtn.innerHTML = news.pinned ? '❌' : '📌';
                        if (AppState.deleteMode) pinBtn.style.display = 'block';
                        
                        pinBtn.onclick = async (e) => {
                            e.preventDefault();
                            if (!checkGithubConfig()) return;
                            
                            news.pinned = !news.pinned;
                            forceRender(); 
                            await syncIndexToGithub(); 
                            showToast(news.pinned ? '📌 已置顶' : '❌ 已取消置顶');
                        };
                        wrapper.appendChild(pinBtn);

                        const delBtn = document.createElement('button');
                        delBtn.className = 'delete-btn';
                        delBtn.innerHTML = '🗑️';
                        if (AppState.deleteMode) delBtn.style.display = 'block';
                        
                        delBtn.onclick = async (e) => {
                            e.preventDefault();
                            if (!checkGithubConfig()) return;

                            if(confirm('确认删除此条目并同步删除云端文件吗？')) {
                                const pathToDelete = news.path;
                                let found = false;
                                for (let y in archiveData) {
                                    for (let m in archiveData[y]) {
                                        for (let d in archiveData[y][m]) {
                                            const arr = archiveData[y][m][d];
                                            const idx = arr.findIndex(item => item.path === pathToDelete);
                                            if (idx !== -1) {
                                                arr.splice(idx, 1);
                                                if (arr.length === 0) delete archiveData[y][m][d];
                                                found = true; break;
                                            }
                                        }
                                        if(found) break;
                                    }
                                    if(found) break;
                                }
                                forceRender();
                                await syncDeleteToGithub(pathToDelete);
                                showToast('🗑️ 已删除该文章');
                            }
                        };
                        wrapper.appendChild(delBtn);
                        newsList.appendChild(wrapper);
                    });
                } else {
                    newsList.innerHTML = '<div class="empty-state">No articles found for this date.</div>';
                }
            } catch (err) { 
                newsList.innerHTML = '<div class="empty-state">No articles found for this date.</div>';
            }
        }

        document.getElementById('yearSelect').addEventListener('change', (e) => {
            AppState.year = parseInt(e.target.value, 10);
            forceRender();
        });
        
        document.getElementById('monthSelect').addEventListener('change', (e) => {
            AppState.month = parseInt(e.target.value, 10);
            forceRender();
        });
        
        document.getElementById('prevBtn').addEventListener('click', () => {
            AppState.month--;
            if (AppState.month < 1) { 
                AppState.month = 12; 
                AppState.year--; 
            }
            forceRender();
        });
        
        document.getElementById('nextBtn').addEventListener('click', () => {
            AppState.month++;
            if (AppState.month > 12) { 
                AppState.month = 1; 
                AppState.year++; 
            }
            forceRender();
        });
        
        document.getElementById('todayBtn').addEventListener('click', () => {
            AppState.year = today.getFullYear(); 
            AppState.month = today.getMonth() + 1; 
            AppState.day = today.getDate();
            forceRender();
        });

        let lastTap = 0;
        document.querySelector('.calendar-wrapper').addEventListener('click', function(e) {
            const currentTime = new Date().getTime();
            const tapLength = currentTime - lastTap;
            if (tapLength < 500 && tapLength > 0) {
                AppState.deleteMode = !AppState.deleteMode;
                const btns = document.querySelectorAll('.delete-btn, .pin-btn');
                btns.forEach(btn => btn.style.display = AppState.deleteMode ? 'block' : 'none');
                e.preventDefault();
            }
            lastTap = currentTime;
        });
        
        // 检查配置，如果没有就弹出面板
        function checkGithubConfig() {
            const ghToken = localStorage.getItem('GH_TOKEN_NYT');
            const ghOwner = localStorage.getItem('GH_OWNER_NYT');
            const ghRepo = localStorage.getItem('GH_REPO_NYT');
            if (!ghToken || !ghOwner || !ghRepo) {
                alert('请先点击右上角 ⚙️ 配置 GitHub 信息，否则无法在网页端执行同步操作！');
                document.getElementById('settingsModal').style.display = 'flex';
                return false;
            }
            return true;
        }

        function toBase64Safe(str) {
            const bytes = new TextEncoder().encode(str);
            let bin = '';
            const chunkSize = 0x8000;
            for (let i = 0; i < bytes.length; i += chunkSize) {
                bin += String.fromCharCode.apply(null, bytes.subarray(i, i + chunkSize));
            }
            return btoa(bin);
        }

        async function syncIndexToGithub() {
            const ghToken = localStorage.getItem('GH_TOKEN_NYT');
            const ghOwner = localStorage.getItem('GH_OWNER_NYT');
            const ghRepo = localStorage.getItem('GH_REPO_NYT');

            try {
                loadingBar.style.width = '30%';
                const idxRes = await fetch(`https://api.github.com/repos/${ghOwner}/${ghRepo}/contents/docs/index.html?t=${Date.now()}`, {
                    headers: { 'Authorization': `token ${ghToken}` }, cache: 'no-store'
                });
                
                if (!idxRes.ok) throw new Error('Failed to fetch from GitHub');
                
                const idxData = await idxRes.json();
                const idxContent = fromBase64Safe(idxData.content);

                const dataStart = idxContent.indexOf('/*DATA_START*/') + 14;
                const dataEnd = idxContent.indexOf('/*DATA_END*/');
                const newJsonStr = JSON.stringify(archiveData);
                const newIdxContent = idxContent.substring(0, dataStart) + newJsonStr + idxContent.substring(dataEnd);

                loadingBar.style.width = '70%';
                const putRes = await fetch(`https://api.github.com/repos/${ghOwner}/${ghRepo}/contents/docs/index.html`, {
                    method: 'PUT',
                    headers: { 'Authorization': `token ${ghToken}`, 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        message: `Update index.html pinned status`,
                        content: toBase64Safe(newIdxContent),
                        sha: idxData.sha
                    })
                });
                
                if (!putRes.ok) throw new Error('Failed to push to GitHub');

                loadingBar.style.width = '100%';
                setTimeout(() => { loadingBar.style.width = '0%'; }, 1000);
            } catch(e) {
                loadingBar.style.width = '0%';
                showToast('❌ 云端同步状态失败，请检查配置或网络');
            }
        }

        async function syncDeleteToGithub(fileRelPath) {
            const ghToken = localStorage.getItem('GH_TOKEN_NYT');
            const ghOwner = localStorage.getItem('GH_OWNER_NYT');
            const ghRepo = localStorage.getItem('GH_REPO_NYT');

            try {
                loadingBar.style.width = '10%';
                
                const targetFilePath = `docs/${fileRelPath}`;
                const fileRes = await fetch(`https://api.github.com/repos/${ghOwner}/${ghRepo}/contents/${targetFilePath}?t=${Date.now()}`, {
                    headers: { 'Authorization': `token ${ghToken}` }, cache: 'no-store'
                });
                
                if (fileRes.ok) {
                    const fileData = await fileRes.json();
                    await fetch(`https://api.github.com/repos/${ghOwner}/${ghRepo}/contents/${targetFilePath}`, {
                        method: 'DELETE',
                        headers: { 'Authorization': `token ${ghToken}`, 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            message: `Delete archived html file: ${fileRelPath}`,
                            sha: fileData.sha
                        })
                    });
                }
                
                loadingBar.style.width = '50%';

                const idxRes = await fetch(`https://api.github.com/repos/${ghOwner}/${ghRepo}/contents/docs/index.html?t=${Date.now()}`, {
                    headers: { 'Authorization': `token ${ghToken}` }, cache: 'no-store'
                });
                const idxData = await idxRes.json();
                const idxContent = fromBase64Safe(idxData.content);

                const dataStart = idxContent.indexOf('/*DATA_START*/') + 14;
                const dataEnd = idxContent.indexOf('/*DATA_END*/');
                const newJsonStr = JSON.stringify(archiveData);
                const newIdxContent = idxContent.substring(0, dataStart) + newJsonStr + idxContent.substring(dataEnd);

                loadingBar.style.width = '80%';
                await fetch(`https://api.github.com/repos/${ghOwner}/${ghRepo}/contents/docs/index.html`, {
                    method: 'PUT',
                    headers: { 'Authorization': `token ${ghToken}`, 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        message: `Update index.html after deleting file`,
                        content: toBase64Safe(newIdxContent),
                        sha: idxData.sha
                    })
                });
                
                loadingBar.style.width = '100%';
                setTimeout(() => { loadingBar.style.width = '0%'; }, 1000);
            } catch(e) {
                loadingBar.style.width = '0%';
                showToast('❌ 云端同步删除失败');
            }
        }

        initSelects();
        forceRender();

    </script>
</body>
</html>"""

    final_html = html_template.replace(
        "/*DATA_START*/REPLACEME_JSON_DATA/*DATA_END*/", 
        f"/*DATA_START*/{json_data}/*DATA_END*/"
    )

    with open(os.path.join(BASE_DIR, "index.html"), "w", encoding="utf-8") as f:
        f.write(final_html)
    print("首页 index.html 已生成！")


def git_push_to_github(msg="Auto-archive NYT Headline"):
    """执行本地命令将修改自动 Push 到 Github"""
    if not AUTO_PUSH_GITHUB:
        return
    print("\n⏳ 正在自动推送变更到 GitHub...")
    if not os.path.exists(".git"):
        print("⚠️ 当前目录并非 Git 仓库，跳过自动同步。")
        return
    try:
        subprocess.run(["git", "add", "docs/"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        status = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True)
        if not status.stdout.strip():
            print("ℹ️ 没有需要推送的更新。")
            return

        subprocess.run(["git", "commit", "-m", msg], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run(["git", "push"], check=True)
        print("✅ 成功同步到 GitHub！网页版约在 1~3 分钟后刷新可见。")
    except subprocess.CalledProcessError as e:
        print(f"❌ Git 执行失败，错误码: {e.returncode}")
    except FileNotFoundError:
        print("❌ 系统找不到 Git，请确认您已安装 Git 并将其加入环境变量中。")


if __name__ == "__main__":
    os.makedirs(BASE_DIR, exist_ok=True)
    
    # 抓取文章，返回 True 代表有新文章写入
    has_new_article = fetch_nyt_news()
    
    # 如果抓取到了新文章，再执行生成首页和向 GitHub 推送的动作
    if has_new_article:
        generate_index()
        git_push_to_github()
    else:
        # 虽然没有新文章，但为了防止 index.html 被误删或初始化，兜底跑一次生成
        generate_index()
