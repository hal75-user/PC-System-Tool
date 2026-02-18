"""
データ検証モジュール
レースデータの整合性をチェックし、エラーを検出する
"""

import os
import pandas as pd
from typing import List, Dict, Set, Tuple
from collections import defaultdict, Counter
import logging

logger = logging.getLogger(__name__)

# エラーメッセージのインデント定数
ERROR_MSG_INDENT = "  "       # エラーメッセージの基本インデント（2スペース）
DETAIL_INDENT = "    "        # 詳細情報のインデント（4スペース）
SUB_DETAIL_INDENT = "      "  # サブ詳細のインデント（6スペース）

# ログ出力時の配列の最大表示要素数
MAX_LOG_ITEMS = 10  # ログが長くなりすぎないように制限


class ValidationError:
    """検証エラーを表すクラス"""
    
    def __init__(self, error_type: str, message: str, details: Dict = None, allow_confirmation: bool = True):
        """
        Args:
            error_type: エラータイプ（例: "csv_duplicate", "zekken_duplicate"）
            message: エラーメッセージ
            details: エラーの詳細情報（同一エラー判定に使用）
            allow_confirmation: 確認済みステータスを許容するか
        """
        self.error_type = error_type
        self.message = message
        self.details = details or {}
        self.allow_confirmation = allow_confirmation
        self.confirmed = False
    
    def get_comparison_key(self) -> str:
        """同一エラー判定用のキーを生成"""
        if self.error_type == "csv_duplicate":
            # ファイル名重複: 区間名が同じ
            return f"{self.error_type}:{self.details.get('section', '')}"
        
        elif self.error_type == "zekken_duplicate":
            # ゼッケン重複: 区間とゼッケンが同じ
            return f"{self.error_type}:{self.details.get('section', '')}:{self.details.get('zekken', '')}"
        
        elif self.error_type == "section_order":
            # 区間通過順: 同一グループ・同一基準区間の場合は同一エラーとみなす
            group = self.details.get('group', '')
            first_section = self.details.get('first_section', '')
            return f"{self.error_type}:{group}:{first_section}"
        
        elif self.error_type == "zekken_order":
            # ゼッケン通過順: 同一ゼッケン・同一グループの場合は同一エラーとみなす
            zekken = self.details.get('zekken', '')
            group = self.details.get('group', '')
            return f"{self.error_type}:{zekken}:{group}"
        
        elif self.error_type == "invalid_status":
            # ステータス不正: 走行している区間とゼッケンとステータスが同じ
            section = self.details.get('section', '')
            zekken = self.details.get('zekken', '')
            status = self.details.get('status', '')
            return f"{self.error_type}:{section}:{zekken}:{status}"
        
        elif self.error_type == "measurement_type":
            # 計測タイプ確認: Tの時刻とゼッケンが同じ
            section = self.details.get('section', '')
            time = self.details.get('time', '')
            zekken = self.details.get('zekken', '')
            return f"{self.error_type}:{section}:{time}:{zekken}"
        
        elif self.error_type == "measurement_deficiency":
            # 計測データ不備: 区間が同じ
            section = self.details.get('section', '')
            return f"{self.error_type}:{section}"
        
        return f"{self.error_type}:{str(self.details)}"
    
    def __str__(self):
        return self.message


def truncate_for_log(items: List, max_items: int = MAX_LOG_ITEMS) -> str:
    """
    ログ出力用にリストを適切な長さに切り詰めて文字列化
    
    Args:
        items: 切り詰める対象のリスト
        max_items: 最大表示要素数
        
    Returns:
        切り詰められた文字列表現
    """
    truncated = str(items[:max_items])
    if len(items) > max_items:
        truncated += '...'
    return truncated


