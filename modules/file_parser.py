"""
ファイル解析モジュール
PDF/Excel/CSVからテキストを抽出
"""
from pathlib import Path
from typing import Dict, Any

class FileParser:
    """ファイル解析クラス"""
    
    def parse(self, file_path: str) -> Dict[str, Any]:
        """ファイルを解析してテキストデータを抽出"""
        path = Path(file_path)
        suffix = path.suffix.lower()
        
        if suffix == '.pdf':
            return self._parse_pdf(path)
        elif suffix == '.xlsx':
            return self._parse_excel(path)
        elif suffix == '.csv':
            return self._parse_csv(path)
        else:
            raise ValueError(f"未対応のファイル形式: {suffix}")
    
    def parse_bytes(self, content: bytes, filename: str) -> Dict[str, Any]:
        """バイトデータを解析"""
        suffix = Path(filename).suffix.lower()
        
        if suffix == '.pdf':
            return self._parse_pdf_bytes(content)
        elif suffix == '.xlsx':
            return self._parse_excel_bytes(content)
        elif suffix == '.csv':
            return self._parse_csv_bytes(content)
        else:
            raise ValueError(f"未対応のファイル形式: {suffix}")
    
    def _parse_pdf(self, path: Path) -> Dict[str, Any]:
        import fitz  # PyMuPDF
        doc = fitz.open(path)
        text = ""
        for page in doc:
            text += page.get_text()
        doc.close()
        return {"type": "pdf", "text": text}
    
    def _parse_pdf_bytes(self, content: bytes) -> Dict[str, Any]:
        import fitz
        doc = fitz.open(stream=content, filetype="pdf")
        text = ""
        for page in doc:
            text += page.get_text()
        doc.close()
        return {"type": "pdf", "text": text}
    
    def _parse_excel(self, path: Path) -> Dict[str, Any]:
        import pandas as pd
        df = pd.read_excel(path)
        return {"type": "excel", "text": df.to_string(), "columns": list(df.columns), "row_count": len(df)}
    
    def _parse_excel_bytes(self, content: bytes) -> Dict[str, Any]:
        import pandas as pd
        from io import BytesIO
        df = pd.read_excel(BytesIO(content))
        return {"type": "excel", "text": df.to_string(), "columns": list(df.columns), "row_count": len(df)}
    
    def _parse_csv(self, path: Path) -> Dict[str, Any]:
        import pandas as pd
        df = pd.read_csv(path)
        return {"type": "csv", "text": df.to_string(), "columns": list(df.columns), "row_count": len(df)}
    
    def _parse_csv_bytes(self, content: bytes) -> Dict[str, Any]:
        import pandas as pd
        from io import BytesIO
        df = pd.read_csv(BytesIO(content))
        return {"type": "csv", "text": df.to_string(), "columns": list(df.columns), "row_count": len(df)}
