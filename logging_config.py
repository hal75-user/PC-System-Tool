"""
ロギング設定モジュール
アプリケーション全体のログ管理を行う
"""

import logging
import logging.handlers
from pathlib import Path
from datetime import datetime


def setup_logging(log_level=logging.INFO, log_to_file=True, log_to_console=True):
    """
    ロギング設定を初期化
    
    Args:
        log_level: ログレベル（logging.DEBUG, INFO, WARNING, ERROR, CRITICAL）
        log_to_file: ファイルへのログ出力を有効にするか
        log_to_console: コンソールへのログ出力を有効にするか
    
    Returns:
        設定されたロガー
    """
    # ログディレクトリ作成
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # ルートロガー取得
    logger = logging.getLogger("pc_system_tool")
    logger.setLevel(log_level)
    
    # 既存のハンドラをクリア（重複を防ぐ）
    logger.handlers.clear()
    
    # フォーマッター作成
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # ファイルハンドラ（ローテーション付き）
    if log_to_file:
        # 日付付きログファイル名
        log_filename = log_dir / f"app_{datetime.now().strftime('%Y%m%d')}.log"
        
        file_handler = logging.handlers.RotatingFileHandler(
            log_filename,
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    # コンソールハンドラ
    if log_to_console:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    
    # 初期化メッセージ
    logger.info("=" * 80)
    logger.info("PC System Tool - ロギングシステム初期化完了")
    logger.info(f"ログレベル: {logging.getLevelName(log_level)}")
    logger.info(f"ログディレクトリ: {log_dir.absolute()}")
    logger.info("=" * 80)
    
    return logger


def get_logger(name):
    """
    指定された名前のロガーを取得
    
    Args:
        name: ロガー名（通常は __name__ を使用）
    
    Returns:
        ロガーインスタンス
    """
    return logging.getLogger(f"pc_system_tool.{name}")


# グローバルロガーの初期化（アプリケーション起動時に一度だけ呼び出す）
_app_logger = None


def init_app_logging(log_level=logging.INFO):
    """
    アプリケーション全体のロギングを初期化
    
    Args:
        log_level: ログレベル
    
    Returns:
        アプリケーションロガー
    """
    global _app_logger
    if _app_logger is None:
        _app_logger = setup_logging(log_level)
    return _app_logger


def get_app_logger():
    """
    アプリケーションロガーを取得
    
    Returns:
        アプリケーションロガー（未初期化の場合は自動初期化）
    """
    global _app_logger
    if _app_logger is None:
        _app_logger = setup_logging()
    return _app_logger