def validate_all(race_folder: str, results: List, sections: List, 
                 calc_engine=None) -> List[ValidationError]:
    """
    すべてのデータ検証を実行
    
    Args:
        race_folder: レースデータフォルダのパス
        results: レース結果のリスト
        sections: 区間設定のリスト
        calc_engine: 計算エンジン（計測データ不備チェックに使用、オプション）
        
    Returns:
        ValidationErrorのリスト
    """
    errors = []
    
    # 1. CSVファイル名重複チェック
    filename_errors = check_duplicate_filenames(race_folder)
    errors.extend(filename_errors)
    
    # 2. ゼッケン重複チェック
    zekken_dup_errors = check_duplicate_zekken_in_section(results)
    errors.extend(zekken_dup_errors)
    
    # 3. 区間通過順チェック
    section_order_errors = check_section_passage_order(results, sections)
    errors.extend(section_order_errors)
    
    # 4. ゼッケン通過順チェック
    zekken_order_errors = check_zekken_passage_order(results, sections)
    errors.extend(zekken_order_errors)
    
    # 5. ステータス不正チェック
    status_errors = check_invalid_status_with_time(results)
    errors.extend(status_errors)
    
    # 6. 計測タイプ確認
    type_errors = check_measurement_type(race_folder)
    errors.extend(type_errors)
    
    # 7. 計測データ不備確認（計算エンジンが利用可能な場合のみ）
    if calc_engine:
        deficiency_errors = check_measurement_deficiency(calc_engine, sections)
        errors.extend(deficiency_errors)
    
    return errors


def check_duplicate_filenames(race_folder: str) -> List[ValidationError]:
    """
    CSVファイル名重複チェック
    同じ区間名を持つファイルが複数存在しないかチェック
    
    例: PC3GOAL.csv と PC3GOAL_PC4START.csv が共存
    """
    errors = []
    
    if not race_folder or not os.path.exists(race_folder):
        return errors
    
    # CSVファイルをすべて取得
    csv_files = [f for f in os.listdir(race_folder) if f.endswith('.csv')]
    
    # 区間名をキーに、ファイル名のリストを作成
    section_to_files = defaultdict(list)
    
    for filename in csv_files:
        # ファイル名から区間名を抽出
        # 例: PC3GOAL.csv → PC3GOAL
        # 例: PC3GOAL_PC4START.csv → PC3GOAL, PC4START
        basename = filename[:-4]  # .csv を除去
        
        # _ で分割して区間名を取得
        parts = basename.split('_')
        for part in parts:
            if part:  # 空でない場合
                section_to_files[part].append(filename)
    
    # 重複をチェック
    for section, files in section_to_files.items():
        if len(files) > 1:
            error_msg = f"⚠️ CSVファイル名重複エラー\n"
            error_msg += f"区間 '{section}' が複数のファイルに存在します:\n"
            for f in files:
                error_msg += f"  - {f}\n"
            error_msg += "ファイル名を修正してください。"
            
            error = ValidationError(
                error_type="csv_duplicate",
                message=error_msg,
                details={"section": section, "files": files},
                allow_confirmation=False  # 確認を許容しない
            )
            errors.append(error)
    
    return errors


def check_duplicate_zekken_in_section(results: List) -> List[ValidationError]:
    """
    ゼッケン重複チェック
    同じ区間に同じゼッケンが2回以上出現しないかチェック
    """
    errors = []
    
    # 区間ごとにゼッケンをカウント
    section_zekken_count = defaultdict(lambda: Counter())
    
    for result in results:
        section = result.section
        zekken = result.zekken
        section_zekken_count[section][zekken] += 1
    
    # 2回以上出現するゼッケンを検出
    for section, zekken_counter in section_zekken_count.items():
        for zekken, count in zekken_counter.items():
            if count > 1:
                error_msg = f"⚠️ ゼッケン重複エラー\n"
                error_msg += f"区間 '{section}' でゼッケン {zekken} が{count}回出現しています。\n"
                error_msg += "CSVファイルを確認してください。"
                
                error = ValidationError(
                    error_type="zekken_duplicate",
                    message=error_msg,
                    details={"section": section, "zekken": zekken, "count": count},
                    allow_confirmation=False  # 確認を許容しない
                )
                errors.append(error)
    
    return errors


