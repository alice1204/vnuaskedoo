import os
import logging
from typing import Optional
from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.database import Database

load_dotenv()

logger = logging.getLogger(__name__)

MONGODB_URI = os.getenv("MONGODB_URI")
MONGODB_DB_NAME = os.getenv("MONGODB_DB_NAME", "kltn_scheduler")
USE_MONGODB = os.getenv("USE_MONGODB", "true").lower() in ("true", "1", "yes")

_client: Optional[MongoClient] = None
_db: Optional[Database] = None
_connection_checked: bool = False
_is_connected: bool = False


def get_db() -> Optional[Database]:
    """
    Trả về đối tượng Database của MongoDB.
    Nếu USE_MONGODB=false hoặc không thể kết nối tới server, trả về None (để service fallback sang file).
    """
    global _client, _db, _connection_checked, _is_connected

    if not USE_MONGODB or not MONGODB_URI:
        return None

    if _db is not None:
        return _db

    if _connection_checked and not _is_connected:
        return None

    try:
        _client = MongoClient(
            MONGODB_URI,
            serverSelectionTimeoutMS=4000,
            connectTimeoutMS=4000,
        )
        # Kiểm tra kết nối nhanh bằng lệnh ping
        _client.admin.command("ping")
        _db = _client[MONGODB_DB_NAME]
        _is_connected = True
        logger.info(f"Kết nối thành công tới MongoDB Database: {MONGODB_DB_NAME}")
        return _db
    except Exception as e:
        logger.warning(f"Không thể kết nối tới MongoDB Atlas: {e}. Hệ thống sẽ sử dụng dữ liệu cục bộ (Fallback).")
        _is_connected = False
        _client = None
        _db = None
        return None
    finally:
        _connection_checked = True


def is_mongo_connected() -> bool:
    """Kiểm tra MongoDB có đang khả dụng không."""
    return get_db() is not None


def get_collection(name: str):
    """Lấy một collection theo tên từ MongoDB, trả về None nếu không kết nối được."""
    db = get_db()
    if db is not None:
        return db[name]
    return None
