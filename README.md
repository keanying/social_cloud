<div align="center">
<img src="static/images/brand-logo.png" width="96" alt="社媒云">

# 社媒云

**复制链接，一键保存社交媒体上的视频和图片**

支持 50 个平台的视频、图集、实况照片、背景音乐与文案提取，本页播放、一键下载，自带用户与点数管理后台。

[功能](#功能) · [支持的平台](#支持的平台) · [快速开始](#快速开始) · [首次使用](#首次使用超级管理员) · [配置](#配置) · [API](#api-接入) · [开发与测试](#开发与测试) · [合规声明](#合规声明)
</div>

---

## 功能

**面向用户的首页**

- 一个输入框粘贴任意平台的分享链接或整段分享文案，自动识别平台
- 解析结果在本页直接播放视频和音乐、查看图集与实况照片（服务端中转，绕开防盗链，可拖动进度）
- 单个下载，或「一键下载全部」把视频、背景音乐、图片打包成一个 zip；文件按「平台-标题-视频 / 音频 / 图1」自动命名
- 默认登录后才能解析（可在后台关闭）；**首页解析、播放、下载都不扣点数**

**用户控制台**（`/console`）

- 查看剩余点数、有效期、QPS 上限与调用趋势
- 创建和管理自己的 API Key，查看请求日志，开发者文档与在线调试

**管理后台**（`/admin`，超级管理员）

- 客户账号：单个或批量调整点数（增加 / 扣减 / 设为指定值）、有效期、QPS，启用停用，重置密码
- 系统设置：注册开关、新用户默认点数 / 试用天数 / QPS、首页解析是否需要登录、全局服务开关
- API 密钥管理、支持平台开关与限流、平台凭据（Cookie）巡检、运行日志与 CSV 导出

**点数规则**：只有通过 API Key 调用 `/api/v1/parse` 才扣点，每次成功解析扣 1 点，失败自动退回；管理员与「无限额度」账号不扣点。

## 支持的平台

| 平台名称 | 作者 | 标题 | 文案 | 封面 | 视频 | 图集 | 多视频 | 实况 | 音频 | 字幕 | 解析说明 |
| --- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **抖音** | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | [查看](docs/parsers/douyin.md) |
| **小红书** | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |  | ✓ |  |  | [查看](docs/parsers/xiaohongshu.md) |
| **视频号** | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |  |  | ✓ |  | [查看](docs/parsers/wechat-channels.md) |
| **微信公众号** | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |  | ✓ |  | [查看](docs/parsers/wechat-mp.md) |
| **快手** | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |  |  | ✓ |  | [查看](docs/parsers/kuaishou.md) |
| **哔哩哔哩** | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |  |  |  | [查看](docs/parsers/bilibili.md) |
| **豆包** | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |  | ✓ |  | [查看](docs/parsers/doubao.md) |
| **即梦AI** | ✓ | ✓ | ✓ | ✓ | ✓* | ✓ | ✓ |  |  |  | [查看](docs/parsers/jimeng.md) |
| **小云雀AI** | ✓ | ✓ | ✓ | ✓* | ✓* | ✓ |  |  |  |  | [查看](docs/parsers/xiaoyunque.md) |
| **可灵AI** | ✓ | ✓ |  | ✓ | ✓ |  |  |  |  |  | [查看](docs/parsers/kling.md) |
| **海螺AI** | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |  |  |  |  | [查看](docs/parsers/hailuo.md) |
| **夸克AI** | ✓ | ✓ |  | ✓ | ✓ | ✓ |  |  |  |  | [查看](docs/parsers/quark-ai.md) |
| **通义千问** | ✓ | ✓ |  | ✓ | ✓ | ✓ | ✓ |  |  |  | [查看](docs/parsers/qianwen.md) |
| **腾讯元宝** | ✓ | ✓ |  | ✓ | ✓* | ✓ | ✓ |  |  |  | [查看](docs/parsers/yuanbao.md) |
| **闲鱼** | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |  |  |  |  | [查看](docs/parsers/xianyu.md) |
| **拼多多** | ✓ | ✓ |  | ✓ | ✓ | ✓ |  |  | ✓ |  | [查看](docs/parsers/pinduoduo.md) |
| **Soul** | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |  |  |  |  | [查看](docs/parsers/soul.md) |
| **汽水音乐** | ✓ | ✓ |  | ✓ | ✓ |  |  |  | ✓ | ✓ | [查看](docs/parsers/qsmusic.md) |
| **QQ音乐** | ✓ | ✓ |  | ✓ | ✓ |  | ✓ |  | ✓ | ✓ | [查看](docs/parsers/qqmusic.md) |
| **网易云音乐** | ✓ | ✓ |  | ✓ | ✓ | ✓ |  |  | ✓ | ✓ | [查看](docs/parsers/netease-music.md) |
| **酷狗音乐** | ✓ | ✓ |  | ✓ | ✓ |  |  |  | ✓ |  | [查看](docs/parsers/kugou-music.md) |
| **配音秀** | ✓ | ✓ |  | ✓ | ✓ |  |  |  |  |  | [查看](docs/parsers/peiyinxiu.md) |
| **松果时刻** | ✓ | ✓ |  | ✓ | ✓ | ✓ | ✓ |  | ✓ |  | [查看](docs/parsers/pinecone-moment.md) |
| **腾讯频道** | ✓ | ✓ |  | ✓ | ✓ |  |  |  |  |  | [查看](docs/parsers/tencent-channel.md) |
| **剪映 / CapCut** | ✓ | ✓ |  | ✓ | ✓ | ✓ |  |  | ✓ |  | [查看](docs/parsers/jianying.md) |
| **快影** | ✓ | ✓ | ✓ | ✓ | ✓ |  |  |  | ✓ |  | [查看](docs/parsers/kwaiying.md) |
| **皮皮搞笑** | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |  |  |  |  | [查看](docs/parsers/pipigaoxiao.md) |
| **微视** | ✓ | ✓ |  | ✓ | ✓ |  |  |  |  |  | [查看](docs/parsers/weishi.md) |
| **AcFun** | ✓ | ✓ |  | ✓ | ✓ |  |  |  |  |  | [查看](docs/parsers/acfun.md) |
| **西瓜视频** | ✓ | ✓ | ✓ | ✓ | ✓ |  |  |  |  |  | [查看](docs/parsers/xigua.md) |
| **今日头条** | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |  |  |  |  | [查看](docs/parsers/toutiao.md) |
| **绿洲** | ✓ | ✓ |  | ✓ | ✓ | ✓ |  |  |  |  | [查看](docs/parsers/lvzhou.md) |
| **皮皮虾** | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |  |  |  |  | [查看](docs/parsers/pipixia.md) |
| **全民K歌** |   | ✓ |  | ✓ | ✓ |  |  |  |  |  | [查看](docs/parsers/quanminkge.md) |
| **新片场** | ✓ | ✓ |  | ✓ | ✓ |  | ✓ |  |  |  | [查看](docs/parsers/xinpianchang.md) |
| **好看视频** | ✓ | ✓ |  | ✓ | ✓ |  |  |  |  |  | [查看](docs/parsers/haokan.md) |
| **梨视频** | ✓ | ✓ |  | ✓ | ✓ |  |  |  |  |  | [查看](docs/parsers/lishipin.md) |
| **微博** | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |  | ✓ |  |  | [查看](docs/parsers/weibo.md) |
| **知乎** | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |  |  |  |  | [查看](docs/parsers/zhihu.md) |
| **虎牙** |   | ✓ |  | ✓ | ✓ |  |  |  |  |  | [查看](docs/parsers/huya.md) |
| **美拍** | ✓ | ✓ |  | ✓ | ✓ |  |  |  |  |  | [查看](docs/parsers/meipai.md) |
| **最右** | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |  | ✓ |  |  | [查看](docs/parsers/zuiyou.md) |
| **番茄小说** | ✓ | ✓ |  | ✓ | ✓ |  |  |  |  |  | [查看](docs/parsers/fanqie.md) |
| **红果短剧** | ✓ | ✓ |  | ✓ | ✓ |  |  |  |  |  | [查看](docs/parsers/fanqie.md) |
| **红果漫剧** | ✓ | ✓ |  | ✓ | ✓ |  |  |  |  |  | [查看](docs/parsers/fanqie.md) |
| **得物** | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |  |  |  |  | [查看](docs/parsers/dewu.md) |
| **网易LOFTER** | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |  |  |  |  | [查看](docs/parsers/lofter.md) |
| **星绘AI** | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |  |  |  |  | [查看](docs/parsers/butterflyai.md) |
| **央视** | ✓ | ✓ |  | ✓ | ✓ |  |  |  |  |  | [查看](docs/parsers/cctv.md) |
| **央视频** | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |  |  |  |  | [查看](docs/parsers/yangshipin.md) |

带 `*` 的项保留平台原生水印。部分平台需要配置 Cookie，见 [平台 Cookie 配置](docs/cookie-config.md)；平台改版可能导致个别平台暂时不可用，可在后台「支持平台」中单独关闭。

## 快速开始

需要 Python 3.10+（推荐 3.11）。启动脚本会自动创建 `.venv` 并安装依赖，默认端口 `8051`。

| 操作 | Windows | Linux / macOS |
| --- | --- | --- |
| 启动服务 | `scripts\start.bat` | `./scripts/start.sh` |
| 单元测试 + 启动验证 | `scripts\start.bat verify` | `./scripts/start.sh verify` |

启动后访问 `http://127.0.0.1:8051/`。入口统一为 `run.py`：Linux / macOS 使用 gunicorn，Windows 使用 waitress。

**Docker 部署**

```bash
cp .env.example .env
docker compose up -d --build
docker compose logs -f web
```

数据库与会话密钥持久化在 `./data`，日志在 `./logs`。

## 首次使用：超级管理员

1. 首次部署后访问 `/auth/setup` 创建超级管理员。该页面只在系统中还没有管理员时开放，创建后自动关闭。
2. 管理员登录后进入 `/admin`，在「系统设置」中配置注册开关、新用户默认点数、首页解析是否需要登录等。
3. 普通用户在首页或 `/auth/register` 注册，登录后进入 `/console`。

> 管理员只有一个，后台不能把普通用户升级为管理员，请妥善保管管理员密码。

## 配置

复制 `.env.example` 为 `.env` 后按需修改，常用项：

| 变量 | 说明 | 默认值 |
| --- | --- | --- |
| `SECRET_KEY` | 会话加密密钥，生产环境建议固定为强随机值 | 自动生成并保存在 `data/.secret_key` |
| `DATABASE_PATH` | SQLite 数据库路径 | `data/media_parser.db` |
| `WEB_HOST` / `WEB_PORT` / `WEB_WORKERS` | 监听地址、端口、gunicorn 进程数（`run.py` 读取） | `0.0.0.0` / `8051` / `2` |
| `TRUST_PROXY_HEADERS` | 部署在 Nginx 等反向代理之后时设为 `true` | `false` |
| `API_ONLY` | 纯 API 模式：不提供网页，接口免 Key 调用 | `false` |
| `CORS_ORIGINS` | `/api/*` 允许的跨域来源，逗号分隔 | `*` |
| `MAX_DOWNLOAD_BYTES` | 本页播放 / 单个下载中转的单文件上限（字节） | `1073741824`（1 GB） |
| `MAX_BUNDLE_BYTES` | 「一键下载全部」打包 zip 的总大小上限（字节） | `2147483648`（2 GB） |
| `DYNAMIC_PROXY_API_URL` | 平台风控时自动切换的动态代理提取地址，见 [docs/proxy-retry.md](docs/proxy-retry.md) | 空 |
| `XHS_COOKIE` 等 | 各平台 Cookie 凭据，见 [docs/cookie-config.md](docs/cookie-config.md) | 空 |

注册开关、解析是否需要登录、默认点数等运行时开关在后台「系统设置」中修改，即时生效，无需重启。

### 本页播放与一键下载

平台 CDN 普遍有防盗链，浏览器无法直接播放或下载，因此由服务端中转：`/api/media` 用于本页播放（支持 Range 拖动进度），`/api/download` 用于单个下载，`/api/download/bundle` 把多个文件边下载边打包成一个 zip（只触发一次下载，避免浏览器拦截连续下载；失败的文件会在 zip 内的说明中列出）。

- 只中转**当前登录用户 2 小时内解析得到的地址**，不能被用来访问任意网址；
- 每一跳重定向都会校验目标必须是公网地址，拒绝内网与本机地址；
- 中转响应带有 `Content-Security-Policy: sandbox` 与 `nosniff`，非音视频 / 图片内容一律按二进制返回。

中转会占用服务器带宽，请结合带宽情况调整 `MAX_DOWNLOAD_BYTES`，必要时在后台关闭注册。

## API 接入

用户在控制台创建 API Key 后调用：

```bash
curl --get 'https://your-domain.com/api/v1/parse' \
  --header 'Authorization: Bearer mp-xxx' \
  --data-urlencode 'url=分享链接或整段分享文案'
```

接口返回统一的 JSON（`retcode` / `succ` / `data` / `error_code`），字段与错误码详见 [docs/api.md](docs/api.md) 或控制台「开发者文档」。

## 开发与测试

```bash
python -m pytest -q
python scripts/verify.py --spawn
```

- 第一条运行单元测试；第二条用临时数据库启动服务并做冒烟检查
- GitHub Actions 在 Ubuntu 与 Windows 上执行同样的测试与启动验证（`.github/workflows/verify.yml`）
- 真实链接回归：`python tests/manual_verify_parsers.py --limit 1`（会访问各平台，需要外网）
- 架构说明见 [docs/architecture.md](docs/architecture.md)，测试说明见 [docs/testing.md](docs/testing.md)

```text
app.py / run.py      应用入口 / 跨平台启动
src/api/             解析、本页播放、一键下载接口
src/parsers/         各平台解析器（ParserFactory 自动注册）
src/web/             首页、用户控制台、管理后台
templates/ static/   页面模板与静态资源（图标：static/icons-ms.svg）
scripts/             启动、验证、Cookie 采集脚本
tests/               单元测试与真实样本库
```

## 合规声明

社媒云仅用于保存**用户自己发布或已获得作者授权**的公开内容，不支持私密、付费、会员专享内容及版权长视频。请遵守各平台用户协议与相关法律法规；转载、二次发布或商用前请先取得原作者许可。因使用本项目产生的法律责任由使用者自行承担。

## 许可证与致谢

本项目基于 [ucmao/media-parser](https://github.com/ucmao/media-parser)（MIT License）二次开发，现由社媒云独立维护，原项目版权声明保留在 [LICENSE](LICENSE) 中。

界面图标来自 [Material Symbols](https://github.com/google/material-design-icons)（Apache License 2.0）。
