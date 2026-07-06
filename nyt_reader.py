import requests
from bs4 import BeautifulSoup
import os
import json
from datetime import datetime, timezone, timedelta

BASE_DIR = "docs"
tz_utc_8 = timezone(timedelta(hours=8))

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
        # 寻找头条文章链接。NYT中文网的文章通常包含日期或者类别，过滤掉纯导航或视频
        for a_tag in soup.find_all('a', href=True):
            href = a_tag['href']
            # 文章链接特征：通常包含多个斜杠，不包含特定排除词
            if href.startswith('/') and len(href.split('/')) > 3:
                if not href.startswith('/video/') and not href.startswith('/podcasts/') and 'index.html' not in href:
                    article_url = "https://cn.nytimes.com" + href
                    break

        if not article_url:
            print("未找到文章链接。")
            return

        record_file = "last_nyt_url.txt"
        last_url = ""
        if os.path.exists(record_file):
            with open(record_file, "r") as f:
                last_url = f.read().strip()

        if article_url == last_url:
            print("头条未更新，本次不生成新文章。")
            return

        print(f"发现新突发头条: {article_url}")
        with open(record_file, "w") as f:
            f.write(article_url)

        art_res = requests.get(article_url, headers=headers, timeout=15)
        art_res.encoding = 'utf-8'
        art_soup = BeautifulSoup(art_res.text, 'html.parser')

        # 纽约时报中文网标题通常在 h1 或 article-header 中
        title_tag = art_soup.find('h1')
        title = title_tag.text.strip() if title_tag else "NYT Chinese News"

        now = datetime.now(tz_utc_8)
        current_time = now.strftime("%Y-%m-%d %H:%M")

        paragraphs = art_soup.find_all('p')
        content_paragraphs = []

        for p in paragraphs:
            text = p.text.strip()
            # 过滤过短文本及版权、翻译免责声明等
            if len(text) <= 5: continue
            if "版权所有" in text and "纽约时报" in text: continue
            if "未经许可，" in text: continue
            if "欢迎在" in text and "关注我们" in text: continue
            content_paragraphs.append(text)

        if content_paragraphs:
            save_article(title, content_paragraphs, current_time, article_url, now)
        else:
            print("未提取到有效正文段落。")

    except Exception as e:
        print(f"抓取错误: {e}")