def check_section_passage_order(results: List, sections: List) -> List[ValidationError]:
    """
    区間通過順チェック
    同じグループ内の各区間で、ゼッケンの通過順序が一致するかチェック
    グループごとに1つのエラーを生成し、基準と異なる区間を詳細に記載
    """
    errors = []
    
    # グループごとに区間をグループ化
    group_sections = defaultdict(list)
    for section in sections:
        group = getattr(section, 'group', None) or getattr(section, 'GROUP', None)
        if group:
            group_sections[group].append(section)
    
    # グループごとに検証
    for group, group_section_list in group_sections.items():
        if len(group_section_list) < 2:
            continue  # 区間が1つしかない場合はスキップ
        
        # 各区間のゼッケン順序を取得
        section_zekken_orders = {}
        for section in group_section_list:
            section_name = section.section
            # この区間を通過したゼッケンを順番に取得
            zekken_list = []
            for result in results:
                if result.section == section_name and not result.status:
                    zekken_list.append(result.zekken)
            section_zekken_orders[section_name] = zekken_list
        
        # 基準区間（最初の区間）を取得
        first_section = group_section_list[0].section
        base_order = section_zekken_orders.get(first_section, [])
        
        if not base_order:
            continue  # 基準区間にデータがない場合はスキップ
        
        # グループ内の全区間の問題を収集
        section_issues = []
        
        # 他の区間と比較
        for section in group_section_list[1:]:
            section_name = section.section
            current_order = section_zekken_orders.get(section_name, [])
            
            if not current_order:
                continue  # データがない場合はスキップ
            
            # 順序が異なるかチェック
            # 基準区間にあるゼッケンの順序を比較
            base_set = set(base_order)
            current_set = set(current_order)
            
            # 共通するゼッケンの順序を確認
            common_zekken = base_set & current_set
            if len(common_zekken) < 2:
                continue  # 共通ゼッケンが少ない場合はスキップ
            
            # 基準区間での順序を取得
            base_common_order = [z for z in base_order if z in common_zekken]
            current_common_order = [z for z in current_order if z in common_zekken]
            
            # この区間の問題を記録
            section_detail = []
            
            # 順序が異なる場合
            if base_common_order != current_common_order:
                section_detail.append(f"{DETAIL_INDENT}通過順序が異なります:")
                section_detail.append(f"{SUB_DETAIL_INDENT}基準: {base_common_order}")
                section_detail.append(f"{SUB_DETAIL_INDENT}実際: {current_common_order}")
            
            # 歯抜けチェック（基準にあるが現在にない）
            missing = base_set - current_set
            if missing:
                section_detail.append(f"{DETAIL_INDENT}基準にあるゼッケンが欠けています: {sorted(missing)}")
            
            # 追加ゼッケンチェック（現在にあるが基準にない）
            extra = current_set - base_set
            if extra:
                section_detail.append(f"{DETAIL_INDENT}基準にないゼッケンがあります: {sorted(extra)}")
            
            # 問題があれば記録
            if section_detail:
                section_issues.append((section_name, section_detail))
        
        # グループに問題があれば1つのエラーを生成
        if section_issues:
            error_msg = f"⚠️ 区間通過順エラー\n"
            error_msg += f"グループ {group} で基準区間 {first_section} と異なる区間があります:\n"
            error_msg += f"{ERROR_MSG_INDENT}基準区間 {first_section} の通過順: {base_order}\n\n"
            
            for section_name, section_details in section_issues:
                error_msg += f"{ERROR_MSG_INDENT}【区間 {section_name}】\n"
                error_msg += '\n'.join(section_details) + '\n\n'
            
            error_msg += "確認してください。"
            
            # details には全ての問題のある区間情報を含める
            all_sections_with_issues = [s for s, _ in section_issues]
            
            error = ValidationError(
                error_type="section_order",
                message=error_msg,
                details={
                    "group": group,
                    "first_section": first_section,
                    "base_order": base_order,
                    "sections_with_issues": all_sections_with_issues
                },
                allow_confirmation=True
            )
            errors.append(error)
    
    return errors


