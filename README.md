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

```bash
export GOOGLE_API_KEY=... 
export GOOGLE_CLOUD_PROJECT=... 
export GOOGLE_CLOUD_LOCATION=... 
export GOOGLE_GENAI_USE_VERTEXAI=True

paper2exp run https://arxiv.org/abs/2511.14460 --no-exec --download-pdf --llm gemini
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

LLM/エージェント関連フラグ:

- `--llm {none|gemini}` (default: none)
- `--llm-model <model_id>` (default: gemini-2.5-flash)
- `--download-pdf` (default: false)
- `--agent` (default: false)
- `--max-agent-steps <int>` (default: 2)
- `--allow-network` / `--allow-package-install` / `--allow-write-repo` (default: false)

## LLM の安全設計（要点）

- “書いてないことは言わない”を厳守
- LLM 出力は構造化 JSON + evidence を要求
- URL/コマンドは本文一致＋evidence が無い限り破棄
- secrets はログ/ファイルに出力しません

## 注意

- `--no-exec` 単体では LLM も PDF も呼びません（後方互換）
- ネットワークアクセスは `--allow-network` が明示されたときのみ
- 破壊的コマンドは実行しません
