import os
import shutil
import sqlite3
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional
from zoneinfo import ZoneInfo
from agent_am.config.settings import settings

logger = logging.getLogger("agent_am.backup_manager")

class BackupManager:
    """
    خودکار ڈیٹا بیس بیک اپ اور تصدیق شدہ بحالی سروس
    SQLite3 کے لائیو آن لائن بیک اپ API کی مدد سے محفوظ اسنیپ شاٹس تیار کرتا ہے۔
    """

    def __init__(self, db_path: str = "./agent_am.db", backup_dir: str = "./backups"):
        self.db_path = Path(db_path).resolve()
        self.backup_dir = Path(backup_dir).resolve()
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.tz = ZoneInfo("Asia/Karachi")

    def create_backup(self, label: str = "auto") -> Dict[str, Any]:
        """
        لائیو ڈیٹا بیس کا مکمل محفوظ اور وقتی اسنیپ شاٹ بناتا ہے
        """
        if not self.db_path.exists():
            return {
                "success": False,
                "error": f"ڈیٹا بیس فائل موجود نہیں ہے: {self.db_path}",
                "backup_path": None
            }

        timestamp_str = datetime.now(self.tz).strftime("%Y%m%d_%H%M%S")
        backup_filename = f"agent_am_{label}_{timestamp_str}.db"
        target_path = self.backup_dir / backup_filename

        try:
            # SQLite آن لائن بیک اپ API کا استعمال تاکہ چلتے ہوئے سسٹم میں کرپشن نہ ہو
            src_conn = sqlite3.connect(str(self.db_path))
            dst_conn = sqlite3.connect(str(target_path))
            with dst_conn:
                src_conn.backup(dst_conn)
            dst_conn.close()
            src_conn.close()

            # فوری سالمیت کی تصدیق (Integrity Check)
            is_valid, check_msg = self.verify_backup(str(target_path))
            if not is_valid:
                target_path.unlink(missing_ok=True)
                return {
                    "success": False,
                    "error": f"بیک اپ فائل کی سالمیت فیل ہو گئی: {check_msg}",
                    "backup_path": None
                }

            file_size_kb = round(target_path.stat().st_size / 1024, 2)
            logger.info(f"ڈیٹا بیس کا بیک اپ کامیابی سے تیار ہوا: {backup_filename} ({file_size_kb} KB)")

            # پرانے بیک اپس کی چھانٹی (Keep latest 14)
            self.prune_backups(keep_count=14)

            return {
                "success": True,
                "backup_path": str(target_path),
                "backup_filename": backup_filename,
                "size_kb": file_size_kb,
                "timestamp": timestamp_str
            }
        except Exception as e:
            logger.error(f"بیک اپ بنانے میں خرابی: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "backup_path": None
            }

    def verify_backup(self, backup_path: str) -> (bool, str):
        """
        کسی بھی بیک اپ فائل کی ساخت اور سالمیت کی جانچ کرتا ہے
        """
        path = Path(backup_path)
        if not path.exists():
            return False, "فائل موجود نہیں ہے"

        try:
            conn = sqlite3.connect(str(path))
            cur = conn.cursor()
            res = cur.execute("PRAGMA integrity_check;").fetchone()
            conn.close()
            if res and res[0].lower() == "ok":
                return True, "OK"
            return False, f"Integrity check failed: {res}"
        except Exception as e:
            return False, str(e)

    def restore_backup(self, backup_path: str, target_db: Optional[str] = None) -> Dict[str, Any]:
        """
        کسی مخصوص بیک اپ سے ڈیٹا بیس کو بحال کرتا ہے
        """
        b_path = Path(backup_path)
        dst_path = Path(target_db).resolve() if target_db else self.db_path

        # 1. بیک اپ کی جانچ
        is_valid, msg = self.verify_backup(str(b_path))
        if not is_valid:
            return {
                "success": False,
                "error": f"بیک اپ بحال نہیں ہو سکتا کیونکہ اس کی فائل درست نہیں: {msg}"
            }

        try:
            # موجودہ ڈیٹا بیس کا سیفٹی اسنیپ شاٹ لیں قبل از بحالی
            if dst_path.exists():
                pre_restore_backup = dst_path.parent / f"{dst_path.stem}_pre_restore_{datetime.now(self.tz).strftime('%Y%m%d_%H%M%S')}.db"
                shutil.copy2(dst_path, pre_restore_backup)

            shutil.copy2(b_path, dst_path)
            logger.info(f"ڈیٹا بیس کامیابی سے بحال کر دی گئی: {b_path.name} -> {dst_path.name}")
            return {
                "success": True,
                "restored_from": str(b_path),
                "target_db": str(dst_path),
                "message_urdu": "ڈیٹا بیس کامیابی کے ساتھ بحال ہو چکی ہے۔"
            }
        except Exception as e:
            logger.error(f"بحالی میں خرابی: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

    def list_backups(self) -> List[Dict[str, Any]]:
        """تمام موجودہ بیک اپس کی فہرست تاریخ کے لحاظ سے لاتا ہے"""
        backups = []
        for f in sorted(self.backup_dir.glob("*.db"), key=lambda x: x.stat().st_mtime, reverse=True):
            backups.append({
                "filename": f.name,
                "path": str(f),
                "size_kb": round(f.stat().st_size / 1024, 2),
                "created_at": datetime.fromtimestamp(f.stat().st_mtime, tz=self.tz).strftime("%Y-%m-%d %I:%M %p")
            })
        return backups

    def prune_backups(self, keep_count: int = 14):
        """اضافی پرانے بیک اپس کو ہٹاتا ہے تاکہ ڈسک پر بوجھ نہ بنے"""
        backups = sorted(self.backup_dir.glob("agent_am_*.db"), key=lambda x: x.stat().st_mtime, reverse=True)
        if len(backups) > keep_count:
            for old_file in backups[keep_count:]:
                try:
                    old_file.unlink(missing_ok=True)
                    logger.debug(f"پرانا بیک اپ ہٹایا گیا: {old_file.name}")
                except Exception as e:
                    logger.warning(f"پرانا بیک اپ ہٹانے میں تنبیہ: {str(e)}")

backup_manager = BackupManager()
