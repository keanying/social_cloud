"""人工执行的真实链接解析验证工具；不参与 unittest 自动发现。"""

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import logging
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.parser_factory import ParserFactory
from utils.web_fetcher import UrlParser, WebFetcher


SAMPLES_PATH = Path(__file__).with_name("live_parser_samples.json")


def load_cases():
    return json.loads(SAMPLES_PATH.read_text(encoding="utf-8"))["cases"]


def collect_media(parser):
    def call(method_name, default):
        try:
            return getattr(parser, method_name)()
        except NotImplementedError:
            return default
        except Exception:
            return default

    video_url = call("get_real_video_url", None)
    video_list = call("get_video_list", [])
    image_list = call("get_image_list", [])
    return {
        "video": bool(video_url or video_list),
        "audio": bool(call("get_audio_url", None)),
        "cover": bool(call("get_cover_photo_url", None)),
        "title": bool(call("get_title_content", "") or call("get_description", "")),
        "author": bool(call("get_author_info", {})),
        "images": bool(image_list),
        "live_media": any(
            isinstance(item, dict) and item.get("live_photo_url") for item in image_list
        ),
    }


def verify_case(case, include_expired=False):
    platform = case["platform"]
    pattern = case.get("pattern", "标准链接")
    url = case.get("url", "")
    is_marked_expired = case.get("status") == "expired" or case.get("is_expired") is True
    if is_marked_expired and not include_expired:
        reason = case.get("expired_reason") or case.get("note") or "用例已标记为失效/下架"
        return "SKIPPED", platform, pattern, f"跳过已失效用例 ({reason})", url

    if not url:
        return "MISSING", platform, pattern, "未配置真实链接", url
    try:
        real_url = WebFetcher.fetch_redirect_url(url)
        if not real_url:
            return "FAILED", platform, pattern, "无法获取或识别分享链接", url
        detected_platform = UrlParser.get_platform(real_url)
        if detected_platform != platform:
            return "FAILED", platform, pattern, f"识别为 {detected_platform or '未知平台'}", url
        parser = ParserFactory.create_parser(platform, real_url)
        found = collect_media(parser)
        expected = case.get("expected_fields", ["title"])
        missing = [field for field in expected if not found.get(field)]
        if missing:
            terminal_detail = getattr(parser, "terminal_error", None) or getattr(parser, "_terminal_filter_detail", None)
            if isinstance(terminal_detail, dict):
                detail_msg = terminal_detail.get("detail_msg") or terminal_detail.get("notice") or "作品已被作者删除或设为私密"
                return "EXPIRED", platform, pattern, f"链接已失效: {detail_msg}", url
            if getattr(parser, "no_media_in_content", False):
                return "EXPIRED", platform, pattern, "分享内容仅为纯文本，未包含媒体资源", url
            return "FAILED", platform, pattern, f"缺少字段：{', '.join(missing)}", url
        present = ", ".join(name for name, value in found.items() if value)
        return "PASSED", platform, pattern, f"已取得：{present}", url
    except Exception as exc:
        err_msg = str(exc)
        if "MEDIA_DELETED" in err_msg or "作品权限或已被删除" in err_msg:
            return "EXPIRED", platform, pattern, f"链接已失效: {type(exc).__name__}: {exc}", url
        return "FAILED", platform, pattern, f"{type(exc).__name__}: {exc}", url


