# 好看视频 (Haokan) 逆向解析指南

本篇详细记录百度旗下 **好看视频** 短视频的逆向提取方案。

---

## 1. 平台特征与支持能力

* **平台标识**：`好看视频`
* **支持媒体类型**：无水印 1080P/超清/高清视频 (MP4) / 视频封面 / 标题与作者
* **常见链接形态**：
  * 网页链接：`https://haokan.baidu.com/v?vid=17831460188721240800`
  * 百度分享短链：`https://mr.baidu.com/r/22HM1zborMA?f=cp&u=c88bf4dbb5418758`
  * 百度落地页：`https://mbd.baidu.com/newspage/data/videoshare?nid=sv_10423411367049244882`
  * 百度搜索视频页：`https://m.baidu.com/video/page?pd=video_page&nid=14766924042149789226&sign=...`
* **Cookie 依赖**：无需 Cookie。

---

## 2. 核心逆向流程

1. **短链跳转与参数提取**：
   - 跟踪 `mr.baidu.com` 重定向并保留核心白名单参数（`nid`, `vid`, `id`, `context`, `pd`, `sign`, `word` 等）。
2. **提取 HTML 内嵌视频源**：
   - **现代版本**：匹配提取 `window.jsonData` 中的 `data.videoInfo`，从 `clarityArr` 按清晰度 rank 降序提取最高画质（如 1080P/超清）视频直链；
   - **旧版版本**：提取 `window.__PRELOADED_STATE__` 中的 `curVideoMeta.clarityUrl`；
   - **移动搜索落地页**：从 script 标签内嵌 JSON 中提取协议相对（`//vd...`）播放源并补齐 HTTPS 协议。

---

## 3. 测试与验证

* **单元测试**：[tests/test_haokan_parser.py](file:///Users/leo/Projects/media-parser/tests/test_haokan_parser.py)
* **样本验证**：
  ```bash
  python -m unittest tests/test_haokan_parser.py
  ```
