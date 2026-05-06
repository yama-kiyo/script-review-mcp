# script-review-mcp

連載ドラマ・映画・小説の脚本／プロット (`.docx`) を **構造診断** する MCP サーバー。

Claude Code / Claude Desktop / その他 MCP クライアント上で、自然言語で脚本を渡すだけで:

- **シリーズアーク** の起承転結バランス
- **各話の機能**（情報開示 / 関係変化 / 状況変化 / 感情変化）
- **感情アーク 6 種**（Reagan & Mitchell 2016）の判定
- **主要キャラの動機線** と納得感
- **テーマの貫徹度**

を 5 レイヤーで診断し、**改善ポイントごとに 3 つの対応策（保守的修正 / 中規模リライト / 構造踏み込み）+ 各々のトレードオフ + 工数感** を提示するレポートを生成します。

> 設計思想: AI は「正解を押し付ける批評家」ではなく「**書き手が次の一歩を踏み出すための助言者**」であるべき。
> 強みを先に十分に挙げ、改善は方向性として伝える。最終判断は常に書き手が握る。

---

## こんな方に

- 連載ドラマや長編脚本を書いていて、**全体構造のセカンドオピニオン** が欲しい脚本家・監督
- AI ビデオ制作で生成された脚本の **品質チェック** を仕組み化したい制作会社
- 物語構造の理論（三幕構成 / Save the Cat / 6 感情アーク）を**自分の作品に当てはめて** 学びたい人
- 自分の作風に合わせた診断観点を **カスタマイズ** したい上級ユーザー

---

## インストール

Python 3.11 以上が必要です。

```bash
git clone https://github.com/yama-kiyo/script-review-mcp.git
cd script-review-mcp
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -e .
```

### Claude Code に登録

```bash
claude mcp add script-review --scope user -- \
  "$(pwd)/.venv/bin/python" -m script_review_mcp
```

確認:

```bash
claude mcp list | grep script-review
# → script-review: ... - ✓ Connected
```

### Claude Desktop に登録

`~/Library/Application Support/Claude/claude_desktop_config.json` に追記:

```json
{
  "mcpServers": {
    "script-review": {
      "command": "/path/to/script-review-mcp/.venv/bin/python",
      "args": ["-m", "script_review_mcp"]
    }
  }
}
```

---

## 使い方

Claude に話しかけるだけ:

```
この脚本を構造診断してください
/path/to/your/script.docx
```

Claude が `review_script` ツールを呼び出して docx を読み込み、5レイヤーの診断レポートをマークダウンで返します。

> **注**: MCP の Prompts 機能（`/script-review` 形式のスラッシュコマンド）は Claude Code v2.1 系で引数渡しが安定動作しないため、**Tool 経由のチャット呼び出しを推奨**します。Prompt も登録されているので、対応クライアントなら使えます。

### 入力フォーマット

`.docx` ファイル。以下の脚本フォーマットに対応:

- **連載脚本**: `第１話` `第2話` のような行で各話を区切る（全角・半角どちらでも可）
- **単話脚本 / プロット**: エピソード境界が見つからない場合は全文を 1 話として扱う

シーン記号 `〇` `◯` の有無は問いません（参考程度に使用）。

---

## 5 レイヤー診断観点

### Layer 1. シリーズアーク全体

第1話のフック / 中盤の起伏 / 終盤の盛り上がり / 最終話の決着 を独立に評価。

### Layer 2. 各話の機能

各話を 4 種類（情報開示 / 関係変化 / 状況変化 / 感情変化）に分類。機能が薄い話・重複する話を可視化。

### Layer 3. 感情アーク 6 種判定

Reagan & Mitchell (2016) の物語アーク分類:

1. Rags to Riches — 上昇のみ
2. Riches to Rags — 下降のみ
3. Man in a Hole — 下降→上昇
4. Icarus — 上昇→下降
5. Cinderella — 上昇→下降→上昇
6. Oedipus — 下降→上昇→下降

