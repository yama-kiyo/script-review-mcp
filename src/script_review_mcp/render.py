"""診断レポート (マークダウン) を HTML / PNG に画像化するレンダラ.

設計方針:
    - markdown ライブラリで HTML 化、PEARL の Pearl/Ink パレットで装飾
    - A案/B案/C案 ブロック・優先度バッジ・スコアセル等は軽量な事前変換で
      視覚的に強調する
    - PNG は Chrome headless で書き出し、Pillow で末尾の余白を自動トリム
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import textwrap
from datetime import datetime
from pathlib import Path
from typing import Optional

import markdown as md_lib
from PIL import Image

from . import __version__

# ------------------------------------------------------------------
# Chrome headless パス候補
# ------------------------------------------------------------------

_CHROME_CANDIDATES = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Google Chrome Canary.app/Contents/MacOS/Google Chrome Canary",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
]


def _find_chrome() -> Optional[str]:
    for candidate in _CHROME_CANDIDATES:
        if Path(candidate).is_file():
            return candidate
    for name in ("google-chrome", "chromium", "chromium-browser", "msedge"):
        path = shutil.which(name)
        if path:
            return path
    return None


# ------------------------------------------------------------------
# CSS (PEARL Pearl/Ink パレット)
# ------------------------------------------------------------------

_CSS = """
:root {
  --ink: #0B0B0D;
  --pearl: #F4F0E8;
  --paper: #ffffff;
  --line: #d8d3c7;
  --line-soft: #ebe6da;
  --gold: #b89464;
  --crimson: #a23a3a;
  --green: #1d6b3d;
  --blue: #2a7adb;
  --purple: #7e3ad8;
  --gray: #666;
}
* { box-sizing: border-box; }
body {
  margin: 0;
  padding: 56px 64px;
  font-family: "Helvetica Neue", "Hiragino Sans", "Yu Gothic", "Meiryo", sans-serif;
  background: var(--pearl);
  color: var(--ink);
  line-height: 1.85;
  font-size: 15px;
}
.container { max-width: 1280px; margin: 0 auto; }
h1 {
  font-size: 28px;
  font-weight: 700;
  border-bottom: 2px solid var(--ink);
  padding-bottom: 14px;
  margin-bottom: 28px;
}
h2 {
  font-size: 19px;
  font-weight: 700;
  margin-top: 36px;
  margin-bottom: 14px;
  padding-bottom: 6px;
  border-bottom: 1px solid var(--line);
}
h3 {
  font-size: 16px;
  font-weight: 700;
  margin-top: 24px;
  margin-bottom: 10px;
  padding-left: 12px;
  border-left: 4px solid var(--gold);
}
h4 {
  font-size: 14px;
  font-weight: 700;
  margin-top: 18px;
  margin-bottom: 8px;
  color: var(--gray);
}
p { margin: 8px 0; }
ul, ol { margin: 8px 0; padding-left: 28px; }
li { margin: 4px 0; }
strong { color: var(--ink); font-weight: 700; }
em { color: var(--gray); }
code {
  background: #f0ebde;
  padding: 1px 6px;
  border-radius: 3px;
  font-family: "SF Mono", Menlo, monospace;
  font-size: 13px;
}
pre {
  background: var(--paper);
  border: 1px solid var(--line);
  border-radius: 4px;
  padding: 14px 18px;
  overflow-x: auto;
  font-size: 13px;
}
pre code { background: none; padding: 0; }
table {
  border-collapse: collapse;
  width: 100%;
  margin: 16px 0;
  background: var(--paper);
  font-size: 13px;
}
th, td {
  border: 1px solid var(--line-soft);
  padding: 8px 12px;
  text-align: left;
}
thead th {
  background: #ece6d6;
  font-weight: 700;
}
tbody tr:nth-child(even) td { background: #faf8f2; }
blockquote {
  border-left: 3px solid var(--gold);
  margin: 12px 0;
  padding: 6px 18px;
  color: var(--gray);
  font-size: 14px;
}
hr {
  border: none;
  border-top: 1px solid var(--line);
  margin: 24px 0;
}

/* ------ 専用ブロック (前処理で挿入される) ------ */
.score-row {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 18px;
  margin: 18px 0 28px;
}
.score-card {
  background: var(--paper);
  border: 1px solid var(--line);
  border-radius: 4px;
  padding: 18px 24px;
  text-align: center;
}
.score-card .num {
  font-size: 42px;
  font-weight: 700;
  line-height: 1;
  color: var(--ink);
}
.score-card .num small { font-size: 18px; color: #999; }
.score-card .lbl {
  font-size: 12px;
  letter-spacing: 0.06em;
  color: var(--gray);
  margin-top: 6px;
}

.priority-high, .priority-mid, .priority-low {
  display: inline-block;
  padding: 2px 10px;
  border-radius: 3px;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.05em;
  color: #fff;
  margin-right: 8px;
  vertical-align: middle;
}
.priority-high { background: var(--crimson); }
.priority-mid { background: var(--gold); }
.priority-low { background: #888; }

.option-block {
  border: 1px solid var(--line-soft);
  background: #faf8f2;
  border-radius: 4px;
  padding: 14px 18px;
  margin: 10px 0;
}
.option-block.option-a { border-left: 4px solid #6c7a89; }
.option-block.option-b { border-left: 4px solid var(--blue); }
.option-block.option-c { border-left: 4px solid var(--purple); }
.option-block .label {
  font-weight: 700;
  margin-bottom: 6px;
  font-size: 14px;
}
.option-block ul { margin: 4px 0; }

.confidence-high { color: var(--green); font-weight: 700; }
.confidence-mid { color: var(--gold); font-weight: 700; }
.confidence-low { color: var(--gray); }

.report-footer {
  margin-top: 48px;
  padding-top: 16px;
  border-top: 1px solid var(--line);
  font-size: 11px;
  color: #888;
  display: flex;
  justify-content: space-between;
}
.report-footer .brand {
  color: var(--ink);
  font-weight: 700;
}
"""


# ------------------------------------------------------------------
# Markdown → HTML (前処理 + markdown ライブラリ)
# ------------------------------------------------------------------


def _preprocess_markdown(text: str) -> str:
    """A案/B案/C案・優先度バッジ等を HTML に置換する事前変換."""
    out = text

    # 優先度: 高 / 中 / 低 → バッジ化
    out = re.sub(
        r"【\s*優先度\s*[:：]\s*高\s*】",
        '<span class="priority-high">優先度 高</span>',
        out,
    )
    out = re.sub(
        r"【\s*優先度\s*[:：]\s*中\s*】",
        '<span class="priority-mid">優先度 中</span>',
        out,
    )
    out = re.sub(
        r"【\s*優先度\s*[:：]\s*低\s*】",
        '<span class="priority-low">優先度 低</span>',
        out,
    )

    # **A案. xxx** ... 続く - 行 を <div class="option-block"> ブロックに包む
    # マッチ範囲: **A案. xxx** から、次の **B案/C案/D案/任意の見出し** または空行が来るまで
    def wrap_option(match: re.Match) -> str:
        label_letter = match.group("letter")
        cls = f"option-{label_letter.lower()}"
        title = match.group("title").strip()
        body = match.group("body").rstrip()
        return (
            f'<div class="option-block {cls}">\n'
            f'<div class="label">{label_letter}案. {title}</div>\n\n'
            f'{body}\n'
            f"</div>\n"
        )

    pattern = re.compile(
        r"^\*\*\s*(?P<letter>[A-Ca-c])\s*案\s*\.\s*(?P<title>[^*\n]+?)\*\*\n"
        r"(?P<body>(?:[-•*\s].*\n?)+?)"
        r"(?=^\*\*\s*[A-Ca-c]\s*案|^##|^---|^\*\*推奨|\Z)",
        re.MULTILINE,
    )
    out = pattern.sub(wrap_option, out)

    # 信頼度カラーリング
    out = re.sub(
        r"(信頼度\s*[:：]?\s*)(High)", r'\1<span class="confidence-high">\2</span>', out
    )
    out = re.sub(
        r"(信頼度\s*[:：]?\s*)(Medium)", r'\1<span class="confidence-mid">\2</span>', out
    )
    out = re.sub(
        r"(信頼度\s*[:：]?\s*)(Low)", r'\1<span class="confidence-low">\2</span>', out
    )

    return out


def _detect_score_block(html: str) -> str:
    """総合評価セクション内のスコア行 (◯/100, ◯/10) をスコアカードに変換."""

    def replace_score_section(match: re.Match) -> str:
        section_title = match.group(1)
        section_body = match.group(2)
        score_pattern = re.compile(
            r"<li>\s*<strong>([^<]+)</strong>\s*[:：]?\s*([0-9.]+)\s*/\s*([0-9.]+)\s*</li>"
        )
        cards = []
        remaining_lines = []
        for line in section_body.splitlines():
            score_match = score_pattern.search(line)
            if score_match:
                label, num, denom = score_match.groups()
                cards.append(
                    f'<div class="score-card">'
                    f'<div class="num">{num}<small>/{denom}</small></div>'
                    f'<div class="lbl">{label}</div>'
                    f"</div>"
                )
            else:
                remaining_lines.append(line)
        if not cards:
            return match.group(0)
        cards_html = '<div class="score-row">' + "\n".join(cards) + "</div>"
        return f"<h2>{section_title}</h2>\n{cards_html}\n" + "\n".join(remaining_lines)

    pattern = re.compile(
        r"<h2>([^<]*(?:総合評価|総合スコア|Overall)[^<]*)</h2>\s*"
        r"((?:<ul>.*?</ul>)+)",
        re.DOTALL,
    )
    return pattern.sub(replace_score_section, html)


def render_to_html(markdown_text: str, title: str = "構造診断レポート") -> str:
    """マークダウン診断レポートを装飾済み HTML に変換する."""
    pre = _preprocess_markdown(markdown_text)
    body = md_lib.markdown(
        pre,
        extensions=["tables", "fenced_code", "sane_lists", "md_in_html"],
    )
    body = _detect_score_block(body)

    footer = (
        f'<div class="report-footer">'
        f'<div>※自動診断は初期値の補助。最終判断は書き手が握ってください。</div>'
        f'<div class="brand">script-review-mcp v{__version__} / MIT License</div>'
        f"</div>"
    )

    return textwrap.dedent(f"""\
        <!doctype html>
        <html lang="ja">
        <head>
        <meta charset="utf-8">
        <title>{title}</title>
        <style>{_CSS}</style>
        </head>
        <body>
        <div class="container">
        {body}
        {footer}
        </div>
        </body>
        </html>
    """)


# ------------------------------------------------------------------
# HTML → PNG (Chrome headless + Pillow trim)
# ------------------------------------------------------------------


def render_html_to_png(
    html_path: Path,
    png_path: Path,
    width: int = 1480,
    initial_height: int = 8000,
    scale: int = 2,
) -> None:
    chrome = _find_chrome()
    if chrome is None:
        raise RuntimeError(
            "Chrome / Chromium / Edge が見つかりません。インストールしてから再実行してください。"
        )
    subprocess.run(
        [
            chrome,
            "--headless=new",
            "--no-sandbox",
            "--hide-scrollbars",
            f"--window-size={width},{initial_height}",
            f"--force-device-scale-factor={scale}",
            f"--screenshot={png_path}",
            f"file://{html_path}",
        ],
        check=True,
        capture_output=True,
        timeout=90,
    )
    _trim_bottom_whitespace(png_path)


def _trim_bottom_whitespace(png_path: Path, padding: int = 80) -> None:
    """末尾の Pearl 色 (#F4F0E8) で構成された無コンテンツ領域を切り落とす."""
    try:
        img = Image.open(png_path).convert("RGB")
    except Exception:
        return

    pearl = (244, 240, 232)
    w, h = img.size
    pixels = img.load()

    last_content_row = 0
    sample_xs = list(range(0, w, max(1, w // 64)))
    for y in range(h - 1, -1, -1):
        non_pearl = any(pixels[x, y] != pearl for x in sample_xs)
        if non_pearl:
            last_content_row = y
            break

    new_h = min(h, last_content_row + padding)
    if new_h < h - 50:
        img.crop((0, 0, w, new_h)).save(png_path, optimize=True)


# ------------------------------------------------------------------
# 公開ユーティリティ
# ------------------------------------------------------------------


def _default_output_dir() -> Path:
    env = os.environ.get("SCRIPT_REVIEW_OUTPUT")
    if env:
        return Path(env).expanduser()
    return Path.home() / "Desktop" / "script-review-output"


def render_diagnosis_report(
    markdown_text: str,
    output_dir: Optional[str] = None,
    title: str = "構造診断レポート",
    formats: Optional[list[str]] = None,
    base_name: Optional[str] = None,
) -> dict[str, str]:
    """診断レポート (md) を md/html/png 各形式で保存し、生成ファイルパスを返す.

    Args:
        markdown_text: 診断レポート本文 (markdown)
        output_dir: 出力ディレクトリ (省略時は ``~/Desktop/script-review-output/``)
        title: HTML/PNG のタイトル
        formats: ``["md", "html", "png"]`` のいずれか。省略時は全形式
        base_name: 出力ファイル名のベース。省略時は ``YYYY-MM-DD_HHMMSS_diagnosis``

    Returns:
        ``{"md": "...", "html": "...", "png": "..."}``
    """
    if formats is None:
        formats = ["md", "html", "png"]

    out_dir = Path(output_dir).expanduser() if output_dir else _default_output_dir()
    out_dir.mkdir(parents=True, exist_ok=True)

    if base_name is None:
        base_name = datetime.now().strftime("%Y-%m-%d_%H%M%S") + "_diagnosis"
    base = out_dir / base_name

    paths: dict[str, str] = {}

    if "md" in formats:
        md_path = base.with_suffix(".md")
        md_path.write_text(markdown_text, encoding="utf-8")
        paths["md"] = str(md_path)

    needs_html = "html" in formats or "png" in formats
    if needs_html:
        html_text = render_to_html(markdown_text, title=title)
        html_path = base.with_suffix(".html")
        html_path.write_text(html_text, encoding="utf-8")
        if "html" in formats:
            paths["html"] = str(html_path)

        if "png" in formats:
            png_path = base.with_suffix(".png")
            try:
                render_html_to_png(html_path, png_path)
                paths["png"] = str(png_path)
            except Exception as e:
                paths["png_error"] = (
                    f"PNG レンダリング失敗 ({e}). HTML は生成済み: {html_path}"
                )

    return paths
