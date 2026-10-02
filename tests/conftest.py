import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from auth import UserRepository  # noqa: E402
from stock import StockRepository  # noqa: E402


@pytest.fixture
def stock_repo(tmp_path):
    """A throw-away copy of the real stock file so tests never touch live data."""
    target = tmp_path / "stock.xlsx"
    shutil.copy(ROOT / "stock.xlsx", target)
    return StockRepository(target)


@pytest.fixture
def user_repo(tmp_path):
    return UserRepository(tmp_path / "users.json")