def check_zekken_passage_order(results: List, sections: List) -> List[ValidationError]:
    """
    ゼッケン通過順チェック
    各ゼッケンがグループ内の区間を正しい順序で通過しているかチェック
    ゼッケンごと、グループごとに1つのエラーを生成し、逆転や歯抜けの詳細を記載
    """
    errors = []
    
    # グループごとに区間の正しい順序を取得
    group_section_order = defaultdict(list)
    for section in sections:
        group = getattr(section, 'group', None) or getattr(section, 'GROUP', None)
        if group:
            group_section_order[group].append(section.section)
    
    # ゼッケンごとに通過した区間を取得
    zekken_sections = defaultdict(lambda: defaultdict(list))
    for result in results:
        if not result.status:  # ステータスがない場合のみ
            group = None
            # この区間が属するグループを探す
            for section in sections:
                if section.section == result.section:
                    group = getattr(section, 'group', None) or getattr(section, 'GROUP', None)
                    break
            
            if group:
                zekken_sections[result.zekken][group].append(result.section)
    
    # ゼッケンごとに検証
    for zekken, group_passages in zekken_sections.items():
        for group, passed_sections in group_passages.items():
            expected_order = group_section_order[group]
            
            # 通過順序を比較するには最低2つの区間通過が必要
            # 1つ以下の場合は順序の検証ができないためスキップ
            if len(passed_sections) < 2:
                continue
            
            # 通過した区間の期待される順序を取得
            expected_passed = [s for s in expected_order if s in passed_sections]
            
            # 実際の通過順序と比較
            if passed_sections != expected_passed:
                # 詳細な問題箇所を特定
                problem_details = []
                
                # 逆転を検出（expected_passedに両方とも存在する区間のみ）
                # インデックスマップを作成してO(1)ルックアップを実現
                # これにより、以降のループ内でlist.index()を使うO(n²)を回避
                expected_passed_idx = {section: idx for idx, section in enumerate(expected_passed)}
                expected_order_idx = {section: idx for idx, section in enumerate(expected_order)}
                
                reversals = []
                for i in range(len(passed_sections) - 1):
                    curr_section = passed_sections[i]
                    next_section = passed_sections[i + 1]
                    
                    # 両方の区間が期待順序に含まれている場合のみチェック
                    if curr_section in expected_passed_idx and next_section in expected_passed_idx:
                        curr_idx = expected_passed_idx[curr_section]
                        next_idx = expected_passed_idx[next_section]
                        
                        # 逆転している場合
                        if curr_idx > next_idx:
                            reversals.append(f"{curr_section} → {next_section}")
                
                if reversals:
                    problem_details.append(f"{ERROR_MSG_INDENT}逆転: {', '.join(reversals)}")
                
                # 歯抜けを検出（通過すべきだったが通過していない区間）
                passed_set = set(passed_sections)
                expected_set = set(expected_passed)
                
                # 期待される区間の範囲を特定
                # expected_passed は expected_order のサブセットとして生成されるため通常は必ず含まれる
                # ただし、データの同時更新や不整合があった場合に備えて防御的にチェック
                if expected_passed:
                    # O(1)ルックアップを使用
                    first_expected_idx = expected_order_idx.get(expected_passed[0])
                    last_expected_idx = expected_order_idx.get(expected_passed[-1])
                    
                    if first_expected_idx is not None and last_expected_idx is not None:
                        # その範囲内で通過していない区間を検出
                        missing_sections = []
                        for idx in range(first_expected_idx, last_expected_idx + 1):
                            section = expected_order[idx]
                            if section not in passed_set:
                                missing_sections.append(section)
                        
                        if missing_sections:
                            problem_details.append(f"{ERROR_MSG_INDENT}歯抜け（未通過）: {', '.join(missing_sections)}")
                    else:
                        # データ不整合: expected_passedの要素がexpected_orderに存在しない
                        # この状況は、データ構造の同時更新や競合状態で発生する可能性がある
                        missing_elements = []
                        if first_expected_idx is None:
                            missing_elements.append(f"first={expected_passed[0]}")
                        if last_expected_idx is None:
                            missing_elements.append(f"last={expected_passed[-1]}")
                        
                        logger.warning(
                            f"データ不整合検出: ゼッケン {zekken} のグループ {group} で "
                            f"expected_passed の要素 [{', '.join(missing_elements)}] が "
                            f"expected_order に見つかりません。"
                            f"expected_passed={truncate_for_log(expected_passed)}, "
                            f"expected_order={truncate_for_log(expected_order)}"
                        )
                
                # エラーメッセージを構築
                error_msg = f"⚠️ ゼッケン通過順エラー\n"
                error_msg += f"ゼッケン {zekken} がグループ {group} で不正な順序で通過しています:\n\n"
                error_msg += f"{ERROR_MSG_INDENT}期待される順序: {' → '.join(expected_passed)}\n"
                error_msg += f"{ERROR_MSG_INDENT}実際の通過順序: {' → '.join(passed_sections)}\n\n"
                
                if problem_details:
                    error_msg += "【問題箇所】\n"
                    error_msg += '\n'.join(problem_details) + '\n\n'
                
                error_msg += "確認してください。"
                
                error = ValidationError(
                    error_type="zekken_order",
                    message=error_msg,
                    details={
                        "zekken": zekken,
                        "group": group,
                        "expected_passed": expected_passed,
                        "passed_sections": passed_sections
                    },
                    allow_confirmation=True
                )
                errors.append(error)
    
    return errors


