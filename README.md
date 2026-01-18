# Paper2Exp (MVP)

Paper2Exp は、論文参照（arXiv / HF Papers）から再現実験用のランバンドル、軽量ベンチ、簡潔なサマリを自動生成する最小構成のツールです。LLM（Gemini/Vertex AI）による「証拠ベースの spec 自動補完」にも対応します。

## インストール

```bash
pip install -e .
```

## クイックスタート

### 従来互換（no-exec）
外部実行/clone/bench/LLM/PDFダウンロードは行いません。

```bash
paper2exp run https://arxiv.org/abs/2511.14460 --no-exec
```

### LLM補完（no-exec + PDFダウンロード）
外部コマンド実行はせず、PDFを取得→テキスト抽出→Geminiで証拠付きパッチを生成し spec に反映します。

> 注意: PDF取得および LLM 呼び出しにはネットワークアクセスが必要です。  
> ネットワークアクセスは `--allow-network` が明示されたときのみ行います。

```bash
export GOOGLE_API_KEY=... 
export GOOGLE_CLOUD_PROJECT=... 
export GOOGLE_CLOUD_LOCATION=... 
export GOOGLE_GENAI_USE_VERTEXAI=True

paper2exp run https://arxiv.org/abs/2511.14460 --no-exec --download-pdf --llm gemini --allow-network
```

## バッチ実行

```bash
paper2exp batch configs/papers_seed.yaml --no-exec
```

## 出力アーティファクト

各 run は `runs/<timestamp>_<paper_id>/` に出力され、最低限以下を必ず生成します。

- `paper/metadata.json`
- `repro/spec.yaml`
- `repro/run.sh`
- `repro/results.jsonl`
- `repro/compare.md`
- `summary.md`
- `bench/report.md`
- `bench/results.json`

LLM を使用した場合は監査用に `runs/.../llm/` が追加されます。

- `llm/prompt.txt`
- `llm/schema.json`
- `llm/response.json`
- `llm/decision.md`

## CLI

- `paper2exp run <paper_ref> [--workdir <path>] [--mode smoke|repro] [--no-exec]`
- `paper2exp batch <config.yaml> [--no-exec]`
- `paper2exp report <run_dir>`
- `paper2exp paper-only --run <run_dir> [--lang ja|en] [--max-applications 6] [--no-llm] [--llm gemini]`

LLM/エージェント関連フラグ:

- `--llm {none|gemini}` (default: none)
- `--llm-model <model_id>` (default: gemini-2.5-flash)
- `--download-pdf` (default: false)
- `--agent` (default: false)
- `--max-agent-steps <int>` (default: 2)
- `--allow-network` / `--allow-package-install` / `--allow-write-repo` (default: false)

## 許可フラグ早見表

| 操作 | 必要な許可フラグ | 備考 |
|---|---|---|
| PDFダウンロード | `--allow-network` | `--download-pdf` と併用 |
| LLM呼び出し（Gemini） | `--allow-network` | `--llm gemini` と併用 |
| リポジトリclone/検証 | `--allow-network` | `git` 実行 |
| 依存導入（pip等） | `--allow-package-install` + `--allow-network` | wheelhouseがあればネット不要 |
| repoへの書き込み | `--allow-write-repo` | 書き換えが必要な場合 |

## LLM の安全設計（要点）

- “書いてないことは言わない”を厳守
- LLM 出力は構造化 JSON + evidence を要求
- URL/コマンドは本文一致＋evidence が無い限り破棄
- secrets はログ/ファイルに出力しません

## 注意

- `--no-exec` 単体では LLM も PDF も呼びません（後方互換）
- ネットワークアクセスは `--allow-network` が明示されたときのみ
- 破壊的コマンドは実行しません

## Troubleshooting（よくある詰まり）

- GitHub認証が必要: `could not read Username for 'https://github.com'`
- DNS/ネットワークでpipが失敗: `could not resolve host`
- pytestが無い: `No module named pytest`

## paper-only（参照モード）

run ディレクトリを参照して、facts / insights / applications を生成します（実行なし）。

```bash
paper2exp paper-only --run runs/<run_id> --lang ja --no-llm
```

生成物:
- `paper_only/facts.json`
- `paper_only/insights.json`
- `paper_only/applications.json`
- `paper_only/report.md`

LLM を使う場合は `paper_only/llm_*` に監査ファイルが保存されます。
