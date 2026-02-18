"""
出力モジュール
Excel/CSV ファイルへの出力機能
"""

import pandas as pd
from typing import List
from calculation_engine import CalculationEngine
from config_loader import ConfigLoader


class OutputFormatter:
    """出力フォーマッタークラス"""
    
    def __init__(self, calc_engine: CalculationEngine, config_loader: ConfigLoader):
        self.calc = calc_engine
        self.config = config_loader
    
    def create_dataframe(self) -> pd.DataFrame:
        """結果を DataFrame に変換"""
        # ゼッケン一覧を取得（昇順）
        zekkens = sorted(self.calc.results.keys())
        
        # 区間一覧を section の順序で取得
        sections = self.config.get_section_order()
        
        # データを格納するリスト
        rows = []
        
        for zekken in zekkens:
            row_data = {'ゼッケン': zekken}
            
            for section in sections:
                if section not in self.calc.results[zekken]:
                    # データがない場合
                    row_data[f'{section}_通過時間'] = 'ー'
                    row_data[f'{section}_差分'] = 'ー'
                    row_data[f'{section}_順位'] = 'ー'
                    row_data[f'{section}_得点'] = 0
                    continue
                
                result = self.calc.results[zekken][section]
                
                # ステータスがある場合
                if result.status:
                    if result.status == "N.C.":
                        # N.C.の場合: タイム表示あり、差分算出、順位は除外
                        row_data[f'{section}_通過時間'] = self.calc.format_time(result.passage_time) if result.passage_time else 'ー'
                        row_data[f'{section}_差分'] = self.calc.format_diff(result.diff) if result.diff is not None else 'ー'
                        row_data[f'{section}_順位'] = result.status
                        row_data[f'{section}_得点'] = result.point
                    else:
                        # RIT, BLNKの場合: タイム表示無し
                        row_data[f'{section}_通過時間'] = result.status
                        row_data[f'{section}_差分'] = result.status
                        row_data[f'{section}_順位'] = result.status
                        row_data[f'{section}_得点'] = 0
                else:
                    # 通過時間
                    row_data[f'{section}_通過時間'] = self.calc.format_time(result.passage_time)
                    
                    # 差分
                    row_data[f'{section}_差分'] = self.calc.format_diff(result.diff)
                    
                    # 順位（PC/PCG のみ）
                    section_type = self.calc._get_section_type(section)
                    if section_type in ['PC', 'PCG'] and result.rank:
                        row_data[f'{section}_順位'] = result.rank
                    else:
                        row_data[f'{section}_順位'] = 'ー'
                    
                    # 得点
                    row_data[f'{section}_得点'] = result.point
            
            # 総合得点
            row_data['総合得点'] = self.calc.get_total_score(zekken)
            
            rows.append(row_data)
        
        df = pd.DataFrame(rows)
        return df
    
    def export_to_excel(self, filename: str = "result.xlsx") -> bool:
        """Excel ファイルに出力"""
        try:
            df = self.create_dataframe()
            
            # Excel ライターを作成
            with pd.ExcelWriter(filename, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='結果', index=False)
            
            return True
        
        except Exception as e:
            print(f"Excel 出力エラー: {e}")
            return False
    
    def export_to_csv(self, filename: str = "result.csv") -> bool:
        """CSV ファイルに出力"""
        try:
            df = self.create_dataframe()
            df.to_csv(filename, index=False, encoding='utf-8-sig')
            return True
        
        except Exception as e:
            print(f"CSV 出力エラー: {e}")
            return False
    
    def get_summary_dataframe(self) -> pd.DataFrame:
        """サマリー用の DataFrame を作成（総合順位）
        
        列:
        - Result (順位)
        - No (ゼッケン)
        - DriverName
        - CoDriverName
        - CarName
        - 車両製造年
        - CarClass
        - Point (純粋な得点)
        - H.C.L Point ((PC+PCG)*係数*年齢係数+CO)
        - Penalty(-) (ペナルティ点数)
        - TotalPoint (H.C.L. Point - Penalty)
        """
        # ゼッケンと総合得点のリストを作成
        data = []
        
        for zekken in sorted(self.calc.results.keys()):
            # entries 情報取得
            entry = self.config.entries_dict.get(zekken, {})
            
            # 得点計算
            pure_score = self.calc.get_pure_score(zekken)
            hcl_score = self.calc.get_hcl_score(zekken)
            
            # ペナルティ取得（AppConfigから）
            penalty = 0  # デフォルト値、実際の値は後でAppConfigから取得される
            
            # TotalPoint計算
            total_point = hcl_score - penalty
            
            # 最終結果ステータスを確認
            if zekken in self.calc.final_status:
                status = self.calc.final_status[zekken]
                rank = status  # ステータスを順位として記録（後で順位付けから除外される）
            else:
                rank = None
            
            data.append({
                'Result': rank,  # 順位（後で計算）
                'No': zekken,
                'DriverName': entry.get('DriverName', ''),
                'CoDriverName': entry.get('CoDriverName', ''),
                'CarName': entry.get('CarName', ''),
                '車両製造年': entry.get('CarYear', ''),
                'CarClass': entry.get('CarClass', ''),
                'Point': pure_score,
                'H.C.L Point': hcl_score,
                'Penalty(-)': penalty,  # 後で更新される
                'TotalPoint': total_point  # 後で更新される
            })
        
        # DataFrame 作成
        df = pd.DataFrame(data)
        
        # ステータスがないものを得点順にソート（TotalPointで）
        normal_df = df[df['Result'].isna()].copy()
        normal_df = normal_df.sort_values('H.C.L Point', ascending=False)
        normal_df['Result'] = range(1, len(normal_df) + 1)
        
        # ステータスがあるものと結合
        status_df = df[~df['Result'].isna()]
        
        result_df = pd.concat([normal_df, status_df], ignore_index=True)
        
        # 後方互換性のため、'No' を 'ゼッケン'、'Result' を '順位' としても参照できるようにする
        # ResultTableWidget (main_pyside6.py の line 994, 996) は 'ゼッケン' と '順位' 列を使用している
        # 将来的には ResultTableWidget を 'No' と 'Result' 列を使用するように変更することを推奨
        result_df['ゼッケン'] = result_df['No']
        result_df['順位'] = result_df['Result']
        
        return result_df
    
    def get_all_classes(self) -> List[str]:
        """すべての車両クラスを取得（重複なし、ソート済み）"""
        classes = set()
        for entry in self.config.entries_dict.values():
            car_class = entry.get('CarClass', '')
            if car_class:
                classes.add(car_class)
        return sorted(list(classes))
    
    def get_summary_by_class(self, class_name: str) -> pd.DataFrame:
        """クラス別の総合順位DataFrame を作成
        
        Args:
            class_name: 車両クラス名
        
        Returns:
            クラスに属するゼッケンのみの DataFrame（クラス内順位付け）
        """
        # まず全体のサマリーデータを取得
        all_data = []
        
        for zekken in sorted(self.calc.results.keys()):
            # entries 情報取得
            entry = self.config.entries_dict.get(zekken, {})
            
            # クラスフィルタリング
            if entry.get('CarClass', '') != class_name:
                continue
            
            # 得点計算
            pure_score = self.calc.get_pure_score(zekken)
            hcl_score = self.calc.get_hcl_score(zekken)
            
            # ペナルティ取得
            penalty = 0  # デフォルト値、実際の値は後でAppConfigから取得される
            
            # TotalPoint計算
            total_point = hcl_score - penalty
            
            # 最終結果ステータスを確認
            if zekken in self.calc.final_status:
                status = self.calc.final_status[zekken]
                rank = status  # ステータスを順位として記録
            else:
                rank = None
            
            all_data.append({
                'Result': rank,  # 順位（後で計算）
                'No': zekken,
                'DriverName': entry.get('DriverName', ''),
                'CoDriverName': entry.get('CoDriverName', ''),
                'CarName': entry.get('CarName', ''),
                '車両製造年': entry.get('CarYear', ''),
                'CarClass': entry.get('CarClass', ''),
                'Point': pure_score,
                'H.C.L Point': hcl_score,
                'Penalty(-)': penalty,  # 後で更新される
                'TotalPoint': total_point  # 後で更新される
            })
        
        # DataFrame 作成
        df = pd.DataFrame(all_data)
        
        if df.empty:
            return df
        
        # ステータスがないものをクラス内で得点順にソート
        normal_df = df[df['Result'].isna()].copy()
        normal_df = normal_df.sort_values('H.C.L Point', ascending=False)
        normal_df['Result'] = range(1, len(normal_df) + 1)
        
        # ステータスがあるものと結合
        status_df = df[~df['Result'].isna()]
        
        result_df = pd.concat([normal_df, status_df], ignore_index=True)
        
        # 後方互換性のため、'No' を 'ゼッケン'、'Result' を '順位' としても参照できるようにする
        # ResultTableWidget (main_pyside6.py の line 994, 996) は 'ゼッケン' と '順位' 列を使用している
        # 将来的には ResultTableWidget を 'No' と 'Result' 列を使用するように変更することを推奨
        result_df['ゼッケン'] = result_df['No']
        result_df['順位'] = result_df['Result']
        
        return result_df
