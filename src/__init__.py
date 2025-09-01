"""
RTK GNSS Worker 包初始化
"""

__version__ = "1.0.0"
__author__ = "RTK GNSS Team"
__description__ = "RTK GNSS Worker for precise positioning"

from .gnss_worker import GNSSWorker
from .config import Config

__all__ = ['GNSSWorker', 'Config']
