"""
race CSV ファイル解析モジュール
race フォルダ内のすべての CSV ファイルを読み込み、START/GOAL 時刻を抽出
"""

import os
import glob
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, Tuple
import re
from logging_config import get_logger

# ロガー取得
logger = get_logger(__name__)


class RaceParser:
    """race CSV ファイル解析クラス"""
    
    def __init__(self, race_folder: str = "race"):
        self.race_folder = race_folder
        # start_time[ゼッケン][区間名] = 時刻文字列
        self.start_time = {}
        # goal_time[ゼッケン][区間名] = 時刻文字列
        self.goal_time = {}
        logger.info(f"RaceParser初期化: フォルダ={race_folder}")
        
    def parse_all(self) -> Tuple[bool, str]:
        """race フォルダ内のすべての CSV ファイルを解析
        
        Returns:
            (成功: bool, エラーメッセージ: str)
        """
        csv_files = glob.glob(os.path.join(self.race_folder, "*.csv"))
        
        if len(csv_files) == 0:
            return False, "race フォルダに CSV ファイルが見つかりません"
        
        for csv_file in csv_files:
            success, msg = self._parse_file(csv_file)
            if not success:
                return False, f"{os.path.basename(csv_file)}: {msg}"
        
        return True, f"{len(csv_files)}件のファイルを解析しました"
    
    def _parse_filename(self, filename: str) -> list:
        """ファイル名から区間情報を抽出
        
        Args:
            filename: ファイル名（例: "PC1START.csv", "PC1GOAL_PC2START.csv"）
        
        Returns:
            [(区間名, START/GOAL), ...] のリスト
        """
        basename = os.path.splitext(os.path.basename(filename))[0]
        
        # パターン: 区間名 + START or GOAL
        # 例: PC1START, PC1GOAL_PC2START
        results = []
        
        # アンダースコアで分割
        parts = basename.split('_')
        
        for part in parts:
            # 区間名とSTART/GOALを分離
            match = re.match(r'([A-Z]+\d+)(START|GOAL)', part)
            if match:
                section = match.group(1)
                timing = match.group(2)
                results.append((section, timing))
        
        return results
    
    def _parse_file(self, filepath: str) -> Tuple[bool, str]:
        """1つの CSV ファイルを解析
        
        Args:
            filepath: CSV ファイルパス
        
        Returns:
            (成功: bool, エラーメッセージ: str)
        """
        try:
            # ファイル名から区間情報を取得
            section_info = self._parse_filename(filepath)
            if len(section_info) == 0:
                return True, ""  # 無視
            
            # CSV 読み込み
            df = pd.read_csv(filepath, encoding='utf-8-sig')
            
            # time 列を探す
            time_col_idx = None
            for idx, col in enumerate(df.columns):
                if 'time' in col.lower():
                    time_col_idx = idx
                    break
            
            if time_col_idx is None:
                return False, "time 列が見つかりません"
            
            time_col = df.columns[time_col_idx]
            
            # number 列は time の右側
            if time_col_idx + 1 >= len(df.columns):
                return False, "number 列が見つかりません（time 列の右側にありません）"
            
            number_col = df.columns[time_col_idx + 1]
            
            # ゼッケンごとに時刻を抽出
            zekken_found = {}
            
            for _, row in df.iterrows():
                number = row[number_col]
                
                # number が空でない行のみ処理
                if pd.isna(number) or number == '':
                    continue
                
                try:
                    zekken = int(float(number))
                except (ValueError, TypeError):
                    continue
                
                # 同一ファイル内で同じゼッケンが複数回出現
                if zekken in zekken_found:
                    return False, f"ゼッケン {zekken} が複数回出現しています"
                
                time_val = row[time_col]
                if pd.isna(time_val):
                    continue
                
                time_str = str(time_val).strip()
                zekken_found[zekken] = time_str
                
                # 各区間情報に対して時刻を記録
                for section_name, timing_type in section_info:
                    if timing_type == 'START':
                        if zekken not in self.start_time:
                            self.start_time[zekken] = {}
                        self.start_time[zekken][section_name] = time_str
                    elif timing_type == 'GOAL':
                        if zekken not in self.goal_time:
                            self.goal_time[zekken] = {}
                        self.goal_time[zekken][section_name] = time_str
            
            return True, ""
        
        except Exception as e:
            return False, f"ファイル解析エラー: {str(e)}"
    
    def get_passage_time(self, zekken: int, section: str) -> Tuple[bool, float]:
        """指定されたゼッケンと区間の通過時間（秒）を取得
        
        Args:
            zekken: ゼッケン番号
            section: 区間名
        
        Returns:
            (データあり: bool, 通過時間: float)
        """
        # START と GOAL がそろっているか確認
        if zekken not in self.start_time or section not in self.start_time[zekken]:
            return False, 0.0
        if zekken not in self.goal_time or section not in self.goal_time[zekken]:
            return False, 0.0
        
        start_str = self.start_time[zekken][section]
        goal_str = self.goal_time[zekken][section]
        
        try:
            # 時刻文字列をパース
            start_dt = self._parse_time(start_str)
            goal_dt = self._parse_time(goal_str)
            
            # 差分を計算（秒）
            diff = (goal_dt - start_dt).total_seconds()
            
            # 日をまたいだ場合の処理
            if diff < 0:
                diff += 24 * 3600
            
            return True, diff
        
        except Exception:
            return False, 0.0
    
    def _parse_time(self, time_str: str) -> datetime:
        """時刻文字列を datetime にパース
        
        Args:
            time_str: 時刻文字列（例: "14:27:56.28"）
        
        Returns:
            datetime オブジェクト
        """
        # 複数のフォーマットに対応
        formats = [
            "%H:%M:%S.%f",
            "%H:%M:%S",
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(time_str, fmt)
            except ValueError:
                continue
        
        raise ValueError(f"時刻フォーマットが不正です: {time_str}")
    
    def has_start(self, zekken: int, section: str) -> bool:
        """START 時刻があるか"""
        return zekken in self.start_time and section in self.start_time[zekken]
    
    def has_goal(self, zekken: int, section: str) -> bool:
        """GOAL 時刻があるか"""
        return zekken in self.goal_time and section in self.goal_time[zekken]
    
    def get_all_zekkens(self) -> set:
        """すべてのゼッケン番号を取得"""
        zekkens = set()
        zekkens.update(self.start_time.keys())
        zekkens.update(self.goal_time.keys())
        return zekkens
    
    def get_pcg_passage_time(self, zekken: int, start_section: str, 
                              goal_section: str) -> Tuple[bool, float]:
        """PCG 区間の通過時間を取得
        
        Args:
            zekken: ゼッケン番号
            start_section: 開始区間名（例: PC1）
            goal_section: 終了区間名（例: PC5）
        
        Returns:
            (データあり: bool, 通過時間: float)
        """
        # START と GOAL がそろっているか確認
        if zekken not in self.start_time or start_section not in self.start_time[zekken]:
            return False, 0.0
        if zekken not in self.goal_time or goal_section not in self.goal_time[zekken]:
            return False, 0.0
        
        start_str = self.start_time[zekken][start_section]
        goal_str = self.goal_time[zekken][goal_section]
        
        try:
            # 時刻文字列をパース
            start_dt = self._parse_time(start_str)
            goal_dt = self._parse_time(goal_str)
            
            # 差分を計算（秒）
            diff = (goal_dt - start_dt).total_seconds()
            
            # 日をまたいだ場合の処理
            if diff < 0:
                diff += 24 * 3600
            
            return True, diff
        
        except Exception:
            return False, 0.0