def check_invalid_status_with_time(results: List) -> List[ValidationError]:
    """
    ステータス不正チェック
    RIT または BLNK ステータスのゼッケンが走行データを持っていないかチェック
    """
    errors = []
    
    for result in results:
        if result.status in ['RIT', 'BLNK']:
            # START時刻またはGOAL時刻が存在するかチェック
            has_start = hasattr(result, 'start_time') and result.start_time
            has_goal = hasattr(result, 'goal_time') and result.goal_time
            
            if has_start or has_goal:
                error_msg = f"⚠️ ステータス不正エラー\n"
                error_msg += f"区間 '{result.section}' でゼッケン {result.zekken} は {result.status} ステータスですが、\n"
                if has_start and has_goal:
                    error_msg += "START時刻とGOAL時刻の両方が存在します。\n"
                elif has_start:
                    error_msg += "START時刻が存在します。\n"
                else:
                    error_msg += "GOAL時刻が存在します。\n"
                error_msg += "確認してください。"
                
                error = ValidationError(
                    error_type="invalid_status",
                    message=error_msg,
                    details={
                        "section": result.section,
                        "zekken": result.zekken,
                        "status": result.status
                    },
                    allow_confirmation=True
                )
                errors.append(error)
    
    return errors


def check_measurement_type(race_folder: str) -> List[ValidationError]:
    """
    計測タイプ確認
    type=T（手動計測）の時刻にゼッケンが入力されている場合は警告
    """
    errors = []
    
    if not race_folder or not os.path.exists(race_folder):
        return errors
    
    import glob
    import re
    
    # CSVファイルをすべて取得
    csv_files = glob.glob(os.path.join(race_folder, "*.csv"))
    
    for csv_file in csv_files:
        try:
            # CSV読み込み
            df = pd.read_csv(csv_file, encoding='utf-8-sig')
            
            # 列を探す: type, time, number
            type_col = None
            time_col = None
            number_col = None
            
            # time列を探す
            for idx, col in enumerate(df.columns):
                if 'time' in col.lower():
                    time_col = col
                    # typeはtimeの左側
                    if idx > 0:
                        type_col = df.columns[idx - 1]
                    # numberはtimeの右側
                    if idx + 1 < len(df.columns):
                        number_col = df.columns[idx + 1]
                    break
            
            if not all([type_col, time_col, number_col]):
                continue  # 必要な列が見つからない場合はスキップ
            
            # ファイル名から区間名を抽出
            basename = os.path.splitext(os.path.basename(csv_file))[0]
            sections = []
            parts = basename.split('_')
            for part in parts:
                match = re.match(r'([A-Z]+\d+)(START|GOAL)', part)
                if match:
                    sections.append(match.group(1))
            
            section_name = ', '.join(sections) if sections else basename
            
            # 各行をチェック
            for idx, row in df.iterrows():
                type_val = row[type_col]
                time_val = row[time_col]
                number_val = row[number_col]
                
                # type=Tかつnumberが入力されている場合
                if pd.notna(type_val) and str(type_val).strip().upper() == 'T':
                    if pd.notna(number_val) and str(number_val).strip() != '':
                        try:
                            zekken = int(float(number_val))
                            time_str = str(time_val) if pd.notna(time_val) else ''
                            
                            error_msg = f"⚠️ 計測タイプ確認\n"
                            error_msg += f"区間 '{section_name}' で手動計測（type=T）の時刻にゼッケン {zekken} が入力されています。\n"
                            error_msg += f"  時刻: {time_str}\n"
                            error_msg += f"  ファイル: {os.path.basename(csv_file)}\n"
                            error_msg += "確認してください。"
                            
                            error = ValidationError(
                                error_type="measurement_type",
                                message=error_msg,
                                details={
                                    "section": section_name,
                                    "time": time_str,
                                    "zekken": zekken,
                                    "file": os.path.basename(csv_file)
                                },
                                allow_confirmation=True
                            )
                            errors.append(error)
                        except (ValueError, TypeError):
                            pass  # numberが数値に変換できない場合はスキップ
        
        except Exception as e:
            logger.warning(f"計測タイプチェック中にエラー: {csv_file}: {str(e)}")
            continue
    
    return errors


