# 本機 API 先導執行程式：第二版

第二版修正首次真實試跑暴露的介面問題：提供完整 JSON 欄位規格，明確要求
平面的介入機率表，禁止 Markdown 包裝，並把評分器實際使用的 Hoeffding
相容性規則提供給全部組別。這些都是事後開發修正；新舊版本不得合併當成
同一個事先固定的實驗。本次舊結果的檢查見 RESULTS_REVIEW_ZH.md。

這個版本使用 OpenAI API，直接在你的電腦執行。需要 Python 3.10 或以上，
不需要另外安裝 Python 套件。請先解壓整個 ZIP，不要只從 ZIP 內打開單一檔案。

## Windows 最簡單的執行方式

雙擊 Run_Pilot.cmd，依畫面輸入：

1. 案例數：1 是小批連線試跑，共 4 次請求；12 是完整先導，共 48 次請求。
2. 你的 API 帳戶可使用的模型 ID，必須填實際 ID，程式不預設模型。
3. API key。輸入時不會顯示字元，貼上後按 Enter 即可。

已設定 OPENAI_API_KEY 或 OPENAI_MODEL 環境變數時，程式會直接使用。
金鑰只放在目前程式的執行環境，不寫入程式、設定、紀錄或結果 ZIP。

## 沿用這次 Macquarie 代理的執行設定

第二版保留你對傳輸層的修正，支援 OPENAI_API_BASE 並設定 User-Agent。
在 PowerShell 裡，可沿用這次紀錄中的網址及模型別名：

```powershell
$env:OPENAI_API_BASE = "<institutional-litellm-proxy>"
python run_local.py --model azure/gpt-5.2 --tasks 1
```

金鑰仍在提示時輸入。若這個小批試跑的初始回答有效，且摘要顯示實質證據
回饋確實送達，再執行 --tasks 12。若格式仍失敗，先回傳結果，不要反覆跑
完整批次挑選成功版本。模型名稱是代理回傳的別名，未核實底層模型快照。

## 終端機執行

在這個資料夾開啟 PowerShell 或終端機：

```sh
python run_local.py
```

也可以指定模型與完整先導：

```sh
python run_local.py --model YOUR_MODEL_ID --tasks 12
```

只檢查本機程式及檔案、不呼叫 API：

```sh
python run_local.py --dry-run --tasks 12
```

預設每次請求 max_output_tokens 為 4096，包含模型的可見輸出與推理 token。
若更改這個上限，需對所有組別一致設定，並保留設定紀錄。
API 使用會按你的帳戶收費；本程式不預估價格、不把未知費用寫成零。
每次請求預設最多等待 180 秒；可用 OPENAI_REQUEST_TIMEOUT_SECONDS
環境變數調整至 10–600 秒。逾時不自動重試。

## 結果在哪裡

results 下會建立新的時間戳資料夾與同名 results.zip：

- attempts.jsonl：全部原始回答、修訂、回饋與評分。
- provider_calls.jsonl：API 原始回應、模型名稱、response ID 與 token 用量。
- configuration.json：模型、上限、案例數與執行設定，不含金鑰。
- run_status.json：完成情況及請求數。
- summary.csv、summary.json、summary.txt：四組的描述性比較摘要。

摘要另列出「初始回答可接受實質回饋的數量」及「實際收到實質回饋的修訂
數量」。初始回答格式錯誤時，證據組只收到格式錯誤，不能當成實質驗證的
效果測試。格式失敗輸出的 unsupported claim 計數為零，不代表推論安全。

把產生的 results.zip 提供給研究協作者即可；不需要提供金鑰。
若 API 驗證、模型存取、額度或網路連線失敗，程式會保存失敗紀錄並停止，
不自動重試。查看 provider_calls.jsonl 中的 HTTP 狀態與錯誤回應。
模型輸出格式錯誤則仍然保留並繼續比較，不能手工修好後代替原始輸出。

## 研究範圍與比較

四組共用初始回答：原始回答、自行修訂、僅格式回饋修訂、實質證據回饋修訂。
12 個案例測試既定候選機制的形式化與推論，並非無限制的新機制發現。
public_tasks.json 提供模型問題；evaluator_only.json 的真值不送進模型。
案例與組別有相依性，因此摘要只做描述性比較，不自動產生顯著性檢定。

先跑的 1 個案例屬於執行可行性檢查，應與正式 12 案例的結果分開保留。
完整保留不利結果；不要只回報較成功的一次執行。

## 驗證與文件

```sh
python -m unittest discover -v
```

第二版準備環境已通過 44 項離線及模擬傳輸測試，沒有使用真實 API 金鑰
跑第二版模型。上傳的第一版真實結果已另外核對；不以模擬結果替代它。
API 介面參考：
https://developers.openai.com/api/docs/guides/text
https://developers.openai.com/api/docs/quickstart

如使用其他模型供應商，需替換 provider adapter；此版本不自動把 OpenAI
金鑰送到其他網址。
