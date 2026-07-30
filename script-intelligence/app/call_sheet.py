"""
VERSE – Continuity Script Intelligence
app/call_sheet.py (Backwards Compatibility Layer)

Re-exports call sheet parsing functions from app.parsers.call_sheet_parser.
"""

from app.parsers.call_sheet_parser import parse_call_sheet

__all__ = ["parse_call_sheet"]