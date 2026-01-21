import unittest
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from modules.utils import parse_json_response

class TestJsonParser(unittest.TestCase):
    
    def test_standard_json(self):
        text = '{"key": "value", "list": [1, 2, 3]}'
        result = parse_json_response(text)
        self.assertEqual(result, {"key": "value", "list": [1, 2, 3]})
        
    def test_markdown_json(self):
        text = 'Here is the result:\n```json\n{"key": "value"}\n```'
        result = parse_json_response(text)
        self.assertEqual(result, {"key": "value"})

    def test_markdown_no_lang(self):
        text = '```\n{"key": "value"}\n```'
        result = parse_json_response(text)
        self.assertEqual(result, {"key": "value"})
        
    def test_python_dict(self):
        text = "{'key': 'value', 'list': [1, 2, 3]}"
        result = parse_json_response(text)
        self.assertEqual(result, {"key": "value", "list": [1, 2, 3]})
        
    def test_mixed_text(self):
        text = 'Sure, here is the JSON:\n\n{"key": "value"}\n\nHope this helps.'
        result = parse_json_response(text)
        self.assertEqual(result, {"key": "value"})
        
    def test_unterminated_string_extraction(self):
        # Simulating the case where simple split might fail but bracket search succeeds
        text = 'Prefix text {"key": "value with } inside"} Suffix text'
        result = parse_json_response(text)
        self.assertEqual(result, {"key": "value with } inside"})

    def test_list_parsing(self):
        text = '["item1", "item2"]'
        result = parse_json_response(text)
        self.assertEqual(result, ["item1", "item2"])

if __name__ == '__main__':
    unittest.main()
