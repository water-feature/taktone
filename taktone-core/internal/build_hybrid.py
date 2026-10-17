"""Digitone mk1 container layout used by the crossport."""
from types import SimpleNamespace
DEV = SimpleNamespace(name="Digitone mk1", main_section=3, main_load=0x40000400, stage=0x40200000, flash_at=0x80000, flash_limit=0x380000, trailer=None)