### Layer 4. 主要キャラの動機線

各キャラの「第1話時点の動機 / 終盤の動機 / 動機の変化 / 納得感（5段階）」を表形式で評価。

### Layer 5. テーマの貫徹度

顕在テーマ / 潜在テーマ / 結末との整合性。

---

## 出力レポートの構造

```
# 構造診断レポート — [作品タイトル]

## 総合評価
- 総合スコア: ◯◯/100
- 連載ドラマとしての完成度: ◯◯/10
- 30秒で語る所感: 3行以内

## レイヤー1〜5 の診断
（各観点の所見）

## 強み（3点）
（具体的シーンを引用）

## 改善ポイント・対応策（3点、各3案付き）

### ポイント1【優先度: 高】
**現状**: ...
**対応策（3案）**:

A案. 保守的最小修正
  - やること / 効果 / トレードオフ / 工数（軽中重）
B案. 中規模リライト
  - 同上
C案. 構造踏み込み
  - 同上

**推奨**: A/B/C + 理由（最終判断は書き手）

### ポイント2 ...
### ポイント3 ...

## 全体としての修正優先順位
最初に着手すべき1項目を1つだけ推す
```

**A=保守 / B=中規模 / C=踏み込み** の3段階を意図的に作ることで、書き手の状況・スケジュール・気力に応じた選択を可能にします。

---

## カスタマイズ（自分の作風に合わせる）

`src/script_review_mcp/prompts/script_all.md` が診断プロンプトのテンプレートです。コピーして `script_all.local.md` を作ると、それが自動的に優先されます。

```bash
cd src/script_review_mcp/prompts/
cp script_all.md script_all.local.md
# 自分の作風観点を追記
```

`*.local.md` は `.gitignore` 済み。**Push されません**。

カスタマイズ例:
- 「あなたは [自分の名前] の専属ドラマトゥルクです」と persona を埋める
- 自分の作風観点（例: 「構造美と人間心理の両立を志向する」「説明セリフを徹底排除する」）を追記
- 重視する観点に重みを付ける

---

## 注意点

- **AI診断は完璧ではありません**。生成された改善提案は参考意見として扱い、最終判断は書き手・脚本家・監督が行ってください。
- **個人の作風観点を込めたプロンプト** (`*.local.md`) は知財です。Public フォークに含めないよう `.gitignore` で保護しています。
- **クライアント機密スクリプト** をテストに使う場合は `*.private.docx` 形式で命名すれば `.gitignore` で除外されます。

---

## ロードマップ

- ✅ Phase 1: 連載脚本・全話通し構造診断 (`review_script` Tool)
- 🔜 Phase 2: 1話単位の三幕構成診断 (`review_episode`)
- 🔜 Phase 3: プロット用診断 (`review_plot`)
- 🔜 Phase 4: キャラ整合性チェック / セリフ品質診断 / IP安全性チェック

---

## 開発・コントリビュート

```bash
pip install -e ".[dev]"
pytest                 # （テストは Phase 2 以降で整備予定）
```

Issue / PR 歓迎です。特に:

- 別言語（英語脚本フォーマット等）への対応
- 別 NLE / 別フォーマット (Final Draft `.fdx`, Fountain 等) のローダー追加
- 診断観点の改善案

---

## ライセンス

MIT License — 商用利用、改変、再配布、私的利用、すべて自由です。詳細は [LICENSE](LICENSE)。

---

## 開発元

**PEARL株式会社 / Light Rewrite Studio**
山本清史 (Yamakiyo) — 映画監督・脚本家・映像プロデューサー

- Web: https://lightrewrite.jp/
- X: [@yama_kiyo](https://x.com/yama_kiyo)
- Email: yamakiyo@case.bz

このツールは PEARL の制作現場（連載ドラマ脚本のホン直しワークフロー）から生まれました。同じ課題を抱える書き手・制作者の助けになれば幸いです。