def check_measurement_deficiency(calc_engine, sections: List) -> List[ValidationError]:
    """
    計測データ不備確認
    PC競技：その区間の総通過台数の半数以上が1秒以上ずれている
    CO競技：その区間の総通過台数の半数以上が得点を取得できていない
    PCGは不要
    """
    errors = []
    
    if not calc_engine or not hasattr(calc_engine, 'results'):
        return errors
    
    # 区間ごとにチェック
    for section in sections:
        section_name = section.section
        section_type = None
        
        # 区間タイプを判定
        if section_name.startswith("PCG"):
            continue  # PCGはスキップ
        elif section_name.startswith("PC"):
            section_type = "PC"
        elif section_name.startswith("CO"):
            section_type = "CO"
        else:
            continue  # 不明な区間タイプはスキップ
        
        # この区間の結果を集計
        total_count = 0
        problematic_count = 0
        
        for zekken in calc_engine.results.keys():
            if section_name not in calc_engine.results[zekken]:
                continue
            
            result = calc_engine.results[zekken][section_name]
            
            # ステータスがある場合はスキップ
            if result.status:
                continue
            
            total_count += 1
            
            if section_type == "PC":
                # PC競技: 1秒以上ずれているかチェック
                if result.diff is not None and abs(result.diff) >= 1.0:
                    problematic_count += 1
            
            elif section_type == "CO":
                # CO競技: 得点を取得できていないかチェック
                if result.point == 0:
                    problematic_count += 1
        
        # 半数以上が問題ありの場合
        if total_count > 0 and problematic_count >= total_count / 2:
            if section_type == "PC":
                error_msg = f"⚠️ 計測データ不備（PC競技）\n"
                error_msg += f"区間 '{section_name}' で総通過台数 {total_count}台のうち、\n"
                error_msg += f"{problematic_count}台（{problematic_count/total_count*100:.1f}%）が1秒以上ずれています。\n"
                error_msg += "計測データを確認してください。"
            else:  # CO
                error_msg = f"⚠️ 計測データ不備（CO競技）\n"
                error_msg += f"区間 '{section_name}' で総通過台数 {total_count}台のうち、\n"
                error_msg += f"{problematic_count}台（{problematic_count/total_count*100:.1f}%）が得点を取得できていません。\n"
                error_msg += "計測データを確認してください。"
            
            error = ValidationError(
                error_type="measurement_deficiency",
                message=error_msg,
                details={
                    "section": section_name,
                    "type": section_type,
                    "total_count": total_count,
                    "problematic_count": problematic_count
                },
                allow_confirmation=True
            )
            errors.append(error)
    
    return errors
