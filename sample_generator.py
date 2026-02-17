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
    """Create sample entries CSV file with anonymous data."""
    headers = ['No', 'DriverName', 'CoDriverName', 'CarName', '車両製造年', 'CarClass', '係数', '年齢係数']
    
    # Sample data with 10 entries, 2 classes
    data = [
        ['1', 'driver1', 'codriver1', 'car1', '2020', 'A', '1.0', '1.0'],
        ['2', 'driver2', 'codriver2', 'car2', '2019', 'A', '1.0', '1.0'],
        ['3', 'driver3', 'codriver3', 'car3', '2021', 'A', '1.0', '1.0'],
        ['4', 'driver4', 'codriver4', 'car4', '2018', 'A', '1.0', '1.0'],
        ['5', 'driver5', 'codriver5', 'car5', '2022', 'A', '1.0', '1.0'],
        ['6', 'driver6', 'codriver6', 'car6', '2020', 'A', '1.0', '1.0'],
        ['7', 'driver7', 'codriver7', 'car7', '2019', 'B', '1.0', '1.0'],
        ['8', 'driver8', 'codriver8', 'car8', '2021', 'B', '1.0', '1.0'],
        ['9', 'driver9', 'codriver9', 'car9', '2020', 'B', '1.0', '1.0'],
        ['10', 'driver10', 'codriver10', 'car10', '2022', 'B', '1.0', '1.0'],
    ]
    
    with open(file_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(data)
    
    logger.info(f"Created sample entries file: {file_path}")


def _create_sample_point(file_path: str):
    """Create sample point configuration CSV file."""
    headers = ['Point', 'CO点数']
    
    # Standard point types
    data = [
        ['PC', '100'],
        ['PCG', '80'],
        ['CO', '50'],
    ]
    
    with open(file_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(data)
    
    logger.info(f"Created sample point file: {file_path}")


def _create_sample_section(file_path: str):
    """Create sample section configuration CSV file."""
    headers = ['Section', 'Point', '標準', '許容', 'GOAL', 'DAY', 'GROUP']
    
    # 6 sections: 2 PC, 2 PCG, 2 CO for day 1
    data = [
        ['PC1', 'PC', '09:00:00', '00:10:00', '09:30:00', '1', '1'],
        ['PC2', 'PCG', '10:00:00', '00:15:00', '10:30:00', '1', '1'],
        ['CO1', 'CO', '11:00:00', '00:05:00', '11:20:00', '1', '1'],
        ['PC3', 'PC', '12:00:00', '00:10:00', '12:30:00', '1', '1'],
        ['PC4', 'PCG', '13:00:00', '00:15:00', '13:30:00', '1', '1'],
        ['CO2', 'CO', '14:00:00', '00:05:00', '14:30:00', '1', '1'],
    ]
    
    with open(file_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(data)
    
    logger.info(f"Created sample section file: {file_path}")
