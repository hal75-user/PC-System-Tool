"""
計算エンジンモジュール
通過時間、差分、順位、得点を計算
"""

from typing import Dict, List, Tuple, Optional
from config_loader import ConfigLoader
from race_parser import RaceParser


class Result:
    """1つの区間の結果を保持するクラス"""
    
    def __init__(self):
        self.passage_time: Optional[float] = None  # 通過時間（秒）
        self.diff: Optional[float] = None  # 差分（秒）
        self.rank: Optional[int] = None  # 順位
        self.point: int = 0  # 得点
        self.status: Optional[str] = None  # RIT, N.C., BLNK
        

class CalculationEngine:
    """計算エンジンクラス"""
    
    def __init__(self, config_loader: ConfigLoader, race_parser: RaceParser,
                 co_point: int = 500):
        self.config = config_loader
        self.race = race_parser
        self.co_point = co_point
        
        # results[ゼッケン][区間名] = Result
        self.results: Dict[int, Dict[str, Result]] = {}
        
        # 競技ステータス管理: status_map[ゼッケン][区間名] = "RIT" or "N.C." or "BLNK"
        self.status_map: Dict[int, Dict[str, str]] = {}
        
        # 最終結果ステータス: final_status[ゼッケン] = "RIT" or "N.C." or "BLNK"
        self.final_status: Dict[int, str] = {}
    
    def calculate_all(self):
        """すべての計算を実行"""
        # 全ゼッケンを取得
        zekkens = self.race.get_all_zekkens()
        
        # entries に登録されているゼッケンも追加
        zekkens.update(self.config.entries_dict.keys())
        
        # 各ゼッケンの結果を初期化
        for zekken in zekkens:
            self.results[zekken] = {}
        
        # section の順序で区間を処理
        for section_name in self.config.get_section_order():
            section_type = self._get_section_type(section_name)
            
            if section_type == "PC":
                self._calculate_pc(section_name)
            elif section_type == "CO":
                self._calculate_co(section_name)
            elif section_type == "PCG":
                self._calculate_pcg(section_name)
    
    def _get_section_type(self, section_name: str) -> str:
        """区間名から競技タイプを取得"""
        if section_name.startswith("PC") and not section_name.startswith("PCG"):
            return "PC"
        elif section_name.startswith("PCG"):
            return "PCG"
        elif section_name.startswith("CO"):
            return "CO"
        return "UNKNOWN"
    
    def _calculate_pc(self, section_name: str):
        """PC 区間の計算"""
        target_time = self.config.section_dict.get(section_name)
        if target_time is None:
            return
        
        # 各ゼッケンの通過時間と差分を計算
        passage_data = []  # (ゼッケン, 通過時間, 差分の絶対値)
        
        for zekken in self.results.keys():
            result = Result()
            
            # ステータス確認
            status = self._get_status(zekken, section_name)
            if status:
                result.status = status
                self.results[zekken][section_name] = result
                continue
            
            # 通過時間を取得
            has_data, passage_time = self.race.get_passage_time(zekken, section_name)
            
            if has_data:
                result.passage_time = passage_time
                result.diff = passage_time - target_time
                
                # 順位付け用データ
                passage_data.append((zekken, passage_time, abs(result.diff)))
            
            self.results[zekken][section_name] = result
        
        # 順位付け（差分の絶対値が小さい順）
        passage_data.sort(key=lambda x: x[2])
        
        for rank, (zekken, _, _) in enumerate(passage_data, start=1):
            self.results[zekken][section_name].rank = rank
            # 得点付与
            point = self.config.point_dict.get(rank, 0)
            self.results[zekken][section_name].point = point
    
    def _calculate_co(self, section_name: str):
        """CO 区間の計算"""
        target_time = self.config.section_dict.get(section_name)
        if target_time is None:
            return
        
        for zekken in self.results.keys():
            result = Result()
            
            # ステータス確認
            status = self._get_status(zekken, section_name)
            if status:
                result.status = status
                self.results[zekken][section_name] = result
                continue
            
            # 通過時間を取得
            has_data, passage_time = self.race.get_passage_time(zekken, section_name)
            
            if has_data:
                result.passage_time = passage_time
                result.diff = passage_time - target_time
                
                # クリア判定（0〜59.99秒）
                if 0 <= result.diff < 60:
                    result.point = self.co_point
                else:
                    result.point = 0
            
            self.results[zekken][section_name] = result
    
    def _calculate_pcg(self, section_name: str):
        """PCG 区間の計算"""
        target_time = self.config.section_dict.get(section_name)
        if target_time is None:
            return
        
        # PCG が属する GROUP を取得
        group_num = self._get_group_num(section_name)
        if group_num is None:
            return
        
        # 同じ GROUP の PC 区間を取得
        pc_sections = self._get_pc_in_group(group_num)
        if len(pc_sections) < 2:
            return
        
        # 最初の PC と最後の PC
        start_section = pc_sections[0]
        goal_section = pc_sections[-1]
        
        # 各ゼッケンの通過時間と差分を計算
        passage_data = []  # (ゼッケン, 通過時間, 差分の絶対値)
        
        for zekken in self.results.keys():
            result = Result()
            
            # ステータス確認
            status = self._get_status(zekken, section_name)
            if status:
                result.status = status
                self.results[zekken][section_name] = result
                continue
            
            # 通過時間を取得
            has_data, passage_time = self.race.get_pcg_passage_time(
                zekken, start_section, goal_section)
            
            if has_data:
                result.passage_time = passage_time
                result.diff = passage_time - target_time
                
                # 順位付け用データ
                passage_data.append((zekken, passage_time, abs(result.diff)))
            
            self.results[zekken][section_name] = result
        
        # 順位付け（差分の絶対値が小さい順）
        passage_data.sort(key=lambda x: x[2])
        
        for rank, (zekken, _, _) in enumerate(passage_data, start=1):
            self.results[zekken][section_name].rank = rank
            # 得点付与
            point = self.config.point_dict.get(rank, 0)
            self.results[zekken][section_name].point = point
    
    def _get_group_num(self, section_name: str) -> Optional[int]:
        """指定された区間の GROUP 番号を取得"""
        if self.config.section_df is None:
            return None
        
        row = self.config.section_df[self.config.section_df['section'] == section_name]
        if len(row) == 0:
            return None
        
        return int(row.iloc[0]['GROUP'])
    
    def _get_pc_in_group(self, group_num: int) -> List[str]:
        """指定された GROUP の PC 区間リストを取得（PCG を除外）"""
        if self.config.section_df is None:
            return []
        
        group_df = self.config.section_df[
            (self.config.section_df['GROUP'] == group_num) &
            (self.config.section_df['type'] == 'PC')
        ]
        
        return group_df['section'].tolist()
    
    def _get_status(self, zekken: int, section_name: str) -> Optional[str]:
        """指定されたゼッケンと区間のステータスを取得"""
        if zekken in self.status_map and section_name in self.status_map[zekken]:
            return self.status_map[zekken][section_name]
        return None
    
    def set_status(self, zekken: int, section_name: str, status: str):
        """競技ステータスを設定"""
        if zekken not in self.status_map:
            self.status_map[zekken] = {}
        self.status_map[zekken][section_name] = status
    
    def set_final_status(self, zekken: int, status: str):
        """最終結果ステータスを設定"""
        self.final_status[zekken] = status
    
    def get_total_score(self, zekken: int) -> int:
        """総合得点を計算
        
        総合得点 = (PC + PCG) * 係数 * 年齢係数 + CO
        
        注: final_statusがある場合でも得点は計算される（順位付けから除外されるのみ）
        """
        # entries 情報取得
        entry = self.config.entries_dict.get(zekken)
        if entry is None:
            return 0
        
        coef = entry['Coef']
        age_coef = entry['AgeCoef']
        
        pc_pcg_total = 0
        co_total = 0
        
        if zekken not in self.results:
            return 0
        
        for section_name, result in self.results[zekken].items():
            section_type = self._get_section_type(section_name)
            
            if section_type in ["PC", "PCG"]:
                pc_pcg_total += result.point
            elif section_type == "CO":
                co_total += result.point
        
        # 総合得点計算
        total = int(pc_pcg_total * coef * age_coef + co_total)
        return total
    
    def get_pure_score(self, zekken: int) -> int:
        """純粋な得点を計算（係数をかける前）
        
        Point = PC + PCG + CO
        """
        if zekken not in self.results:
            return 0
        
        total = 0
        for section_name, result in self.results[zekken].items():
            total += result.point
        
        return total
    
    def get_hcl_score(self, zekken: int) -> int:
        """H.C.L. Point を計算
        
        H.C.L. Point = (PC + PCG) * 係数 * 年齢係数 + CO
        """
        return self.get_total_score(zekken)
    
    def get_score_for_sections(self, zekken: int, sections: List[str]) -> int:
        """指定された区間のみの得点を計算
        
        Args:
            zekken: ゼッケン番号
            sections: 区間名のリスト
            
        Returns:
            指定区間の総合得点（int変換により小数点以下切り捨て）
            計算式: int((PC + PCG) * 係数 * 年齢係数 + CO)
            注: 得点は常に正の値であり、int()による0方向への切り捨てで問題ない
        """
        # entries 情報取得
        entry = self.config.entries_dict.get(zekken)
        if entry is None:
            return 0
        
        coef = entry['Coef']
        age_coef = entry['AgeCoef']
        
        pc_pcg_total = 0
        co_total = 0
        
        if zekken not in self.results:
            return 0
        
        # 指定された区間のみ集計
        for section_name in sections:
            if section_name not in self.results[zekken]:
                continue
            
            result = self.results[zekken][section_name]
            section_type = self._get_section_type(section_name)
            
            if section_type in ["PC", "PCG"]:
                pc_pcg_total += result.point
            elif section_type == "CO":
                co_total += result.point
        
        # 総合得点計算
        total = int(pc_pcg_total * coef * age_coef + co_total)
        return total
    
    def format_time(self, seconds: Optional[float]) -> str:
        """秒を時刻文字列にフォーマット（HH:MM:SS.SS）"""
        if seconds is None:
            return "ー"
        
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = seconds % 60
        
        return f"{hours:02d}:{minutes:02d}:{secs:05.2f}"
    
    def format_diff(self, seconds: Optional[float]) -> str:
        """差分を文字列にフォーマット（±HH:MM:SS.SS）"""
        if seconds is None:
            return "ー"
        
        sign = "+" if seconds >= 0 else "-"
        abs_seconds = abs(seconds)
        
        hours = int(abs_seconds // 3600)
        minutes = int((abs_seconds % 3600) // 60)
        secs = abs_seconds % 60
        
        return f"{sign}{hours:02d}:{minutes:02d}:{secs:05.2f}"
