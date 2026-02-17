"""
データ検証モジュール
レースデータの整合性をチェックし、エラーを検出する
"""

import os
from typing import List, Dict, Set
from collections import defaultdict, Counter
import logging

logger = logging.getLogger(__name__)


def validate_all(race_folder: str, results: List, sections: List) -> List[str]:
    """
    すべてのデータ検証を実行
    
    Args:
        race_folder: レースデータフォルダのパス
        results: レース結果のリスト
        sections: 区間設定のリスト
        
    Returns:
        エラーメッセージのリスト
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
    
    return errors


def check_duplicate_filenames(race_folder: str) -> List[str]:
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
            errors.append(error_msg)
    
    return errors


def check_duplicate_zekken_in_section(results: List) -> List[str]:
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
                errors.append(error_msg)
    
    return errors


def check_section_passage_order(results: List, sections: List) -> List[str]:
    """
    区間通過順チェック
    同じグループ内の各区間で、ゼッケンの通過順序が一致するかチェック
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
            
            # 順序が異なる場合
            if base_common_order != current_common_order:
                error_msg = f"⚠️ 区間通過順エラー\n"
                error_msg += f"グループ {group} で通過順序が異なります:\n"
                error_msg += f"  基準区間 {first_section}: {base_common_order}\n"
                error_msg += f"  区間 {section_name}: {current_common_order}\n"
                error_msg += "確認してください。"
                errors.append(error_msg)
            
            # 歯抜けチェック（基準にあるが現在にない）
            missing = base_set - current_set
            if missing:
                error_msg = f"⚠️ 区間通過順エラー（歯抜け）\n"
                error_msg += f"グループ {group} の区間 {section_name} で、\n"
                error_msg += f"基準区間 {first_section} にあるゼッケンが欠けています: {sorted(missing)}\n"
                error_msg += "確認してください。"
                errors.append(error_msg)
            
            # 追加ゼッケンチェック（現在にあるが基準にない）
            extra = current_set - base_set
            if extra:
                error_msg = f"⚠️ 区間通過順エラー（追加）\n"
                error_msg += f"グループ {group} の区間 {section_name} で、\n"
                error_msg += f"基準区間 {first_section} にないゼッケンがあります: {sorted(extra)}\n"
                error_msg += "確認してください。"
                errors.append(error_msg)
    
    return errors


def check_zekken_passage_order(results: List, sections: List) -> List[str]:
    """
    ゼッケン通過順チェック
    各ゼッケンがグループ内の区間を正しい順序で通過しているかチェック
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
            
            if len(passed_sections) < 2:
                continue  # 1つの区間しか通過していない場合はスキップ
            
            # 通過した区間の期待される順序を取得
            expected_passed = [s for s in expected_order if s in passed_sections]
            
            # 実際の通過順序と比較
            if passed_sections != expected_passed:
                error_msg = f"⚠️ ゼッケン通過順エラー\n"
                error_msg += f"ゼッケン {zekken} がグループ {group} で不正な順序で通過:\n"
                error_msg += f"  期待: {' → '.join(expected_passed)}\n"
                error_msg += f"  実際: {' → '.join(passed_sections)}\n"
                error_msg += "確認してください。"
                errors.append(error_msg)
    
    return errors


def check_invalid_status_with_time(results: List) -> List[str]:
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
                errors.append(error_msg)
    
    return errors
