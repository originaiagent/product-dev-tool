# ファイルアップロード機能拡張 - 実装概要

## ✅ 実装完了

Product Dev Toolのファイルアップロード機能を大幅に拡張しました。

### 📁 対応ファイル形式

- 🖼️ **画像**: jpg, jpeg, png, gif, bmp, webp
- 📄 **PDF**: pdf（テキスト自動抽出）
- 📊 **Excel**: xlsx, xls（全シート読み込み）
- 📈 **CSV**: csv, tsv（エンコーディング自動判定）
- 📝 **Word**: docx, doc（テキスト抽出）
- 📃 **テキスト**: txt, md, json

---

## 📦 追加ファイル

### 1. コアモジュール

#### `modules/file_processor.py`
ファイル処理の中核クラス
- 各種ファイル形式の読み込み・変換
- テキスト自動抽出
- 画像のbase64エンコード
- エラーハンドリング

#### `modules/file_upload_widget.py`
再利用可能なStreamlitウィジェット
- 統合ファイルアップロードUI
- サマリー表示
- プレビュー機能
- データ抽出ヘルパー関数

### 2. ドキュメント

#### `docs/FILE_UPLOAD_GUIDE.md`
詳細な使い方とAPIリファレンス
- 基本的な使用方法
- サンプルコード
- エラーハンドリング
- 実装例

### 3. テストページ

#### `pages/99_ファイルアップロードテスト.py`
機能テスト用のデモページ
- 基本アップロードテスト
- ファイルタイプ別テスト
- データ抽出とプレビュー

### 4. 依存関係更新

#### `requirements.txt`
追加された依存関係：
- `PyPDF2>=3.0.0` - PDF処理
- `openpyxl>=3.1.0` - Excel処理
- `python-docx>=1.1.0` - Word処理

---

## 🔄 変更されたファイル

### `pages/02_競合分析.py`

**変更内容:**
1. `FileProcessor`のインポート追加
2. 画像のみ → 全ファイル形式対応に変更
3. ファイルから自動テキスト抽出機能
4. AI分析時に抽出テキストも含める

**主な変更点:**
```python
# 変更前: 画像のみ
uploaded_images = st.file_uploader(
    "画像をアップロード（最大30枚）",
    type=["jpg", "jpeg", "png"],
    accept_multiple_files=True
)

# 変更後: 全形式対応
uploaded_files = st.file_uploader(
    "ファイルをアップロード（画像・PDF・Excel・CSV等、最大30ファイル）",
    type=FileProcessor.get_all_extensions(),
    accept_multiple_files=True
)
```

---

## 🚀 使い方

### 既存機能の改善（競合分析）

1. 競合分析ページで「競合を追加」
2. ファイルアップロード欄から様々な形式のファイルをアップロード可能に
   - Amazonの商品画像（PNG/JPG）
   - 競合の仕様書（PDF）
   - 価格比較表（Excel/CSV）
3. 「🤖 情報を自動抽出」でAI分析
   - 画像だけでなく、PDFやExcelから抽出したテキストもAI分析に含まれる

### 新機能のテスト

テストページを起動：
```bash
streamlit run main.py
```
サイドバーから「99_ファイルアップロードテスト」ページを選択

---

## 💡 他のページへの適用方法

### パターン1: 簡単な方法（推奨）

```python
from modules.file_upload_widget import render_file_uploader, extract_text_from_files

processed_files = render_file_uploader(
    key="unique_key",
    label="ファイルをアップロード",
    max_files=30
)

if processed_files:
    text = extract_text_from_files(processed_files)
    # テキストを使った処理...
```

### パターン2: 詳細制御

```python
from modules.file_processor import FileProcessor

uploaded_files = st.file_uploader(
    "ファイルをアップロード",
    type=FileProcessor.get_all_extensions(),
    accept_multiple_files=True
)

if uploaded_files:
    for file in uploaded_files:
        result = FileProcessor.process_file(file)
        # result["text"], result["base64"] などを使用
```

---

## 📊 処理できるデータ例

### PDFファイル
- 競合の製品カタログ
- 技術仕様書
- マーケティング資料

### Excelファイル
- 価格比較表
- 機能マトリックス
- レビュー集計データ

### CSVファイル
- レビューデータ（大量）
- 売上データ
- 顧客フィードバック

### Wordファイル
- 製品説明文書
- プロジェクト企画書

---

## 🎯 主な機能

1. **自動形式判定** - 拡張子から自動でファイルタイプを判定
2. **テキスト自動抽出** - PDF、Excel、Word等から自動でテキスト抽出
3. **エンコーディング自動判定** - CSV等でUTF-8/Shift-JIS自動判定
4. **エラーハンドリング** - ファイルごとにエラーを個別管理
5. **AI連携** - 抽出したテキストをそのままAI分析に活用可能

---

## 📝 注意事項

### 制限事項
- PDFのテキスト抽出は最初の10ページまで
- Excelの表示は最初の3シートまで
- CSVのプレビューは最初の20行まで
- 画像のAI送信は最大5枚まで（処理速度のため）

### トラブルシューティング

**依存関係エラーが出る場合:**
```bash
python3 -m pip install -r requirements.txt
```

**ファイルが読み込めない場合:**
- ファイルが破損していないか確認
- ファイル形式が対応しているか確認
- エラーメッセージを確認（処理結果の"error"キー）

---

## 🔗 関連ドキュメント

- [詳細ガイド](docs/FILE_UPLOAD_GUIDE.md) - API仕様と使用例
- [テストページ](pages/99_ファイルアップロードテスト.py) - 実装サンプル

---

## ✨ まとめ

これで Product Dev Tool は、画像だけでなく、PDF、Excel、CSV、Word など幅広いファイル形式に対応できるようになりました！

**主な改善点:**
- ✅ 6種類のファイル形式に対応
- ✅ 自動テキスト抽出
- ✅ AI分析への統合
- ✅ 再利用可能なモジュール設計
- ✅ テストページで機能確認可能

ご質問やご要望があればお気軽にどうぞ！
