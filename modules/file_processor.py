"""
ファイル処理モジュール
- PDF、Excel、CSV、Word、画像などの読み込み・変換
"""
import base64
import io
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import pandas as pd
from PIL import Image

# オプショナル依存関係
try:
    import PyPDF2
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False

try:
    import openpyxl
    EXCEL_AVAILABLE = True
except ImportError:
    EXCEL_AVAILABLE = False

try:
    import docx
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False


class FileProcessor:
    """ファイル処理クラス"""
    
    # サポートするファイル形式
    SUPPORTED_FORMATS = {
        "image": ["jpg", "jpeg", "png", "gif", "bmp", "webp"],
        "pdf": ["pdf"],
        "excel": ["xlsx", "xls"],
        "csv": ["csv", "tsv"],
        "word": ["docx", "doc"],
        "text": ["txt", "md", "json"]
    }
    
    @classmethod
    def get_all_extensions(cls) -> List[str]:
        """サポートする全ての拡張子を取得"""
        extensions = []
        for format_list in cls.SUPPORTED_FORMATS.values():
            extensions.extend(format_list)
        return extensions
    
    @classmethod
    def get_file_type(cls, filename: str) -> Optional[str]:
        """ファイルタイプを判定"""
        ext = Path(filename).suffix.lower().lstrip(".")
        for file_type, extensions in cls.SUPPORTED_FORMATS.items():
            if ext in extensions:
                return file_type
        return None
    
    @classmethod
    def process_file(cls, uploaded_file) -> Dict:
        """
        アップロードファイルを処理
        
        Returns:
            {
                "type": "image" | "pdf" | "excel" | "csv" | "word" | "text",
                "filename": str,
                "content": str | bytes | pd.DataFrame,
                "base64": str (画像/PDFの場合),
                "text": str (テキスト抽出可能な場合),
                "error": str (エラーがある場合)
            }
        """
        result = {
            "filename": uploaded_file.name,
            "type": None,
            "content": None,
            "base64": None,
            "text": None,
            "error": None
        }
        
        file_type = cls.get_file_type(uploaded_file.name)
        result["type"] = file_type
        
        try:
            if file_type == "image":
                result = cls._process_image(uploaded_file, result)
            elif file_type == "pdf":
                result = cls._process_pdf(uploaded_file, result)
            elif file_type == "excel":
                result = cls._process_excel(uploaded_file, result)
            elif file_type == "csv":
                result = cls._process_csv(uploaded_file, result)
            elif file_type == "word":
                result = cls._process_word(uploaded_file, result)
            elif file_type == "text":
                result = cls._process_text(uploaded_file, result)
            else:
                result["error"] = f"非対応のファイル形式: {uploaded_file.name}"
        
        except Exception as e:
            result["error"] = f"ファイル処理エラー: {str(e)}"
        
        return result
    
    @staticmethod
    def _process_image(uploaded_file, result: Dict) -> Dict:
        """画像ファイルを処理"""
        # base64エンコード
        file_bytes = uploaded_file.read()
        result["base64"] = base64.b64encode(file_bytes).decode()
        result["content"] = file_bytes
        
        # 画像情報取得
        uploaded_file.seek(0)
        img = Image.open(uploaded_file)
        result["text"] = f"画像: {img.size[0]}x{img.size[1]}px, {img.format}"
        
        return result
    
    @staticmethod
    def _process_pdf(uploaded_file, result: Dict) -> Dict:
        """PDFファイルを処理"""
        if not PDF_AVAILABLE:
            result["error"] = "PDF処理にはPyPDF2が必要です"
            return result
        
        # base64エンコード（AIに送信可能に）
        file_bytes = uploaded_file.read()
        result["base64"] = base64.b64encode(file_bytes).decode()
        result["content"] = file_bytes
        
        # テキスト抽出
        uploaded_file.seek(0)
        try:
            pdf_reader = PyPDF2.PdfReader(uploaded_file)
            text_parts = []
            for i, page in enumerate(pdf_reader.pages[:10]):  # 最初の10ページ
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(f"--- Page {i+1} ---\n{page_text}")
            
            result["text"] = "\n\n".join(text_parts)
            if not result["text"]:
                result["text"] = f"PDF: {len(pdf_reader.pages)}ページ（テキスト抽出不可）"
        except Exception as e:
            result["text"] = f"PDF: テキスト抽出エラー ({str(e)})"
        
        return result
    
    @staticmethod
    def _process_excel(uploaded_file, result: Dict) -> Dict:
        """Excelファイルを処理"""
        if not EXCEL_AVAILABLE:
            result["error"] = "Excel処理にはopenpyxlが必要です"
            return result
        
        try:
            # Excelを読み込み
            df_dict = pd.read_excel(uploaded_file, sheet_name=None, engine='openpyxl')
            result["content"] = df_dict
            
            # テキスト抽出（最初のシート）
            text_parts = []
            for sheet_name, df in list(df_dict.items())[:3]:  # 最大3シート
                text_parts.append(f"=== Sheet: {sheet_name} ===")
                text_parts.append(df.head(20).to_csv(index=False))  # 最初の20行
            
            result["text"] = "\n\n".join(text_parts)
            
        except Exception as e:
            result["error"] = f"Excel読み込みエラー: {str(e)}"
        
        return result
    
    @staticmethod
    def _process_csv(uploaded_file, result: Dict) -> Dict:
        """CSVファイルを処理"""
        try:
            # CSVを読み込み（エンコーディング自動判定）
            uploaded_file.seek(0)
            try:
                df = pd.read_csv(uploaded_file, encoding='utf-8')
            except UnicodeDecodeError:
                uploaded_file.seek(0)
                df = pd.read_csv(uploaded_file, encoding='shift-jis')
            
            result["content"] = df
            
            # テキスト抽出
            result["text"] = f"CSV: {len(df)}行 x {len(df.columns)}列\n\n"
            result["text"] += df.head(20).to_csv(index=False)  # 最初の20行
            
        except Exception as e:
            result["error"] = f"CSV読み込みエラー: {str(e)}"
        
        return result
    
    @staticmethod
    def _process_word(uploaded_file, result: Dict) -> Dict:
        """Wordファイルを処理"""
        if not DOCX_AVAILABLE:
            result["error"] = "Word処理にはpython-docxが必要です"
            return result
        
        try:
            doc = docx.Document(uploaded_file)
            
            # テキスト抽出
            text_parts = []
            for i, para in enumerate(doc.paragraphs):
                if para.text.strip():
                    text_parts.append(para.text)
                if i >= 100:  # 最大100段落
                    break
            
            result["text"] = "\n\n".join(text_parts)
            result["content"] = result["text"]
            
        except Exception as e:
            result["error"] = f"Word読み込みエラー: {str(e)}"
        
        return result
    
    @staticmethod
    def _process_text(uploaded_file, result: Dict) -> Dict:
        """テキストファイルを処理"""
        try:
            # テキストを読み込み（エンコーディング自動判定）
            file_bytes = uploaded_file.read()
            try:
                text = file_bytes.decode('utf-8')
            except UnicodeDecodeError:
                text = file_bytes.decode('shift-jis')
            
            result["content"] = text
            result["text"] = text[:10000]  # 最初の10000文字
            
        except Exception as e:
            result["error"] = f"テキスト読み込みエラー: {str(e)}"
        
        return result
    
    @classmethod
    def create_summary(cls, processed_files: List[Dict]) -> str:
        """処理したファイルのサマリーを作成"""
        if not processed_files:
            return "ファイルがアップロードされていません"
        
        summary_parts = []
        
        # ファイルタイプ別にカウント
        type_counts = {}
        for pf in processed_files:
            file_type = pf.get("type", "unknown")
            type_counts[file_type] = type_counts.get(file_type, 0) + 1
        
        summary_parts.append(f"📁 合計 {len(processed_files)} ファイル:")
        for file_type, count in type_counts.items():
            emoji_map = {
                "image": "🖼️",
                "pdf": "📄",
                "excel": "📊",
                "csv": "📈",
                "word": "📝",
                "text": "📃"
            }
            emoji = emoji_map.get(file_type, "📦")
            summary_parts.append(f"  {emoji} {file_type}: {count}件")
        
        # エラーがある場合
        errors = [pf for pf in processed_files if pf.get("error")]
        if errors:
            summary_parts.append(f"\n⚠️ エラー: {len(errors)}件")
        
        return "\n".join(summary_parts)
    
    @classmethod
    def extract_all_text(cls, processed_files: List[Dict]) -> str:
        """全ファイルからテキストを抽出して結合"""
        text_parts = []
        
        for pf in processed_files:
            if pf.get("error"):
                continue
            
            filename = pf.get("filename", "unknown")
            text = pf.get("text", "")
            
            if text:
                text_parts.append(f"=== {filename} ===\n{text}")
        
        return "\n\n".join(text_parts)
    
    @classmethod
    def get_images_for_ai(cls, processed_files: List[Dict], max_images: int = 5) -> List[str]:
        """AI送信用の画像をbase64形式で取得"""
        images = []
        
        for pf in processed_files:
            if pf.get("type") == "image" and pf.get("base64"):
                images.append(pf["base64"])
                if len(images) >= max_images:
                    break
        
        return images
