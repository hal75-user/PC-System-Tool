"""
Sample settings file generator for PC-System-Tool.

This module provides functionality to generate sample configuration files
for initial setup and testing purposes.
"""

import os
import csv
import logging
from typing import List, Dict

logger = logging.getLogger(__name__)


def generate_sample_files(base_path: str) -> bool:
    """
    Generate sample settings files in the specified directory.
    
    Creates a 'settings' folder with sample CSV files:
    - entries_sample.csv
    - point_sample.csv
    - section_sample.csv
    
    Args:
        base_path: Base directory where 'settings' folder will be created
        
    Returns:
        bool: True if generation successful, False otherwise
    """
    try:
        # Create settings folder
        settings_path = os.path.join(base_path, 'settings')
        os.makedirs(settings_path, exist_ok=True)
        logger.info(f"Created settings folder: {settings_path}")
        
        # Generate each sample file
        _create_sample_entries(os.path.join(settings_path, 'entries_sample.csv'))
        _create_sample_point(os.path.join(settings_path, 'point_sample.csv'))
        _create_sample_section(os.path.join(settings_path, 'section_sample.csv'))
        
        logger.info("Sample files generated successfully")
        return True
        
    except Exception as e:
        logger.error(f"Failed to generate sample files: {e}")
        return False


def _create_sample_entries(file_path: str):
    """Create sample entries CSV file with real-looking data."""
    headers = ['No', 'DriverName', 'DriverAge', 'CoDriverName', 'CoDriverAge', 'CarName', '係数', '車製造年', 'CarClass', '年齢係数']
    
    # Sample data with 10 entries, based on actual format
    data = [
        ['1', '竹元 京人', '25843', '竹元 淳子', '25794', 'BUGATTI T40', '1.75', '1928', 'A', '1'],
        ['2', '佐藤公夫', '27470', '佐藤 喜美子', '27381', 'BUGATTI T35B', '1.75', '1927', 'A', '1'],
        ['3', '遊佐 勇人', '21879', '遊佐 直子', '20571', 'ASTON MARTIN INTERNATIONAL', '1.65', '1930', 'B', '1'],
        ['4', '小宮 延雄', '27542', '小宮 芳子', '25970', 'MG N TYPE MAGNETT', '1.65', '1935', 'B', '1'],
        ['5', '比嘉成夫', '24191', '比嘉 祐太郎', '13097', 'FIAT 508S BALILLA COPPA D\'ORO', '1.6', '1935', 'B', '1'],
        ['6', '疋野 繁', '26118', '疋野 則子', '24328', 'LAGONDA RAPIER', '1.65', '1935', 'B', '1'],
        ['7', '中島 照夫', '23992', '中島 房子', '21508', 'JAGUAR SS100', '1.55', '1936', 'B', '1'],
        ['8', '加藤 佳支信', '22265', '加藤 三美子', '22310', 'MG TA MIDGET', '1.65', '1936', 'B', '1'],
        ['9', '平野 喜正', '26614', '平野 三枝子', '26609', 'MORGAN 4/4 FLAT RADIATOR', '1.55', '1937', 'B', '1'],
        ['10', '竹内 眞哉', '26645', '桶谷 渡', '21949', 'ALVIS SPEED 25 VANDEN PLAS TOURER', '1.65', '1937', 'B', '1'],
    ]
    
    with open(file_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(data)
    
    logger.info(f"Created sample entries file: {file_path}")


def _create_sample_point(file_path: str):
    """Create sample point configuration CSV file - exact copy of actual data."""
    headers = ['Order', 'Point']
    
    # Point distribution matching actual LFAT2025 data (1st to 78th place)
    data = []
    points_list = [
        500, 480, 460, 440, 420, 400, 380, 360, 340, 320,  # 1-10
        300, 280, 260, 240, 220, 200, 190, 180, 170, 160,  # 11-20
        150, 140, 130, 120, 110, 105, 100, 95, 90, 85,     # 21-30
        80, 75, 70, 65, 60, 57, 54, 51, 48, 45,            # 31-40
        40, 38, 36, 34, 32, 30, 28, 26, 24, 22,            # 41-50
        20, 18, 16, 14, 12, 10, 8, 6, 4, 2,                # 51-60
    ]
    
    # Add points for positions 1-60
    for i, pts in enumerate(points_list, 1):
        data.append([str(i), str(pts)])
    
    # Add positions 61-78 with 0 points
    for i in range(61, 79):
        data.append([str(i), '0'])
    
    with open(file_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(data)
    
    logger.info(f"Created sample point file: {file_path}")


def _create_sample_section(file_path: str):
    """Create sample section configuration CSV file with real location data."""
    headers = ['type', 'section', 'name', 'time', 'GROUP', 'DAY']
    
    # Sample sections based on actual LFAT2025 format
    data = [
        ['CO', 'CO1', '那須野が原公園', '12600', '1', '1'],
        ['PC', 'PC1', 'つくるまサーキット', '25', '2', '1'],
        ['PC', 'PC2', 'つくるまサーキット', '19', '2', '1'],
        ['PC', 'PC3', 'つくるまサーキット', '12', '2', '1'],
        ['PC', 'PC4', 'つくるまサーキット', '32', '2', '1'],
        ['PC', 'PC5', 'つくるまサーキット', '16', '2', '1'],
        ['PCG', 'PCG1', 'つくるまサーキット', '104', '2', '1'],
        ['PC', 'PC6', '公道', '330', '3', '1'],
        ['PC', 'PC7', '公道', '19', '3', '1'],
        ['PC', 'PC8', '公道', '11', '3', '1'],
    ]
    
    with open(file_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(data)
    
    logger.info(f"Created sample section file: {file_path}")
