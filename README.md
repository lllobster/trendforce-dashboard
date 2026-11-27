# TrendForce 存储价格看板

按照公开的 TrendForce DRAM 与 NAND Flash 现货价格页面，定时记录 15 项产品的盘平均价格，并发布静态 ECharts 看板。

## 本地运行

使用 Python 3.12 或更新版本：

```bash
python scrape.py
python -m http.server 8000 --directory docs
```

浏览 `http://localhost:8000`。爬虫会按来源网页的更新日期覆盖同日价格、追加新日期，因此可以重复运行。抓取失败时不会覆盖已有数据。

## GitHub Pages 发布

1. 将本项目推送到新仓库 `lllobster/trendforce-dashboard` 的 `main` 分支。
2. 在仓库 **Settings → Pages → Build and deployment** 选择 **GitHub Actions**。
3. 在 **Actions** 中手动运行 `Update TrendForce dashboard` 一次；成功后打开 `https://lllobster.github.io/trendforce-dashboard/`。
4. 工作流默认每天北京时间 19:17 运行，自动抓取并更新页面。

GitHub Actions 需要拥有仓库内容写入权限，以便把 `docs/data/history.json` 的历史记录提交回 `main`。若组织策略限制工作流写权限，请由仓库管理员调整相应设置。公开的 GitHub Pages 页面及其 JSON 数据对任何访问者可见。

数据来源：[TrendForce DRAM](https://www.trendforce.cn/price)、[TrendForce NAND Flash](https://www.trendforce.cn/price/flash)。首次展示的历史基底由[参考看板的公开历史表](https://github.com/flandre576-cpu/memory_pricememory_price)转换而来；2026 年 11 月的最新点位按 TrendForce 公开页面补入，之后由本项目独立更新。公开发布和再次使用数据时应遵守来源网站的使用条款。
