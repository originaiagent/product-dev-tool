# ファイルアップロード機能拡張ガイド

## 📚 概要

Product Dev Toolのファイルアップロード機能を大幅に拡張しました。以下のファイル形式に対応しています：

### サポートファイル形式

| カテゴリ | 拡張子 | 説明 |
|---------|--------|------|
| 🖼️ **画像** | jpg, jpeg, png, gif, bmp, webp | 画像ファイル（AI分析に送信可能） |
| 📄 **PDF** | pdf | PDFドキュメント（テキスト自動抽出） |
| 📊 **Excel** | xlsx, xls | Excelスプレッドシート（全シート読み込み） |
| 📈 **CSV** | csv, tsv | CSVファイル（UTF-8/Shift-JIS自動判定） |
| 📝 **Word** | docx, doc | Wordドキュメント（テキスト抽出） |
| 📃 **テキスト** | txt, md, json | プレーンテキストファイル |

---

## 🚀 使い方

### 1. 競合分析ページでの使用

`pages/02_競合分析.py` で既に実装済みです。

**使用方法：**
1. 競合を追加
2. 「ファイルをアップロード」ボタンから、画像・PDF・Excel・CSVなど様々なファイルをアップロード
3. ファイルから自動的にテキストを抽出
4. 「🤖 情報を自動抽出」ボタンでAI分析

**特徴：**
- 最大30ファイルまで一度にアップロード可能
- 画像はbase64エンコードしてAIに送信
- PDF、Excel、CSVなどからテキストを自動抽出してAI分析に含める

---

### 2. 他のページでの使用方法

#### 方法A: FileProcessorクラスを直接使用

```python
from modules.file_processor import FileProcessor

# ファイルアップローダー
uploaded_files = st.file_uploader(
    "ファイルをアップロード",
    type=FileProcessor.get_all_extensions(),
    accept_multiple_files=True
)

if uploaded_files:
    processed_files = []
    for file in uploaded_files:
        result = FileProcessor.process_file(file)
        processed_files.append(result)
    
    # サマリー表示
    summary = FileProcessor.create_summary(processed_files)
    st.info(summary)
    
    # 全テキストを抽出
    all_text = FileProcessor.extract_all_text(processed_files)
    
    # 画像を抽出（AI送信用）
    images = FileProcessor.get_images_for_ai(processed_files, max_images=5)
```

#### 方法B: 統合ウィジェットを使用（推奨）

```python
from modules.file_upload_widget import render_file_uploader, extract_text_from_files, extract_images_from_files

# ファイルアップロードウィジェット
processed_files = render_file_uploader(
    key="my_uploader",
    label="ファイルをアップロード",
    max_files=30,
    show_summary=True,
    show_preview=True
)

if processed_files:
    # テキスト抽出
    text = extract_text_from_files(processed_files)
    st.text_area("抽出テキスト", text, height=200)
    
    # 画像抽出
    images = extract_images_from_files(processed_files, max_images=5)
    st.write(f"画像数: {len(images)}")
```

---

## 🔧 FileProcessorクラス API

### メソッド

#### `process_file(uploaded_file) -> Dict`

単一ファイルを処理して、以下の辞書を返します：

```python
{
    "type": "image" | "pdf" | "excel" | "csv" | "word" | "text",
    "filename": str,
    "content": str | bytes | pd.DataFrame,
    "base64": str,  # 画像/PDFの場合
    "text": str,    # テキスト抽出可能な場合
    "error": str    # エラーがある場合
}
```

#### `get_all_extensions() -> List[str]`

サポートする全ての拡張子を取得

#### `get_file_type(filename: str) -> Optional[str]`

ファイル名からタイプを判定

#### `create_summary(processed_files: List[Dict]) -> str`

処理したファイルのサマリーテキストを生成

#### `extract_all_text(processed_files: List[Dict]) -> str`

全ファイルからテキストを抽出して結合

