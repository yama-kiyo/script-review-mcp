"""MCP サーバー本体 (FastMCP).

Claude Code から ``/script-review`` のスラッシュコマンドとして呼び出せる Prompts を公開する。
"""

from __future__ import annotations

from importlib.resources import files
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from .docx_loader import format_episode_index, load_script

mcp = FastMCP("script-review")


def _render_prompt(template_name: str, variables: dict[str, str]) -> str:
    """``prompts/`` 配下のテンプレートに ``{{var}}`` 置換を施して返す.

    ``foo.md`` を要求された場合、まず ``foo.local.md``（ユーザー個人の
    カスタマイズ版・公開対象外）を探し、なければ ``foo.md``（Generic 版）を
    使う。これにより、フレームワークは公開しつつ、各ユーザーが自身の作風に
    合わせた診断観点を ``*.local.md`` として手元に持てる。
    """
    base, ext = template_name.rsplit(".", 1)
    local_name = f"{base}.local.{ext}"
    prompts_pkg = files("script_review_mcp.prompts")

    local_path = prompts_pkg.joinpath(local_name)
    if local_path.is_file():
        template = local_path.read_text(encoding="utf-8")
    else:
        template = prompts_pkg.joinpath(template_name).read_text(encoding="utf-8")

    rendered = template
    for key, value in variables.items():
        rendered = rendered.replace(f"{{{{{key}}}}}", value)
    return rendered


def _build_script_all_prompt(docx_path: str) -> str:
    """共通ロジック: docx を読み込み、全話通し構造診断用のプロンプト文字列を組み立てる."""
    path = Path(docx_path).expanduser()
    doc = load_script(path)

    full_text = "\n".join(doc.full_lines)

    return _render_prompt(
        "script_all.md",
        {
            "title": doc.title,
            "episode_count": str(len(doc.episodes)),
            "char_count": f"{doc.char_count:,}",
            "episode_index": format_episode_index(doc),
            "full_text": full_text,
        },
    )


@mcp.tool(
    name="review_script",
    description=(
        "連載脚本（.docx）を読み込み、全話通しの構造診断指示書を生成する。"
        "監督が「この脚本を診断して」「構造を分析して」「シリーズ全体をレビューして」"
        "等と言ったときにこのツールを呼び出す。返り値の指示書を読み、"
        "そこに書かれた5レイヤー観点（シリーズアーク / 各話機能 / 感情アーク / "
        "キャラ動機線 / テーマ貫徹度）でマークダウン形式の診断レポートを書く。"
    ),
)
def review_script(docx_path: str) -> str:
    """連載脚本(.docx) の全話通し構造診断指示書を返す.

    Args:
        docx_path: 診断対象 .docx の絶対パス（ホームディレクトリ ~ 展開対応）
    """
    return _build_script_all_prompt(docx_path)


@mcp.prompt(
    name="script-review",
    description="連載脚本（.docx）の全話通し構造診断。シリーズアーク・感情アーク・キャラ動機線・テーマ貫徹度を5レイヤーで分析する。",
)
def script_review_all(docx_path: str) -> str:
    """連載脚本ファイルを読み込み、全話通しの構造診断プロンプトを返す.

    Args:
        docx_path: 診断対象 .docx の絶対パス
    """
    return _build_script_all_prompt(docx_path)


def main() -> None:
    """CLI / モジュール起動エントリポイント."""
    mcp.run()


if __name__ == "__main__":
    main()