def save_cases(cases_data):
    """回写更新后的用例到 live_parser_samples.json。"""
    raw_content = json.loads(SAMPLES_PATH.read_text(encoding="utf-8"))
    raw_content["cases"] = cases_data
    raw_content["total_cases"] = len(cases_data)
    SAMPLES_PATH.write_text(json.dumps(raw_content, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main():
    ParserFactory._discover()
    parser = argparse.ArgumentParser(description="一键多形态验证真实分享链接")
    parser.add_argument("--platform", action="append", help="仅验证指定平台；可重复传入")
    parser.add_argument("--list-missing", action="store_true", help="仅列出缺少链接的平台")
    parser.add_argument("--include-expired", action="store_true", help="强制包含标记为失效的用例一起运行")
    parser.add_argument("--auto-mark-expired", action="store_true", help="自动将检测到已失效的用例标记为 status=expired")
    parser.add_argument("--limit", type=int, default=0, help="限制每个平台运行的最大用例数 (默认全部)")
    parser.add_argument("--workers", type=int, default=20, help="并发线程数 (默认 20，0 表示单线程顺序执行)")
    parser.add_argument("--summary-only", action="store_true", help="仅输出最终汇总，适合全量回归")
    args = parser.parse_args()
    if args.summary_only:
        logging.disable(logging.CRITICAL)

    all_cases = load_cases()
    cases = all_cases
    if args.platform:
        requested = set(args.platform)
        cases = [case for case in cases if case["platform"] in requested]
        unknown = requested - {case["platform"] for case in cases}
        if unknown:
            parser.error(f"样例清单中不存在平台：{', '.join(sorted(unknown))}")
    if args.list_missing:
        for case in cases:
            if not case.get("url"):
                print(f"MISSING  {case['platform']}: {case['note']}", flush=True)
        return

    if args.limit > 0:
        limited_cases = []
        counts = {}
        for case in cases:
            p = case["platform"]
            counts[p] = counts.get(p, 0) + 1
            if counts[p] <= args.limit:
                limited_cases.append(case)
        cases = limited_cases

    platform_count = len(set(c["platform"] for c in cases))
    print(f"🧪 开始执行 {platform_count} 平台自动化多形态链接验证 (共 {len(cases)} 条用例, 线程数: {args.workers if args.workers > 0 else 1})...\n", flush=True)
    
    results = []
    status_icons = {
        "PASSED": "✅ PASSED  ",
        "FAILED": "❌ FAILED  ",
        "EXPIRED": "⚠️ EXPIRED ",
        "SKIPPED": "⚪ SKIPPED ",
        "MISSING": "⚪ MISSING ",
    }

    if args.workers > 1:
        with ThreadPoolExecutor(max_workers=args.workers) as executor:
            future_to_case = {executor.submit(verify_case, case, args.include_expired): case for case in cases}
            for future in as_completed(future_to_case):
                try:
                    res = future.result()
                except Exception as exc:
                    c = future_to_case[future]
                    res = ("FAILED", c["platform"], c.get("pattern", ""), f"{type(exc).__name__}: {exc}", c.get("url", ""))
                results.append(res)
                status, platform, pattern, detail, url = res
                status_tag = status_icons.get(status, f"[{status}]")
                if not args.summary_only:
                    print(f"{status_tag} [{platform:<6}] ({pattern[:25]}): {detail}", flush=True)
    else:
        for case in cases:
            res = verify_case(case, args.include_expired)
            results.append(res)
            status, platform, pattern, detail, url = res
            status_tag = status_icons.get(status, f"[{status}]")
            if not args.summary_only:
                print(f"{status_tag} [{platform:<6}] ({pattern[:25]}): {detail}", flush=True)

    summary = {status: sum(1 for result in results if result[0] == status) for status in ("PASSED", "FAILED", "EXPIRED", "SKIPPED", "MISSING")}
    print("\n" + "=" * 60, flush=True)
    print("📊 验证汇总：" + ", ".join(f"{key}={value}" for key, value in summary.items() if value > 0 or key in ("PASSED", "FAILED")), flush=True)
    
    active_total = summary["PASSED"] + summary["FAILED"] + summary["EXPIRED"] + summary["MISSING"]
    if active_total > 0:
        pass_rate = (summary["PASSED"] / active_total) * 100
        print(f"🎯 有效用例通过率：{pass_rate:.1f}% ({summary['PASSED']}/{active_total})", flush=True)
    if summary.get("SKIPPED", 0) > 0:
        print(f"💡 已跳过失效/下架用例: {summary['SKIPPED']} 条 (传入 --include-expired 可强制测试)", flush=True)
    
    if args.summary_only or summary.get("FAILED", 0) > 0 or summary.get("EXPIRED", 0) > 0:
        failures = [result for result in results if result[0] in ("FAILED", "EXPIRED")]
        if failures:
            print("\n🚨 需关注/异常用例：", flush=True)
            for status, platform, pattern, detail, url in failures:
                print(f"- [{status}] [{platform}] {pattern}: {detail} -> {url}", flush=True)

    if args.auto_mark_expired and summary.get("EXPIRED", 0) > 0:
        expired_urls = {res[4]: res[3] for res in results if res[0] == "EXPIRED" and res[4]}
        marked_count = 0
        for case in all_cases:
            case_url = case.get("url")
            if case_url in expired_urls and case.get("status") != "expired":
                case["status"] = "expired"
                case["expired_reason"] = expired_urls[case_url]
                marked_count += 1
        if marked_count > 0:
            save_cases(all_cases)
            print(f"\n💾 已自动将 {marked_count} 条失效链接标记为 status='expired' 并持久化回用例库。", flush=True)

    print("=" * 60, flush=True)


if __name__ == "__main__":
    main()
