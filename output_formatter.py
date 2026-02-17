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
        """サマリー用の DataFrame を作成（総合順位）"""
        # ゼッケンと総合得点のリストを作成
        data = []
        
        for zekken in sorted(self.calc.results.keys()):
            # 最終結果ステータスを確認
            if zekken in self.calc.final_status:
                status = self.calc.final_status[zekken]
                data.append({
                    'ゼッケン': zekken,
                    '総合得点': 0,
                    '順位': status
                })
            else:
                total_score = self.calc.get_total_score(zekken)
                data.append({
                    'ゼッケン': zekken,
                    '総合得点': total_score,
                    '順位': None
                })
        
        # DataFrame 作成
        df = pd.DataFrame(data)
        
        # ステータスがないものを得点順にソート
        normal_df = df[df['順位'].isna()].copy()
        normal_df = normal_df.sort_values('総合得点', ascending=False)
        normal_df['順位'] = range(1, len(normal_df) + 1)
        
        # ステータスがあるものと結合
        status_df = df[~df['順位'].isna()]
        
        result_df = pd.concat([normal_df, status_df], ignore_index=True)
        return result_df
