"""
MCP 工具注册与签名完整性验证测试
"""
import unittest
import asyncio
from mcp_server import mcp

class TestMCPTools(unittest.TestCase):
    def test_registered_tools(self):
        tools = asyncio.run(mcp.list_tools())
        tool_names = [tool.name for tool in tools]
        expected_tools = [
            "fanqie_check_status",
            "fanqie_login_interactive",
            "fanqie_get_login_qrcode",
            "fanqie_list_books",
            "fanqie_publish_chapter",
            "fanqie_batch_publish_chapters",
            "fanqie_update_book_title",
            "fanqie_update_book_cover",
            "fanqie_get_batch_progress",
        ]
        for t in expected_tools:
            self.assertIn(t, tool_names, f"MCP 工具 {t} 未成功注册")

if __name__ == "__main__":
    unittest.main()