def save_article(title, paragraphs, pub_date, article_url, now_obj):
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
    <title>{title}</title>
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
        <h1>{title}</h1>
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
    archive_data = {}

    if os.path.exists(BASE_DIR):
        years = [d for d in os.listdir(BASE_DIR) if d.isdigit()]
        for year in years:
            y_key = str(int(year))
            if y_key not in archive_data:
                archive_data[y_key] = {}

            months = [d for d in os.listdir(os.path.join(BASE_DIR, year)) if d.isdigit()]
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

                            page_title = "NYT 新闻"
                            try:
                                with open(os.path.join(BASE_DIR, year, month, file), 'r', encoding='utf-8') as f_html:
                                    content = f_html.read(2000)
                                    start = content.find('<title>')
                                    end = content.find('</title>')
                                    if start != -1 and end != -1:
                                        page_title = content[start+7:end]
                            except:
                                pass

                            if d_key not in archive_data[y_key][m_key]:
                                archive_data[y_key][m_key][d_key] = []

                            archive_data[y_key][m_key][d_key].append({
                                "time": time_str,
                                "path": file_path,
                                "title": page_title
                            })
                    except Exception:
                        pass

    json_data = json.dumps(archive_data)

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
        
        .header-brand { background: var(--card); padding: 15px 20px 15px 20px; font-weight: bold; font-family: "Georgia", serif; font-size: 1.2rem; border-bottom: 1px solid var(--border); text-align: center; letter-spacing: 1px;}

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
        .news-time { font-size: 13px; font-family: "Georgia", serif; font-weight: 600; flex-shrink: 0; color: var(--primary); }
        .news-title { font-size: 15px; margin-left: 15px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; text-align: right; flex: 1; }
        
        .delete-btn { background: #d93025; color: white; border: none; border-radius: 4px; padding: 0 15px; height: 50px; font-size: 16px; cursor: pointer; display: none; transition: all 0.2s; flex-shrink: 0; }

        .empty-state { text-align: center; padding: 50px 20px; color: #aaa; font-style: italic; }

        .toast-msg { position: fixed; bottom: 30px; left: 50%; transform: translateX(-50%) translateY(20px); background: #333; color: #fff; padding: 12px 24px; border-radius: 4px; font-size: 14px; z-index: 1000; opacity: 0; pointer-events: none; transition: opacity 0.3s, transform 0.3s; white-space: nowrap; box-shadow: 0 4px 12px rgba(0,0,0,0.2); }
        .toast-msg.show { opacity: 1; transform: translateX(-50%) translateY(0); }
    </style>
</head>
<body>
    <div id="loadingBar"></div>
    <div id="toastMsg" class="toast-msg"></div>
    
    <div class="header-brand">T H E&nbsp;&nbsp;N E W&nbsp;&nbsp;Y O R K&nbsp;&nbsp;T I M E S</div>

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
        const archiveData = /*DATA_START*/REPLACEME_JSON_DATA/*DATA_END*/;
        
        const today = new Date();
        let currentYear = today.getFullYear();
        let currentMonth = today.getMonth() + 1;
        let selectedDay = today.getDate();
        let selectedYear = currentYear;
        let selectedMonth = currentMonth;
        
        window.deleteMode = false;

        const yearSelect = document.getElementById('yearSelect');
        const monthSelect = document.getElementById('monthSelect');
        const daysGrid = document.getElementById('daysGrid');
        const newsList = document.getElementById('newsList');

        function initSelects() {
            yearSelect.innerHTML = '';
            const years = Object.keys(archiveData).map(Number).sort((a, b) => b - a);
            if (!years.includes(currentYear)) years.unshift(currentYear);
            
            years.forEach(y => {
                const opt = document.createElement('option');
                opt.value = y; opt.textContent = y + ' 年';
                yearSelect.appendChild(opt);
            });
            yearSelect.value = selectedYear;
            monthSelect.value = selectedMonth;
        }

        function renderCalendar(year, month) {
            daysGrid.innerHTML = '';
            const firstDay = new Date(year, month - 1, 1).getDay();
            const startDay = firstDay === 0 ? 7 : firstDay;
            const daysInMonth = new Date(year, month, 0).getDate();
            
            for (let i = 1; i < startDay; i++) {
                const emptyCell = document.createElement('div');
                emptyCell.className = 'day-cell empty';
                daysGrid.appendChild(emptyCell);
            }
            
            const monthData = (archiveData[year] && archiveData[year][month]) ? archiveData[year][month] : {};
            
            for (let day = 1; day <= daysInMonth; day++) {
                const cell = document.createElement('div');
                cell.className = 'day-cell';
                cell.textContent = day;
                
                const dot = document.createElement('div');
                dot.className = 'dot';
                cell.appendChild(dot);
                
                if (monthData[day] && monthData[day].length > 0) {
                    cell.classList.add('has-news');
                } else {
                    cell.classList.add('no-news');
                }
                
                if (year === today.getFullYear() && month === today.getMonth() + 1 && day === today.getDate()) cell.classList.add('today');
                if (year === selectedYear && month === selectedMonth && day === selectedDay) cell.classList.add('selected');
                
                cell.addEventListener('click', () => {
                    selectedYear = year; selectedMonth = month; selectedDay = day;
                    renderCalendar(year, month);
                    renderNews(year, month, day);
                });
                
                daysGrid.appendChild(cell);
            }
        }

        function renderNews(year, month, day) {
            newsList.innerHTML = '';
            const monthData = (archiveData[year] && archiveData[year][month]) ? archiveData[year][month] : null;
            const dayData = monthData ? monthData[day] : null;
            
            if (dayData && dayData.length > 0) {
                dayData.forEach((news, index) => {
                    const wrapper = document.createElement('div');
                    wrapper.className = 'news-item-wrapper';

                    const a = document.createElement('a');
                    a.href = news.path;
                    a.className = 'news-item';
                    a.innerHTML = `<span class="news-time">${news.time}</span><span class="news-title">${news.title}</span>`;
                    wrapper.appendChild(a);

                    const delBtn = document.createElement('button');
                    delBtn.className = 'delete-btn';
                    delBtn.innerHTML = '🗑️';
                    if (window.deleteMode) delBtn.style.display = 'block';
                    
                    delBtn.onclick = async (e) => {
                        e.preventDefault();
                        if(confirm('确认删除此条目并同步删除云端文件吗？')) {
                            const pathToDelete = news.path;
                            dayData.splice(index, 1);
                            if (dayData.length === 0) delete archiveData[year][month][day];
                            renderCalendar(year, month);
                            renderNews(year, month, day);
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
        }

        let lastTap = 0;
        const calWrapper = document.querySelector('.calendar-wrapper');
        calWrapper.addEventListener('click', function(e) {
            const currentTime = new Date().getTime();
            const tapLength = currentTime - lastTap;
            if (tapLength < 500 && tapLength > 0) {
                window.deleteMode = !window.deleteMode;
                const btns = document.querySelectorAll('.delete-btn');
                btns.forEach(btn => btn.style.display = window.deleteMode ? 'block' : 'none');
                e.preventDefault();
            }
            lastTap = currentTime;
        });

        async function syncDeleteToGithub(fileRelPath) {
            const ghToken = localStorage.getItem('GH_TOKEN_NYT');
            const ghOwner = localStorage.getItem('GH_OWNER_NYT');
            const ghRepo = localStorage.getItem('GH_REPO_NYT');
            if (!ghToken || !ghOwner || !ghRepo) return;

            try {
                loadingBar.style.width = '10%';
                
                const targetFilePath = `docs/${fileRelPath}`;
                const fileRes = await fetch(`https://api.github.com/repos/${ghOwner}/${ghRepo}/contents/${targetFilePath}`, {
                    headers: { 'Authorization': `token ${ghToken}` }
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

                const idxRes = await fetch(`https://api.github.com/repos/${ghOwner}/${ghRepo}/contents/docs/index.html`, {
                    headers: { 'Authorization': `token ${ghToken}` }
                });
                const idxData = await idxRes.json();
                const idxContent = decodeURIComponent(escape(atob(idxData.content)));

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
                        content: btoa(unescape(encodeURIComponent(newIdxContent))),
                        sha: idxData.sha
                    })
                });
                
                loadingBar.style.width = '100%';
                setTimeout(() => { loadingBar.style.width = '0%'; }, 1000);
            } catch(e) {
                console.error("Sync delete failed", e);
                loadingBar.style.width = '0%';
                showToast('❌ 云端同步删除失败');
            }
        }

        yearSelect.addEventListener('change', (e) => { renderCalendar(parseInt(e.target.value), parseInt(monthSelect.value)); });
        monthSelect.addEventListener('change', (e) => { renderCalendar(parseInt(yearSelect.value), parseInt(e.target.value)); });
        document.getElementById('prevBtn').addEventListener('click', () => {
            let m = parseInt(monthSelect.value) - 1; let y = parseInt(yearSelect.value);
            if (m < 1) { m = 12; y--; yearSelect.value = y; }
            monthSelect.value = m; renderCalendar(y, m);
        });
        document.getElementById('nextBtn').addEventListener('click', () => {
            let m = parseInt(monthSelect.value) + 1; let y = parseInt(yearSelect.value);
            if (m > 12) { m = 1; y++; yearSelect.value = y; }
            monthSelect.value = m; renderCalendar(y, m);
        });
        document.getElementById('todayBtn').addEventListener('click', () => {
            selectedYear = today.getFullYear(); selectedMonth = today.getMonth() + 1; selectedDay = today.getDate();
            yearSelect.value = selectedYear; monthSelect.value = selectedMonth;
            renderCalendar(selectedYear, selectedMonth); renderNews(selectedYear, selectedMonth, selectedDay);
        });

        initSelects();
        renderCalendar(currentYear, currentMonth);
        renderNews(currentYear, currentMonth, selectedDay);
    </script>
</body>
</html>"""

    final_html = html_template.replace(
        "/*DATA_START*/REPLACEME_JSON_DATA/*DATA_END*/", 
        f"/*DATA_START*/{json_data}/*DATA_END*/"
    )

    with open(os.path.join(BASE_DIR, "index.html"), "w", encoding="utf-8") as f:
        f.write(final_html)
    print("首页 index.html 已更新。")

if __name__ == "__main__":
    os.makedirs(BASE_DIR, exist_ok=True)
    fetch_nyt_news()
    generate_index()