#### `get_images_for_ai(processed_files: List[Dict], max_images: int) -> List[str]`

AI送信用の画像をbase64形式で取得

---

## 📊 データ抽出例

### Excelファイルの場合

```python
result = FileProcessor.process_file(uploaded_excel)

# 複数シートのDataFrameを取得
if result["type"] == "excel":
    df_dict = result["content"]  # {"Sheet1": DataFrame, "Sheet2": DataFrame, ...}
    for sheet_name, df in df_dict.items():
        st.write(f"Sheet: {sheet_name}")
        st.dataframe(df)

# テキストとして取得
text = result["text"]  # CSVフォーマットのテキスト
```

### PDFファイルの場合

```python
result = FileProcessor.process_file(uploaded_pdf)

# テキスト抽出（最大10ページ）
text = result["text"]
st.text_area("PDFテキスト", text)

# base64エンコードデータ（AI送信用）
pdf_base64 = result["base64"]
```

### CSVファイルの場合

```python
result = FileProcessor.process_file(uploaded_csv)

# DataFrameとして取得
df = result["content"]
st.dataframe(df)

# テキストとして取得
text = result["text"]  # 最初の20行
```

---

## 🎨 統合ウィジェット

### render_file_uploader()

引数：
- `key`: ウィジェットの一意なキー（必須）
- `label`: 表示ラベル（デフォルト: "ファイルをアップロード"）
- `max_files`: 最大ファイル数（デフォルト: 30）
- `show_summary`: サマリー表示するか（デフォルト: True）
- `show_preview`: プレビュー表示するか（デフォルト: True）
- `allowed_types`: 許可するファイルタイプ（デフォルト: None=全て）

例：

```python
# 画像のみ許可
processed_files = render_file_uploader(
    key="image_only",
    label="画像をアップロード",
    allowed_types=["jpg", "jpeg", "png"]
)

# Excel/CSVのみ許可
processed_files = render_file_uploader(
    key="data_only",
    label="データファイルをアップロード",
    allowed_types=["xlsx", "xls", "csv"]
)
```

---

## 💡 実装例：レビュー分析ページ

```python
from modules.file_upload_widget import render_file_uploader, extract_text_from_files

st.title("📊 レビュー分析")

# ファイルアップロード
processed_files = render_file_uploader(
    key="reviews",
    label="レビューファイルをアップロード（Excel/CSV/テキスト）",
    allowed_types=["xlsx", "xls", "csv", "txt"],
    max_files=10
)

if processed_files:
    # テキスト抽出
    review_text = extract_text_from_files(processed_files)
    
    # AI分析ボタン
    if st.button("🤖 レビューを分析"):
        with st.spinner("分析中..."):
            response = ai_provider.generate_with_retry(
                prompt=f"以下のレビューを分析してください：\n\n{review_text}",
                task="analyze"
            )
            st.write(response)
```

---

## 🔍 エラーハンドリング

各ファイルの処理結果に `error` キーが含まれている場合、エラーが発生しています：

```python
for pf in processed_files:
    if pf.get("error"):
        st.error(f"{pf['filename']}: {pf['error']}")
    else:
        # 正常に処理された
        st.success(f"{pf['filename']}: 処理完了")
```

---

## 📦 依存関係

以下のライブラリが `requirements.txt` に追加されています：

```
PyPDF2>=3.0.0      # PDF処理
openpyxl>=3.1.0    # Excel処理
python-docx>=1.1.0 # Word処理
```

既にインストール済みです。

---

## 🎯 まとめ

1. **競合分析ページ**では既に実装済み
2. 他のページで使う場合は **`render_file_uploader()`** を使うのが最も簡単
3. より細かい制御が必要な場合は **`FileProcessor`** クラスを直接使用
4. PDF、Excel、CSV等から自動でテキスト抽出され、AI分析に活用できる

ご質問があればお気軽にどうぞ！
