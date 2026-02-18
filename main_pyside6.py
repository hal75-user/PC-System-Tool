"""
GUI メインモジュール（PySide6版）
PySide6 を使った高機能 GUI アプリケーション
"""

import sys
import pandas as pd
from typing import List
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTableWidget, QTableWidgetItem, QPushButton, QTabWidget,
    QLabel, QMessageBox, QFileDialog, QDialog, QFormLayout,
    QLineEdit, QComboBox, QScrollArea, QHeaderView, QStyle, QSplitter,
    QAbstractItemView, QGridLayout
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QColor, QBrush, QFont, QAction

from config_loader import ConfigLoader
from race_parser import RaceParser
from calculation_engine import CalculationEngine
from output_formatter import OutputFormatter
from app_config import AppConfig
from logging_config import init_app_logging, get_logger
from sample_generator import generate_sample_files
from data_validator import validate_all, ValidationError

# ロギング初期化
init_app_logging()
logger = get_logger(__name__)


class ErrorDialog(QDialog):
    """エラー確認ダイアログ"""
    
    def __init__(self, parent, errors: List[ValidationError]):
        super().__init__(parent)
        self.errors = errors
        self.setWindowTitle("エラー確認")
        self.setMinimumSize(800, 600)
        
        self._create_widgets()
    
    def _create_widgets(self):
        layout = QVBoxLayout()
        
        # 説明ラベル
        info_label = QLabel("検出されたエラー/警告の一覧です。\n"
                           "各エラーを確認した後、「確認」ボタンをクリックしてください。")
        layout.addWidget(info_label)
        
        # エラーリスト
        self.error_table = QTableWidget()
        self.error_table.setColumnCount(3)
        self.error_table.setHorizontalHeaderLabels(["ステータス", "エラー種別", "詳細"])
        self.error_table.horizontalHeader().setStretchLastSection(True)
        self.error_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.error_table.setSelectionMode(QAbstractItemView.SingleSelection)
        
        # エラーを表示
        self._populate_errors()
        
        layout.addWidget(self.error_table)
        
        # ボタン
        button_layout = QHBoxLayout()
        
        self.confirm_btn = QPushButton("選択したエラーを確認済みにする")
        self.confirm_btn.clicked.connect(self._confirm_selected_error)
        button_layout.addWidget(self.confirm_btn)
        
        self.confirm_all_btn = QPushButton("すべて確認済みにする")
        self.confirm_all_btn.clicked.connect(self._confirm_all_errors)
        button_layout.addWidget(self.confirm_all_btn)
        
        self.unconfirm_btn = QPushButton("選択したエラーを未確認に戻す")
        self.unconfirm_btn.clicked.connect(self._unconfirm_selected_error)
        button_layout.addWidget(self.unconfirm_btn)
        
        button_layout.addStretch()
        
        close_btn = QPushButton("閉じる")
        close_btn.clicked.connect(self.accept)
        button_layout.addWidget(close_btn)
        
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
    
    def _populate_errors(self):
        """エラーをテーブルに表示"""
        self.error_table.setRowCount(len(self.errors))
        
        for row, error in enumerate(self.errors):
            # ステータス列
            status_item = QTableWidgetItem()
            if error.confirmed:
                status_item.setText("✓ 確認済み")
                status_item.setBackground(QBrush(QColor(200, 255, 200)))  # 緑
            else:
                status_item.setText("未確認")
                status_item.setBackground(QBrush(QColor(255, 200, 200)))  # 赤
            status_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            self.error_table.setItem(row, 0, status_item)
            
            # エラー種別列
            type_names = {
                "csv_duplicate": "CSVファイル名重複",
                "zekken_duplicate": "ゼッケン重複",
                "section_order": "区間通過順",
                "zekken_order": "ゼッケン通過順",
                "invalid_status": "ステータス不正",
                "measurement_type": "計測タイプ",
                "measurement_deficiency": "計測データ不備"
            }
            type_item = QTableWidgetItem(type_names.get(error.error_type, error.error_type))
            type_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            self.error_table.setItem(row, 1, type_item)
            
            # 詳細列
            detail_item = QTableWidgetItem(error.message)
            detail_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            self.error_table.setItem(row, 2, detail_item)
        
        # 列幅を調整
        self.error_table.setColumnWidth(0, 100)
        self.error_table.setColumnWidth(1, 150)
    
    def _confirm_selected_error(self):
        """選択したエラーを確認済みにする"""
        selected_rows = self.error_table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "警告", "エラーを選択してください。")
            return
        
        row = selected_rows[0].row()
        error = self.errors[row]
        
        # 確認を許容しないエラーの場合は警告
        if not error.allow_confirmation:
            QMessageBox.critical(
                self,
                "確認不可",
                "このエラーは確認済みにすることができません。\n\n"
                "このエラーは重大な問題のため、必ず修正する必要があります。"
            )
            return
        
        # 確認済みに変更
        error.confirmed = True
        self._populate_errors()
        QMessageBox.information(self, "成功", "エラーを確認済みにしました。")
    
    def _confirm_all_errors(self):
        """すべてのエラーを確認済みにする（許容されるもののみ）"""
        # 確認できないエラーをカウント
        non_confirmable = sum(1 for err in self.errors if not err.allow_confirmation)
        confirmable = sum(1 for err in self.errors if err.allow_confirmation)
        
        if non_confirmable > 0:
            reply = QMessageBox.question(
                self,
                "確認",
                f"確認可能な{confirmable}件のエラーを確認済みにします。\n"
                f"（{non_confirmable}件の重大エラーは確認できません）\n\n"
                f"続行しますか？",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply == QMessageBox.No:
                return
        else:
            reply = QMessageBox.question(
                self,
                "確認",
                f"{confirmable}件のエラーをすべて確認済みにしますか？",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply == QMessageBox.No:
                return
        
        # すべての確認可能なエラーを確認済みにする
        for error in self.errors:
            if error.allow_confirmation:
                error.confirmed = True
        
        self._populate_errors()
        QMessageBox.information(self, "成功", f"{confirmable}件のエラーを確認済みにしました。")
    
    def _unconfirm_selected_error(self):
        """選択したエラーを未確認に戻す"""
        selected_rows = self.error_table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "警告", "エラーを選択してください。")
            return
        
        row = selected_rows[0].row()
        error = self.errors[row]
        
        # 未確認に戻す
        error.confirmed = False
        self._populate_errors()
        QMessageBox.information(self, "成功", "エラーを未確認に戻しました。")
    
    def get_unconfirmed_count(self) -> int:
        """未確認エラーの数を取得"""
        return sum(1 for error in self.errors if not error.confirmed)


class StatusMatrixDialog(QDialog):
    """区間ステータス設定ダイアログ（フィルター・タブ対応版）"""
    
    def __init__(self, parent, app_config, config_loader):
        super().__init__(parent)
        self.app_config = app_config
        self.config_loader = config_loader
        self.setWindowTitle("区間ステータス設定")
        self.setMinimumSize(1200, 700)
        
        self.all_zekkens = sorted(config_loader.entries_dict.keys())
        self.all_sections = config_loader.get_section_order()
        self.status_options = ["", "RIT", "N.C.", "BLNK"]
        
        # 現在選択されているステータス
        self.current_status = ""
        
        # フィルター条件（ゼッケン番号のリスト）
        self.filter_conditions = []
        self.filter_active = False
        
        # タブウィジェット用
        self.tab_widgets = []  # 各タブのStatusMatrixTabWidget
        
        self._create_widgets()
        self._load_current_status()
    
    def _create_widgets(self):
        layout = QVBoxLayout()
        
        # 上部: 説明とステータス選択
        top_layout = QVBoxLayout()
        
        label = QLabel("セルをクリックまたはドラッグして選択し、選択中のステータスを適用します")
        top_layout.addWidget(label)
        
        # ステータス選択ボタン
        button_layout = QHBoxLayout()
        button_layout.addWidget(QLabel("ステータス選択:"))
        
        self.status_buttons = {}
        for status in self.status_options:
            btn_text = "空白" if status == "" else status
            btn = QPushButton(btn_text)
            btn.setCheckable(True)
            btn.setMinimumWidth(80)
            if status == "":
                btn.setChecked(True)
            btn.clicked.connect(lambda checked, s=status: self._on_status_selected(s))
            self.status_buttons[status] = btn
            button_layout.addWidget(btn)
        
        button_layout.addStretch()
        top_layout.addLayout(button_layout)
        
        # フィルターUI
        filter_group_layout = QVBoxLayout()
        filter_label = QLabel("ゼッケン番号フィルター:")
        filter_label.setStyleSheet("font-weight: bold;")
        filter_group_layout.addWidget(filter_label)
        
        # フィルター条件リストとボタン
        filter_controls = QHBoxLayout()
        
        # フィルター条件を表示するスクロールエリア
        self.filter_scroll = QScrollArea()
        self.filter_scroll.setMaximumHeight(100)
        self.filter_scroll.setWidgetResizable(True)
        
        self.filter_widget = QWidget()
        self.filter_layout = QVBoxLayout(self.filter_widget)
        self.filter_layout.setAlignment(Qt.AlignTop)
        self.filter_scroll.setWidget(self.filter_widget)
        
        filter_controls.addWidget(self.filter_scroll, stretch=3)
        
        # フィルターボタン類
        filter_buttons = QVBoxLayout()
        
        add_filter_btn = QPushButton("+ 条件追加")
        add_filter_btn.clicked.connect(self._add_filter_condition)
        filter_buttons.addWidget(add_filter_btn)
        
        apply_filter_btn = QPushButton("フィルター適用")
        apply_filter_btn.clicked.connect(self._apply_filter)
        filter_buttons.addWidget(apply_filter_btn)
        
        show_all_btn = QPushButton("全表示")
        show_all_btn.clicked.connect(self._show_all)
        filter_buttons.addWidget(show_all_btn)
        
        filter_buttons.addStretch()
        filter_controls.addLayout(filter_buttons)
        
        filter_group_layout.addLayout(filter_controls)
        top_layout.addLayout(filter_group_layout)
        
        layout.addLayout(top_layout)
        
        # タブウィジェット
        self.tab_widget = QTabWidget()
        
        # 全日タブ
        all_day_widget = StatusMatrixTabWidget(self, self.all_zekkens, self.all_sections)
        self.tab_widgets.append(all_day_widget)
        self.tab_widget.addTab(all_day_widget, "全日")
        
        # 日別タブを動的に生成
        max_day = self.config_loader.get_max_day()
        if max_day > 0:
            for day_idx in range(1, max_day + 1):
                sections = self.config_loader.get_sections_by_day(day_idx)
                if sections:
                    day_widget = StatusMatrixTabWidget(self, self.all_zekkens, sections)
                    self.tab_widgets.append(day_widget)
                    self.tab_widget.addTab(day_widget, f"{day_idx}日目")
        else:
            # DAY列がない場合、GROUP列で代替
            for group_idx in range(1, 10):
                sections = self.config_loader.get_sections_by_group(group_idx)
                if sections:
                    group_widget = StatusMatrixTabWidget(self, self.all_zekkens, sections)
                    self.tab_widgets.append(group_widget)
                    self.tab_widget.addTab(group_widget, f"グループ{group_idx}")
                elif group_idx > 1 and len(self.tab_widgets) > 1:
                    break
        
        layout.addWidget(self.tab_widget)
        
        # 下部ボタン
        bottom_layout = QHBoxLayout()
        
        save_btn = QPushButton("保存")
        save_btn.clicked.connect(self._save)
        bottom_layout.addWidget(save_btn)
        
        cancel_btn = QPushButton("キャンセル")
        cancel_btn.clicked.connect(self.reject)
        bottom_layout.addWidget(cancel_btn)
        
        clear_btn = QPushButton("すべてクリア")
        clear_btn.clicked.connect(self._clear_all)
        bottom_layout.addWidget(clear_btn)
        
        bottom_layout.addStretch()
        layout.addLayout(bottom_layout)
        
        self.setLayout(layout)
    
    def _add_filter_condition(self):
        """フィルター条件を追加"""
        condition_widget = QWidget()
        condition_layout = QHBoxLayout(condition_widget)
        condition_layout.setContentsMargins(0, 0, 0, 0)
        
        zekken_input = QLineEdit()
        zekken_input.setPlaceholderText("ゼッケン番号")
        zekken_input.setMaximumWidth(150)
        condition_layout.addWidget(zekken_input)
        
        remove_btn = QPushButton("×")
        remove_btn.setMaximumWidth(30)
        remove_btn.clicked.connect(lambda: self._remove_filter_condition(condition_widget))
        condition_layout.addWidget(remove_btn)
        
        condition_layout.addStretch()
        
        self.filter_layout.addWidget(condition_widget)
        self.filter_conditions.append(zekken_input)
    
    def _remove_filter_condition(self, widget):
        """フィルター条件を削除"""
        # ウィジェット内のLineEditを探してリストから削除
        for child in widget.findChildren(QLineEdit):
            if child in self.filter_conditions:
                self.filter_conditions.remove(child)
        
        # ウィジェット自体を削除
        self.filter_layout.removeWidget(widget)
        widget.deleteLater()
    
    def _apply_filter(self):
        """フィルターを適用"""
        # 有効なゼッケン番号を収集
        filtered_zekkens = []
        for input_widget in self.filter_conditions:
            text = input_widget.text().strip()
            if text:
                try:
                    zekken = int(text)
                    if zekken in self.all_zekkens:
                        filtered_zekkens.append(zekken)
                except ValueError:
                    pass
        
        if filtered_zekkens:
            self.filter_active = True
            filtered_zekkens = sorted(set(filtered_zekkens))
            # 全タブにフィルター適用
            for tab_widget in self.tab_widgets:
                tab_widget.apply_filter(filtered_zekkens)
        else:
            QMessageBox.warning(self, "警告", "有効なゼッケン番号が入力されていません")
    
    def _show_all(self):
        """全表示（フィルター条件は保持）"""
        self.filter_active = False
        # 全タブのフィルターを解除
        for tab_widget in self.tab_widgets:
            tab_widget.show_all()
    
    def _on_status_selected(self, status):
        """ステータスボタンが選択された時"""
        for s, btn in self.status_buttons.items():
            btn.setChecked(s == status)
        
        self.current_status = status
        # 全タブに現在のステータスを伝播
        for tab_widget in self.tab_widgets:
            tab_widget.current_status = status
    
    def _load_current_status(self):
        """現在のステータス設定を読み込んでテーブルに反映"""
        for tab_widget in self.tab_widgets:
            tab_widget.load_current_status(self.app_config)
    
    def _save(self):
        """ステータスを保存"""
        self.app_config.status_map = {}
        
        # 全日タブからすべてのステータスを収集
        all_day_widget = self.tab_widgets[0]  # 最初のタブは全日
        all_day_widget.save_status(self.app_config)
        
        self.app_config.save()
        QMessageBox.information(self, "成功", "ステータス設定を保存しました")
        self.accept()
    
    def _clear_all(self):
        """すべてクリア"""
        reply = QMessageBox.question(self, "確認", "すべてのステータス設定をクリアしますか？")
        if reply == QMessageBox.Yes:
            for tab_widget in self.tab_widgets:
                tab_widget.clear_all()


class StatusMatrixTabWidget(QWidget):
    """ステータスマトリックスの1つのタブ"""
    
    def __init__(self, parent_dialog, zekkens, sections):
        super().__init__()
        self.parent_dialog = parent_dialog
        self.all_zekkens = zekkens
        self.sections = sections
        self.current_status = ""
        self.filtered_zekkens = None  # Noneは全表示
        
        self._create_widgets()
    
    def _create_widgets(self):
        layout = QVBoxLayout()
        
        # スクロールエリア
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        
        # テーブル
        self.table = QTableWidget()
        self.table.setRowCount(len(self.all_zekkens))
        # 列数: ゼッケン + 区間 + Total Result + Penalty
        self.table.setColumnCount(len(self.sections) + 3)
        
        # 複数セル選択を有効化
        self.table.setSelectionMode(QTableWidget.MultiSelection)
        
        # セルクリック/変更イベント
        self.table.itemClicked.connect(self._on_cell_clicked)
        self.table.itemSelectionChanged.connect(self._on_selection_changed)
        
        # ヘッダー
        headers = ["ゼッケン"] + self.sections + ["ペナルティ", "Total Result"]
        self.table.setHorizontalHeaderLabels(headers)
        
        # ペナルティ列とTotal Result列のインデックスを記憶
        self.penalty_col = len(self.sections) + 1
        self.total_result_col = len(self.sections) + 2
        
        # データ入力
        for row_idx, zekken in enumerate(self.all_zekkens):
            # ゼッケン列
            item = QTableWidgetItem(str(zekken))
            item.setFlags(Qt.ItemIsEnabled)
            item.setBackground(QBrush(QColor(240, 240, 240)))
            item.setForeground(QBrush(QColor(0, 0, 0)))  # 黒文字
            self.table.setItem(row_idx, 0, item)
            
            # 各区間のセル
            for col_idx, section in enumerate(self.sections, start=1):
                item = QTableWidgetItem("")
                item.setTextAlignment(Qt.AlignCenter)
                item.setData(Qt.UserRole, (zekken, section))
                self.table.setItem(row_idx, col_idx, item)
            
            # ペナルティ列（数字入力）
            penalty_item = QTableWidgetItem("")
            penalty_item.setTextAlignment(Qt.AlignCenter)
            penalty_item.setData(Qt.UserRole, ("penalty", zekken))
            penalty_item.setBackground(QBrush(QColor(255, 250, 205)))  # 淡い黄色で区別
            penalty_item.setForeground(QBrush(QColor(0, 0, 0)))  # 黒文字
            self.table.setItem(row_idx, self.penalty_col, penalty_item)
            
            # Total Result列（ステータス入力）
            total_result_item = QTableWidgetItem("")
            total_result_item.setTextAlignment(Qt.AlignCenter)
            total_result_item.setData(Qt.UserRole, ("total_result", zekken))
            self.table.setItem(row_idx, self.total_result_col, total_result_item)
        
        scroll.setWidget(self.table)
        layout.addWidget(scroll)
        
        self.setLayout(layout)
    
    def apply_filter(self, zekkens):
        """フィルターを適用"""
        self.filtered_zekkens = zekkens
        self._update_row_visibility()
    
    def show_all(self):
        """全表示"""
        self.filtered_zekkens = None
        self._update_row_visibility()
    
    def _update_row_visibility(self):
        """行の表示/非表示を更新"""
        for row_idx, zekken in enumerate(self.all_zekkens):
            if self.filtered_zekkens is None:
                self.table.setRowHidden(row_idx, False)
            else:
                self.table.setRowHidden(row_idx, zekken not in self.filtered_zekkens)
    
    def _on_cell_clicked(self, item):
        """セルがクリックされた時"""
        if item.column() == 0:  # ゼッケン列
            return
        
        col = item.column()
        
        # ペナルティ列は数字入力なので、クリックでステータスを適用しない
        if col == self.penalty_col:
            return
        
        # 区間ステータスまたはTotal Result列の場合、ステータスを適用
        if col <= len(self.sections) or col == self.total_result_col:
            self._apply_status_to_item(item)
    
    def _on_selection_changed(self):
        """選択が変更された時（ドラッグ選択）"""
        selected_items = self.table.selectedItems()
        for item in selected_items:
            col = item.column()
            # ゼッケン列とペナルティ列以外にステータスを適用
            if col > 0 and col != self.penalty_col:
                self._apply_status_to_item(item)
    
    def _apply_status_to_item(self, item):
        """アイテムにステータスを適用"""
        item.setText(self.current_status)
        self._update_cell_color(item, self.current_status)
    
    def _update_cell_color(self, item, status):
        """ステータスに応じてセルの色を変更"""
        if status == "":
            item.setBackground(QBrush(QColor(255, 255, 255)))
        elif status == "RIT":
            item.setBackground(QBrush(QColor(255, 200, 200)))
        elif status == "N.C.":
            item.setBackground(QBrush(QColor(255, 255, 200)))
        elif status == "BLNK":
            item.setBackground(QBrush(QColor(200, 200, 255)))
    
    def load_current_status(self, app_config):
        """現在のステータス設定を読み込んでテーブルに反映"""
        for row_idx, zekken in enumerate(self.all_zekkens):
            # 区間ステータス
            for col_idx, section in enumerate(self.sections, start=1):
                current_status = app_config.get_section_status(zekken, section) or ""
                item = self.table.item(row_idx, col_idx)
                if item:
                    item.setText(current_status)
                    self._update_cell_color(item, current_status)
            
            # Total Result ステータス
            total_result_status = app_config.get_final_status(zekken) or ""
            total_result_item = self.table.item(row_idx, self.total_result_col)
            if total_result_item:
                total_result_item.setText(total_result_status)
                self._update_cell_color(total_result_item, total_result_status)
            
            # ペナルティ
            penalty = app_config.get_penalty(zekken)
            penalty_item = self.table.item(row_idx, self.penalty_col)
            if penalty_item:
                if penalty != 0.0:
                    penalty_item.setText(str(penalty))
                else:
                    penalty_item.setText("")
    
    def save_status(self, app_config):
        """ステータスを保存"""
        for row_idx, zekken in enumerate(self.all_zekkens):
            # 区間ステータス
            for col_idx, section in enumerate(self.sections, start=1):
                item = self.table.item(row_idx, col_idx)
                if item:
                    status = item.text()
                    if status:
                        app_config.set_section_status(zekken, section, status)
            
            # Total Result ステータス
            total_result_item = self.table.item(row_idx, self.total_result_col)
            if total_result_item:
                status = total_result_item.text()
                if status:
                    app_config.set_final_status(zekken, status)
            
            # ペナルティ
            penalty_item = self.table.item(row_idx, self.penalty_col)
            if penalty_item:
                penalty_text = penalty_item.text().strip()
                if penalty_text:
                    try:
                        penalty = float(penalty_text)
                        app_config.set_penalty(zekken, penalty)
                    except ValueError:
                        pass  # 無効な数字は無視
    
    def clear_all(self):
        """すべてクリア"""
        for row_idx in range(self.table.rowCount()):
            for col_idx in range(1, self.table.columnCount()):
                item = self.table.item(row_idx, col_idx)
                if item:
                    item.setText("")
                    self._update_cell_color(item, "")


class FinalStatusDialog(QDialog):
    """最終ステータス設定ダイアログ"""
    
    def __init__(self, parent, app_config, config_loader):
        super().__init__(parent)
        self.app_config = app_config
        self.config_loader = config_loader
        self.setWindowTitle("最終ステータス設定")
        self.setMinimumSize(600, 500)
        
        self.zekkens = sorted(config_loader.entries_dict.keys())
        self.status_options = ["RIT", "N.C.", "BLNK"]
        
        self._create_widgets()
        self._load_current_status()
    
    def _create_widgets(self):
        layout = QVBoxLayout()
        
        # 説明
        label = QLabel("ペナルティ列に数値を入力、またはステータス列(RIT/N.C./BLNK)をクリックして設定します")
        layout.addWidget(label)
        
        # テーブル: 縦軸=ゼッケン、横軸=ペナルティ+ステータス
        self.table = QTableWidget()
        self.table.setRowCount(len(self.zekkens))
        self.table.setColumnCount(5)  # ゼッケン, ペナルティ, RIT, N.C., BLNK
        self.table.setHorizontalHeaderLabels(["ゼッケン", "ペナルティ", "RIT", "N.C.", "BLNK"])
        
        # 列幅設定
        self.table.setColumnWidth(0, 80)   # ゼッケン
        self.table.setColumnWidth(1, 100)  # ペナルティ
        self.table.setColumnWidth(2, 80)   # RIT
        self.table.setColumnWidth(3, 80)   # N.C.
        self.table.setColumnWidth(4, 80)   # BLNK
        
        for row_idx, zekken in enumerate(self.zekkens):
            # ゼッケン列（編集不可）
            zekken_item = QTableWidgetItem(str(zekken))
            zekken_item.setFlags(Qt.ItemIsEnabled)
            zekken_item.setBackground(QBrush(QColor(240, 240, 240)))
            zekken_item.setForeground(QBrush(QColor(0, 0, 0)))  # 黒文字
            zekken_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row_idx, 0, zekken_item)
            
            # ペナルティ列（数値入力可能）
            penalty_item = QTableWidgetItem("")
            penalty_item.setTextAlignment(Qt.AlignCenter)
            penalty_item.setBackground(QBrush(QColor(255, 250, 205)))  # 淡い黄色
            penalty_item.setForeground(QBrush(QColor(0, 0, 0)))  # 黒文字
            self.table.setItem(row_idx, 1, penalty_item)
            
            # ステータス列（チェックボックス的に使用）
            for col_idx, status in enumerate(self.status_options, start=2):
                status_item = QTableWidgetItem("")
                status_item.setTextAlignment(Qt.AlignCenter)
                status_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
                self.table.setItem(row_idx, col_idx, status_item)
        
        # セルクリックイベント
        self.table.itemClicked.connect(self._on_cell_clicked)
        
        layout.addWidget(self.table)
        
        # 下部ボタン
        bottom_layout = QHBoxLayout()
        
        save_btn = QPushButton("保存")
        save_btn.clicked.connect(self._save)
        bottom_layout.addWidget(save_btn)
        
        cancel_btn = QPushButton("キャンセル")
        cancel_btn.clicked.connect(self.reject)
        bottom_layout.addWidget(cancel_btn)
        
        clear_btn = QPushButton("すべてクリア")
        clear_btn.clicked.connect(self._clear_all)
        bottom_layout.addWidget(clear_btn)
        
        bottom_layout.addStretch()
        layout.addLayout(bottom_layout)
        
        self.setLayout(layout)
    
    def _load_current_status(self):
        """現在のステータス設定とペナルティを読み込んでテーブルに反映"""
        for row_idx, zekken in enumerate(self.zekkens):
            # ペナルティを読み込み
            penalty = self.app_config.get_penalty(zekken)
            penalty_item = self.table.item(row_idx, 1)
            if penalty_item and penalty != 0.0:
                penalty_item.setText(str(penalty))
            
            # 最終ステータスを読み込み
            current_status = self.app_config.get_final_status(zekken) or ""
            if current_status in self.status_options:
                # 該当するステータス列にマークをつける
                col_idx = 2 + self.status_options.index(current_status)
                status_item = self.table.item(row_idx, col_idx)
                if status_item:
                    status_item.setText("✓")
                    status_item.setBackground(QBrush(QColor(200, 255, 200)))  # 緑色
    
    def _on_cell_clicked(self, item):
        """セルがクリックされた時"""
        row = item.row()
        col = item.column()
        
        # ゼッケン列はスキップ
        if col == 0:
            return
        
        # ペナルティ列は編集可能なので特別処理不要
        if col == 1:
            return
        
        # ステータス列（RIT, N.C., BLNK）がクリックされた場合
        if col >= 2:
            # 同じ行の他のステータス列をクリア
            for c in range(2, 2 + len(self.status_options)):
                other_item = self.table.item(row, c)
                if other_item:
                    other_item.setText("")
                    other_item.setBackground(QBrush(QColor(255, 255, 255)))
            
            # クリックされたセルにチェックマークをつける
            item.setText("✓")
            item.setBackground(QBrush(QColor(200, 255, 200)))
    
    def _save(self):
        """ステータスとペナルティを保存"""
        # ペナルティとステータスをクリア
        self.app_config.final_status = {}
        self.app_config.penalties = {}
        
        # 無効なペナルティ値をチェック
        invalid_penalties = []
        
        for row_idx, zekken in enumerate(self.zekkens):
            # ペナルティを保存
            penalty_item = self.table.item(row_idx, 1)
            if penalty_item and penalty_item.text().strip():
                try:
                    penalty_value = float(penalty_item.text())
                    # 有限の数値かチェック（inf, -inf, NaNは無効）
                    import math
                    if not math.isfinite(penalty_value):
                        invalid_penalties.append((zekken, penalty_item.text()))
                    elif penalty_value != 0.0:
                        self.app_config.set_penalty(zekken, penalty_value)
                except ValueError:
                    invalid_penalties.append((zekken, penalty_item.text()))
            
            # ステータスを保存
            for col_idx, status in enumerate(self.status_options, start=2):
                status_item = self.table.item(row_idx, col_idx)
                if status_item and status_item.text() == "✓":
                    self.app_config.set_final_status(zekken, status)
                    break
        
        # 無効なペナルティがあれば警告を表示
        if invalid_penalties:
            warning_msg = "以下のゼッケンのペナルティ値が無効なため、保存されませんでした:\n\n"
            for zekken, value in invalid_penalties:
                warning_msg += f"  ゼッケン {zekken}: '{value}'\n"
            warning_msg += "\nペナルティは数値で入力してください。"
            QMessageBox.warning(self, "警告", warning_msg)
        
        self.app_config.save()
        
        if invalid_penalties:
            QMessageBox.information(self, "保存完了（一部警告あり）", 
                                  "有効なデータは保存されましたが、一部のペナルティ値が無効でした。")
        else:
            QMessageBox.information(self, "成功", "最終ステータス設定とペナルティを保存しました")
        
        self.accept()
    
    def _clear_all(self):
        """すべてクリア"""
        reply = QMessageBox.question(self, "確認", "すべての最終ステータス設定とペナルティをクリアしますか？")
        if reply == QMessageBox.Yes:
            for row_idx in range(self.table.rowCount()):
                # ペナルティをクリア
                penalty_item = self.table.item(row_idx, 1)
                if penalty_item:
                    penalty_item.setText("")
                
                # ステータスをクリア
                for col_idx in range(2, 2 + len(self.status_options)):
                    status_item = self.table.item(row_idx, col_idx)
                    if status_item:
                        status_item.setText("")
                        status_item.setBackground(QBrush(QColor(255, 255, 255)))



class ResultTableWidget(QWidget):
    """結果表示テーブルウィジェット"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.calc_engine = None
        self.config_loader = None
        self.filter_sections = None  # None = すべて表示
        
        self._create_widgets()
    
    def _create_widgets(self):
        layout = QVBoxLayout()
        
        # テーブル
        self.table = QTableWidget()
        # ソート機能を無効化
        self.table.setSortingEnabled(False)
        # 列幅は_set_column_widths()で個別に設定
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.table.horizontalHeader().setDefaultAlignment(Qt.AlignCenter)
        # 2段ヘッダー用に高さを調整
        self.table.horizontalHeader().setMinimumHeight(50)
        layout.addWidget(self.table)
        
        self.setLayout(layout)
    
    def set_data(self, calc_engine, config_loader):
        """データをセット"""
        self.calc_engine = calc_engine
        self.config_loader = config_loader
        
        # OutputFormatterを使って総合順位を計算
        from output_formatter import OutputFormatter
        self.output_formatter = OutputFormatter(calc_engine, config_loader)
        self.summary_df = self.output_formatter.get_summary_dataframe()
        
        self._populate_table()
    
    def set_filter(self, sections):
        """フィルターを設定"""
        self.filter_sections = sections
        self._populate_table()
    
    def _populate_table(self):
        """テーブルにデータを入力"""
        if not self.calc_engine or not self.config_loader:
            return
        
        # 描画最適化：更新を一時停止
        self.table.setUpdatesEnabled(False)
        
        # 表示する区間を決定
        if self.filter_sections is None:
            sections = self.config_loader.get_section_order()
            is_all_sections = True
        else:
            sections = self.filter_sections
            is_all_sections = False
        
        # ゼッケン一覧
        zekkens = sorted(self.calc_engine.results.keys())
        
        # 表示する区間の得点と順位を計算
        scores = {}
        for zekken in zekkens:
            scores[zekken] = self.calc_engine.get_score_for_sections(zekken, sections)
        
        # 得点に基づいて順位を計算（降順、同点は同順位）
        sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        ranks = {}
        current_rank = 1
        prev_score = None
        for idx, (zekken, score) in enumerate(sorted_scores, start=1):
            if prev_score is not None and score < prev_score:
                current_rank = idx
            ranks[zekken] = current_rank
            prev_score = score
        
        # カラム構成（2段ヘッダー：改行で区切る）
        # 全日表示の場合は「総合」、日別表示の場合は「得点」「順位」
        if is_all_sections:
            columns = ["ゼッケン", "ドライバー名", "総合得点", "総合順位"]
        else:
            columns = ["ゼッケン", "ドライバー名", "得点", "順位"]
        
        for section in sections:
            columns.extend([
                f"{section}\nSTART",
                f"{section}\nGOAL",
                f"{section}\n走行時間",
                f"{section}\n差分",
                f"{section}\n順位",
                f"{section}\n得点"
            ])
        
        # テーブル設定
        self.table.clear()
        self.table.setRowCount(len(zekkens))
        self.table.setColumnCount(len(columns))
        self.table.setHorizontalHeaderLabels(columns)
        
        # 列幅を設定
        self._set_column_widths(columns)
        
        # データ入力
        for row_idx, zekken in enumerate(zekkens):
            # 固定列
            self._set_item(row_idx, 0, str(zekken))
            
            # ドライバー名を取得
            driver_name = ""
            if zekken in self.config_loader.entries_dict:
                driver_name = self.config_loader.entries_dict[zekken].get('DriverName', '')
            if not driver_name:
                driver_name = f"#{zekken}"
            self._set_item(row_idx, 1, driver_name)
            
            # 表示する区間の得点を表示
            section_score = scores.get(zekken, 0)
            self._set_item(row_idx, 2, str(section_score))
            
            # 表示する区間の順位を表示
            section_rank = ranks.get(zekken, "-")
            self._set_item(row_idx, 3, str(section_rank))
            
            col_idx = 4
            
            # 各区間のデータ
            for section in sections:
                if section not in self.calc_engine.results[zekken]:
                    # データなし
                    for _ in range(6):
                        self._set_item(row_idx, col_idx, "ー")
                        col_idx += 1
                    continue
                
                result = self.calc_engine.results[zekken][section]
                # 区間タイプを取得
                section_type = self.calc_engine._get_section_type(section)
                
                if result.status:
                    # ステータスあり
                    if result.status == "N.C.":
                        # N.C.の場合: タイム表示あり、差分算出、順位は除外
                        # START
                        start_time = self._get_time_str(zekken, section, "START")
                        self._set_item(row_idx, col_idx, start_time)
                        col_idx += 1
                        
                        # GOAL
                        goal_time = self._get_time_str(zekken, section, "GOAL")
                        self._set_item(row_idx, col_idx, goal_time)
                        col_idx += 1
                        
                        # 走行時間
                        passage_str = self.calc_engine.format_time(result.passage_time) if result.passage_time else "ー"
                        self._set_item(row_idx, col_idx, passage_str)
                        col_idx += 1
                        
                        # 差分（色付き）- 秒単位で±00.00形式
                        diff_str = self._format_diff_simple(result.diff) if result.diff is not None else "ー"
                        item = self._set_item(row_idx, col_idx, diff_str)
                        if result.diff is not None:
                            self._color_diff_cell(item, result.diff, section_type)
                        col_idx += 1
                        
                        # 順位: N.C.を表示
                        self._set_item(row_idx, col_idx, result.status)
                        col_idx += 1
                        
                        # 得点
                        self._set_item(row_idx, col_idx, str(result.point))
                        col_idx += 1
                    else:
                        # RIT, BLNKの場合: タイム表示無し、すべてステータス表示
                        for _ in range(6):
                            self._set_item(row_idx, col_idx, result.status)
                            col_idx += 1
                else:
                    # START
                    start_time = self._get_time_str(zekken, section, "START")
                    self._set_item(row_idx, col_idx, start_time)
                    col_idx += 1
                    
                    # GOAL
                    goal_time = self._get_time_str(zekken, section, "GOAL")
                    self._set_item(row_idx, col_idx, goal_time)
                    col_idx += 1
                    
                    # 走行時間
                    passage_str = self.calc_engine.format_time(result.passage_time) if result.passage_time else "ー"
                    self._set_item(row_idx, col_idx, passage_str)
                    col_idx += 1
                    
                    # 差分の表示とフォーマット
                    if section_type == "CO":
                        # CO: OK/NG 表示
                        # CO の許容時間を取得（section_dict から time フィールド）
                        co_tolerance = self.config_loader.section_dict.get(section, 0)
                        if result.diff is not None:
                            if abs(result.diff) <= co_tolerance:
                                diff_str = "OK"
                                color = QColor("#388E3C")  # 緑
                            else:
                                diff_str = "NG"
                                color = QColor("#D32F2F")  # 赤
                            item = self._set_item(row_idx, col_idx, diff_str)
                            item.setForeground(color)
                        else:
                            self._set_item(row_idx, col_idx, "ー")
                    else:
                        # PC/PCG: 差分を秒で表示（色付き）
                        diff_str = self._format_diff_simple(result.diff) if result.diff is not None else "ー"
                        item = self._set_item(row_idx, col_idx, diff_str)
                        if result.diff is not None:
                            self._color_diff_cell(item, result.diff, section_type)
                    col_idx += 1
                    
                    # 順位
                    if section_type == "CO":
                        # CO: 順位は "-" を表示
                        self._set_item(row_idx, col_idx, "-")
                    else:
                        # PC/PCG: 順位を表示（色付き）
                        rank_str = str(result.rank) if result.rank else "ー"
                        item = self._set_item(row_idx, col_idx, rank_str)
                        if result.rank:
                            self._color_rank_cell(item, result.rank)
                    col_idx += 1
                    
                    # 得点
                    self._set_item(row_idx, col_idx, str(result.point))
                    col_idx += 1
        
        # 描画最適化：更新を再開
        self.table.setUpdatesEnabled(True)
    
    def _set_column_widths(self, columns):
        """列名に応じて最適な列幅を設定"""
        for col_idx, col_name in enumerate(columns):
            if col_name == "ゼッケン":
                self.table.setColumnWidth(col_idx, 60)
            elif col_name == "ドライバー名":
                self.table.setColumnWidth(col_idx, 120)
            elif col_name in ["総合得点", "得点"]:
                self.table.setColumnWidth(col_idx, 70)
            elif col_name in ["総合順位", "順位"]:
                self.table.setColumnWidth(col_idx, 70)
            elif "\nSTART" in col_name or "\nGOAL" in col_name:
                self.table.setColumnWidth(col_idx, 95)
            elif "\n走行時間" in col_name:
                self.table.setColumnWidth(col_idx, 70)
            elif "\n差分" in col_name:
                self.table.setColumnWidth(col_idx, 60)
            elif "\n順位" in col_name:
                self.table.setColumnWidth(col_idx, 50)
            elif "\n得点" in col_name:
                self.table.setColumnWidth(col_idx, 50)
            else:
                # デフォルト
                self.table.setColumnWidth(col_idx, 80)
    
    def _format_diff_simple(self, seconds: float) -> str:
        """差分を00.00形式でフォーマット（秒単位、符号なし）"""
        if seconds is None:
            return "ー"
        
        return f"{abs(seconds):.2f}"
    
    def _set_item(self, row, col, text):
        """セルにアイテムをセット"""
        item = QTableWidgetItem(text)
        item.setTextAlignment(Qt.AlignCenter)
        self.table.setItem(row, col, item)
        return item
    
    def _get_time_str(self, zekken, section, timing_type):
        """START/GOAL 時刻を取得"""
        if timing_type == "START":
            if zekken in self.calc_engine.race.start_time and section in self.calc_engine.race.start_time[zekken]:
                return self.calc_engine.race.start_time[zekken][section]
        elif timing_type == "GOAL":
            if zekken in self.calc_engine.race.goal_time and section in self.calc_engine.race.goal_time[zekken]:
                return self.calc_engine.race.goal_time[zekken][section]
        return "ー"
    
    def _color_diff_cell(self, item, diff, section_type="PC"):
        """差分セルに色を付ける（PC/PCG用）
        
        Args:
            item: テーブルアイテム
            diff: 差分（秒）
            section_type: 区間タイプ（PC, PCG, CO）
        """
        # CO の場合は色付けしない（OK/NG表示で色付け）
        if section_type == "CO":
            return
        
        # PC/PCG の場合: 1秒以上=赤、1秒以内=緑
        abs_diff = abs(diff)
        if abs_diff >= 1.0:
            # 赤文字
            item.setForeground(QColor("#D32F2F"))
        else:
            # 緑文字
            item.setForeground(QColor("#388E3C"))
    
    def _color_rank_cell(self, item, rank):
        """順位セルに色を付ける（1位のみ黄色背景）
        
        Args:
            item: テーブルアイテム
            rank: 順位
        """
        # 1位のみ黄色背景
        if rank == 1:
            color = QColor("#FFD700")  # 黄色
            item.setBackground(QBrush(color))


class SummaryTableWidget(QWidget):
    """総合成績表示ウィジェット"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.calc_engine = None
        self.config_loader = None
        self.app_config = None
        self.summary_df = None
        
        self._create_widgets()
    
    def _create_widgets(self):
        layout = QVBoxLayout()
        
        # タイトル
        title_label = QLabel("総合成績表")
        title_label.setStyleSheet("font-size: 18px; font-weight: bold;")
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        
        # テーブル
        self.table = QTableWidget()
        self.table.setSortingEnabled(False)
        # 列: Result, No, DriverName, CoDriverName, CarName, 車両製造年, CarClass, Point, H.C.L Point, Penalty(-), TotalPoint
        self.table.setColumnCount(11)
        self.table.setHorizontalHeaderLabels([
            "Result", "No", "DriverName", "CoDriverName", "CarName",
            "車両製造年", "CarClass", "Point", "H.C.L Point", "Penalty(-)", "TotalPoint"
        ])
        
        # 列幅設定
        self.table.setColumnWidth(0, 80)   # Result
        self.table.setColumnWidth(1, 60)   # No
        self.table.setColumnWidth(2, 120)  # DriverName
        self.table.setColumnWidth(3, 120)  # CoDriverName
        self.table.setColumnWidth(4, 150)  # CarName
        self.table.setColumnWidth(5, 80)   # 車両製造年
        self.table.setColumnWidth(6, 100)  # CarClass
        self.table.setColumnWidth(7, 80)   # Point
        self.table.setColumnWidth(8, 100)  # H.C.L Point
        self.table.setColumnWidth(9, 100)  # Penalty(-)
        self.table.setColumnWidth(10, 100) # TotalPoint
        
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.table.horizontalHeader().setDefaultAlignment(Qt.AlignCenter)
        
        layout.addWidget(self.table)
        
        self.setLayout(layout)
    
    def set_data(self, calc_engine, config_loader, app_config):
        """データをセット"""
        self.calc_engine = calc_engine
        self.config_loader = config_loader
        self.app_config = app_config
        
        # OutputFormatterを使って総合順位を計算
        from output_formatter import OutputFormatter
        self.output_formatter = OutputFormatter(calc_engine, config_loader)
        self.summary_df = self.output_formatter.get_summary_dataframe()
        
        self._populate_table()
    
    def _populate_table(self):
        """テーブルにデータを入力"""
        if self.summary_df is None:
            return
        
        # テーブル設定
        self.table.setRowCount(len(self.summary_df))
        
        # データ入力
        for row_idx, row in self.summary_df.iterrows():
            zekken = row['No']
            
            # ペナルティを取得
            penalty = self.app_config.get_penalty(zekken) if self.app_config else 0
            hcl_point = row['H.C.L Point']
            total_point = hcl_point - penalty
            
            # Result (順位)
            rank_value = row['Result']
            if pd.notna(rank_value):
                if isinstance(rank_value, (int, float)):
                    rank_str = str(int(rank_value))
                else:
                    rank_str = str(rank_value)  # RIT/N.C./BLNK
            else:
                rank_str = "-"
            
            rank_item = QTableWidgetItem(rank_str)
            rank_item.setTextAlignment(Qt.AlignCenter)
            # 上位3位に色を付ける
            if rank_str.isdigit():
                rank_int = int(rank_str)
                if rank_int == 1:
                    rank_item.setBackground(QBrush(QColor(255, 215, 0)))  # 金
                    rank_item.setFont(QFont("", -1, QFont.Bold))
                elif rank_int == 2:
                    rank_item.setBackground(QBrush(QColor(192, 192, 192)))  # 銀
                    rank_item.setFont(QFont("", -1, QFont.Bold))
                elif rank_int == 3:
                    rank_item.setBackground(QBrush(QColor(205, 127, 50)))  # 銅
                    rank_item.setFont(QFont("", -1, QFont.Bold))
            self.table.setItem(row_idx, 0, rank_item)
            
            # No (ゼッケン)
            no_item = QTableWidgetItem(str(zekken))
            no_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row_idx, 1, no_item)
            
            # DriverName
            driver_item = QTableWidgetItem(str(row.get('DriverName', '')))
            driver_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row_idx, 2, driver_item)
            
            # CoDriverName
            codriver_item = QTableWidgetItem(str(row.get('CoDriverName', '')))
            codriver_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row_idx, 3, codriver_item)
            
            # CarName
            car_item = QTableWidgetItem(str(row.get('CarName', '')))
            car_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row_idx, 4, car_item)
            
            # 車両製造年 (整数表示)
            year_value = row.get('車両製造年', '')
            if year_value and pd.notna(year_value):
                try:
                    # 既に整数の場合は直接変換、浮動小数点数の場合はfloat経由で変換
                    if isinstance(year_value, int):
                        year_str = str(year_value)
                    else:
                        year_str = str(int(float(year_value)))
                except (ValueError, TypeError):
                    year_str = str(year_value)
            else:
                year_str = ''
            year_item = QTableWidgetItem(year_str)
            year_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row_idx, 5, year_item)
            
            # CarClass
            class_item = QTableWidgetItem(str(row.get('CarClass', '')))
            class_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row_idx, 6, class_item)
            
            # Point (純粋な得点) - 小数点2桁表示
            point_value = row.get('Point', 0)
            try:
                point_str = f"{float(point_value):.2f}"
            except (ValueError, TypeError):
                point_str = str(point_value)
            point_item = QTableWidgetItem(point_str)
            point_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row_idx, 7, point_item)
            
            # H.C.L Point - 小数点2桁表示
            try:
                hcl_str = f"{float(hcl_point):.2f}"
            except (ValueError, TypeError):
                hcl_str = str(hcl_point)
            hcl_item = QTableWidgetItem(hcl_str)
            hcl_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row_idx, 8, hcl_item)
            
            # Penalty(-) - 赤字表記（0の場合も表示）
            penalty_item = QTableWidgetItem(str(int(penalty)))
            penalty_item.setTextAlignment(Qt.AlignCenter)
            if penalty > 0:
                penalty_item.setForeground(QBrush(QColor(255, 0, 0)))  # 赤字
            self.table.setItem(row_idx, 9, penalty_item)
            
            # TotalPoint - 小数点2桁表示
            try:
                total_str = f"{float(total_point):.2f}"
            except (ValueError, TypeError):
                total_str = str(total_point)
            total_item = QTableWidgetItem(total_str)
            total_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row_idx, 10, total_item)
    
    def set_class_data(self, calc_engine, config_loader, app_config, class_name):
        """クラス別データをセット
        
        Args:
            calc_engine: 計算エンジン
            config_loader: 設定ローダー
            app_config: アプリケーション設定
            class_name: クラス名
        """
        self.calc_engine = calc_engine
        self.config_loader = config_loader
        self.app_config = app_config
        
        # OutputFormatterを使ってクラス別総合順位を計算
        from output_formatter import OutputFormatter
        self.output_formatter = OutputFormatter(calc_engine, config_loader)
        self.summary_df = self.output_formatter.get_summary_by_class(class_name)
        
        self._populate_table()


class MainWindow(QMainWindow):
    """メインウィンドウ"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PC System Tool")
        self.setGeometry(100, 100, 1600, 900)
        
        # モジュール初期化
        self.app_config = AppConfig()
        self.config_loader = None
        self.race_parser = None
        self.calc_engine = None
        self.output_formatter = None
        
        # エラー管理
        self.validation_errors: List[ValidationError] = []
        self.confirmed_errors_map = {}  # エラーキー → 確認済みステータス
        
        # 自動読み込みフラグ
        self.auto_load_attempted = False
        
        self._create_widgets()
        self._create_menu()
        
        self.log("=" * 50)
        self.log("PC System Tool を起動しました")
        self.log("=" * 50)
        self.log(f"race フォルダ: {self.app_config.race_folder}")
        self.log(f"settings フォルダ: {self.app_config.settings_folder}")
        self.log(f"CO 点数: {self.app_config.co_point}")
        self.log("")
        
        # 起動時に自動読み込みを試行
        self._auto_load_on_startup()
        
        # 全画面表示
        self.showMaximized()
    
    def _auto_load_on_startup(self):
        """起動時に設定ファイルを自動読み込み"""
        import os
        
        self.log("【起動時自動読み込み】")
        
        # settings フォルダの存在チェック
        if not os.path.exists(self.app_config.settings_folder):
            self.log(f"⚠ settings フォルダが見つかりません: {self.app_config.settings_folder}")
            self.log("パス設定画面を開きます...")
            self.log("")
            
            # エラーメッセージを表示
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Warning)
            msg.setWindowTitle("設定フォルダが見つかりません")
            msg.setText("設定フォルダが見つかりません。\n\nパス設定画面を開きます。\n「サンプル設定ファイル生成」ボタンで\nサンプル設定を作成できます。")
            msg.setStandardButtons(QMessageBox.Ok)
            msg.exec()
            
            # パス設定画面を開く
            self.set_folders()
            return
        
        # 設定ファイルの自動読み込みを試行
        try:
            self.log("設定ファイルを自動読み込み中...")
            self.config_loader = ConfigLoader(self.app_config.settings_folder)
            success, msg = self.config_loader.load_all()
            
            if success:
                self.log(f"✓ {msg}")
                self.log(f"✓ ゼッケン数: {len(self.config_loader.entries_dict)}")
                self.log(f"✓ 区間数: {len(self.config_loader.section_dict)}")
                self.auto_load_attempted = True
                
                # 保存されたステータスを復元
                self._restore_saved_status()
                
                self.log("")
                self.log("✓ 設定ファイルの自動読み込みが完了しました")
                self.log("次に ② Race読み込み をクリックしてください")
            else:
                self.log(f"⚠ 自動読み込み失敗: {msg}")
                self.log("パス設定画面を開きます...")
                
                # エラーメッセージを表示
                error_msg = QMessageBox()
                error_msg.setIcon(QMessageBox.Warning)
                error_msg.setWindowTitle("設定ファイルの読み込み失敗")
                error_msg.setText(f"設定ファイルの読み込みに失敗しました。\n\n{msg}\n\nパス設定画面を開きます。")
                error_msg.setStandardButtons(QMessageBox.Ok)
                error_msg.exec()
                
                # パス設定画面を開く
                self.set_folders()
        except Exception as e:
            self.log(f"⚠ 自動読み込みエラー: {str(e)}")
            self.log("パス設定画面を開きます...")
            
            # エラーメッセージを表示
            error_msg = QMessageBox()
            error_msg.setIcon(QMessageBox.Warning)
            error_msg.setWindowTitle("設定ファイルの読み込みエラー")
            error_msg.setText(f"設定ファイルの読み込み中にエラーが発生しました。\n\n{str(e)}\n\nパス設定画面を開きます。")
            error_msg.setStandardButtons(QMessageBox.Ok)
            error_msg.exec()
            
            # パス設定画面を開く
            self.set_folders()
        
        self.log("")
    
    def _restore_saved_status(self):
        """保存されたステータス設定を復元"""
        if not self.app_config.status_map and not self.app_config.final_status:
            return
        
        status_count = 0
        
        # 区間ステータスの数をカウント
        for zekken, sections in self.app_config.status_map.items():
            status_count += len(sections)
        
        # 最終ステータスの数をカウント
        status_count += len(self.app_config.final_status)
        
        if status_count > 0:
            self.log(f"✓ 保存済みステータス設定を復元しました（{status_count}件）")

    
    def _create_widgets(self):
        """ウィジェット作成"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # メインレイアウト（縦方向）
        central_layout = QVBoxLayout()
        
        # エラー表示エリア（最上部）- ボタン形式に変更
        error_widget = QWidget()
        error_layout = QHBoxLayout()
        error_layout.setContentsMargins(0, 0, 0, 0)
        
        self.error_status_btn = QPushButton("エラーなし")
        self.error_status_btn.setMinimumHeight(40)
        self.error_status_btn.setStyleSheet("""
            QPushButton {
                background-color: #E8F5E9;
                color: #2E7D32;
                border: 2px solid #4CAF50;
                border-radius: 4px;
                padding: 8px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #C8E6C9;
            }
        """)
        self.error_status_btn.clicked.connect(self._open_error_dialog)
        self.error_status_btn.setVisible(False)  # 初期状態は非表示
        error_layout.addWidget(self.error_status_btn)
        
        error_widget.setLayout(error_layout)
        central_layout.addWidget(error_widget)
        
        # 横方向のメインレイアウト
        main_layout = QHBoxLayout()
        
        # 左側: ログパネル
        left_widget = QWidget()
        left_widget.setMaximumWidth(400)
        left_layout = QVBoxLayout()
        
        # ツールバー
        toolbar_layout = QVBoxLayout()
        
        self.load_settings_btn = QPushButton("① Setting読み込み")
        self.load_settings_btn.clicked.connect(self.load_settings)
        toolbar_layout.addWidget(self.load_settings_btn)
        
        self.load_race_btn = QPushButton("② Race読み込み")
        self.load_race_btn.clicked.connect(self.load_race)
        toolbar_layout.addWidget(self.load_race_btn)
        
        self.calculate_btn = QPushButton("③ 計算実行")
        self.calculate_btn.clicked.connect(self.calculate)
        toolbar_layout.addWidget(self.calculate_btn)
        
        self.show_results_btn = QPushButton("④ 結果表示")
        self.show_results_btn.clicked.connect(self.show_results)
        toolbar_layout.addWidget(self.show_results_btn)
        
        toolbar_layout.addWidget(QLabel(""))
        
        self.export_excel_btn = QPushButton("Excel出力")
        self.export_excel_btn.clicked.connect(self.export_excel)
        toolbar_layout.addWidget(self.export_excel_btn)
        
        self.export_csv_btn = QPushButton("CSV出力")
        self.export_csv_btn.clicked.connect(self.export_csv)
        toolbar_layout.addWidget(self.export_csv_btn)
        
        toolbar_layout.addStretch()
        
        left_layout.addLayout(toolbar_layout)
        
        # ログ表示
        log_label = QLabel("処理ログ")
        log_label.setStyleSheet("font-weight: bold;")
        left_layout.addWidget(log_label)
        
        from PySide6.QtWidgets import QTextEdit
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        left_layout.addWidget(self.log_text)
        
        left_widget.setLayout(left_layout)
        main_layout.addWidget(left_widget)
        
        # 右側: 結果表示（タブ）
        self.tab_widget = QTabWidget()
        
        # 総合成績タブ
        self.summary_widget = SummaryTableWidget()
        self.tab_widget.addTab(self.summary_widget, "総合成績")
        
        # 全日タブ
        self.all_day_widget = ResultTableWidget()
        self.tab_widget.addTab(self.all_day_widget, "全日")
        
        # 日別タブ（後で動的に生成）
        self.day_widgets = []
        
        # クラス別総合成績タブ（後で動的に生成）
        self.class_summary_tab = None
        self.class_summary_widgets = {}
        
        main_layout.addWidget(self.tab_widget, stretch=3)
        
        central_layout.addLayout(main_layout)
        central_widget.setLayout(central_layout)
    
    def _create_menu(self):
        """メニューバー作成"""
        menubar = self.menuBar()
        
        # ファイルメニュー
        file_menu = menubar.addMenu("ファイル")
        
        load_settings_action = QAction("Setting 読み込み", self)
        load_settings_action.triggered.connect(self.load_settings)
        file_menu.addAction(load_settings_action)
        
        load_race_action = QAction("Race データ読み込み", self)
        load_race_action.triggered.connect(self.load_race)
        file_menu.addAction(load_race_action)
        
        file_menu.addSeparator()
        
        export_excel_action = QAction("Excel出力", self)
        export_excel_action.triggered.connect(self.export_excel)
        file_menu.addAction(export_excel_action)
        
        export_csv_action = QAction("CSV出力", self)
        export_csv_action.triggered.connect(self.export_csv)
        file_menu.addAction(export_csv_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("終了", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # ステータスメニュー
        status_menu = menubar.addMenu("ステータス")
        
        section_status_action = QAction("区間ステータス設定", self)
        section_status_action.triggered.connect(self.open_status_matrix)
        status_menu.addAction(section_status_action)
        
        final_status_action = QAction("最終ステータス設定", self)
        final_status_action.triggered.connect(self.open_final_status)
        status_menu.addAction(final_status_action)
        
        # 設定メニュー
        settings_menu = menubar.addMenu("設定")
        
        co_point_action = QAction("CO点数設定", self)
        co_point_action.triggered.connect(self.set_co_point)
        settings_menu.addAction(co_point_action)
        
        folders_action = QAction("フォルダ設定", self)
        folders_action.triggered.connect(self.set_folders)
        settings_menu.addAction(folders_action)
    
    def log(self, message):
        """ログメッセージを表示"""
        self.log_text.append(message)
    
    def _update_error_status(self):
        """エラーステータスボタンを更新"""
        if not self.validation_errors:
            self.error_status_btn.setVisible(False)
            return
        
        # 未確認エラーの数をカウント
        unconfirmed_count = sum(1 for err in self.validation_errors if not err.confirmed)
        total_count = len(self.validation_errors)
        
        if unconfirmed_count > 0:
            # 未確認エラーがある場合
            self.error_status_btn.setText(f"⚠️ エラーあり（未確認: {unconfirmed_count}/{total_count}）")
            self.error_status_btn.setStyleSheet("""
                QPushButton {
                    background-color: #FFEBEE;
                    color: #C62828;
                    border: 2px solid #EF5350;
                    border-radius: 4px;
                    padding: 8px;
                    font-weight: bold;
                    font-size: 14px;
                }
                QPushButton:hover {
                    background-color: #FFCDD2;
                }
            """)
        else:
            # すべて確認済み
            self.error_status_btn.setText(f"✓ エラーなし（確認済み: {total_count}件）")
            self.error_status_btn.setStyleSheet("""
                QPushButton {
                    background-color: #E8F5E9;
                    color: #2E7D32;
                    border: 2px solid #4CAF50;
                    border-radius: 4px;
                    padding: 8px;
                    font-weight: bold;
                    font-size: 14px;
                }
                QPushButton:hover {
                    background-color: #C8E6C9;
                }
            """)
        
        self.error_status_btn.setVisible(True)
    
    def _open_error_dialog(self):
        """エラー確認ダイアログを開く"""
        if not self.validation_errors:
            QMessageBox.information(self, "情報", "エラーはありません。")
            return
        
        dialog = ErrorDialog(self, self.validation_errors)
        dialog.exec()
        
        # ダイアログを閉じた後、ステータスを更新
        self._update_error_status()
    
    def _show_errors(self, errors: List[ValidationError]):
        """エラーメッセージを表示"""
        self.validation_errors = errors
        
        # 以前に確認済みのエラーを復元
        for error in self.validation_errors:
            error_key = error.get_comparison_key()
            if error_key in self.confirmed_errors_map:
                error.confirmed = self.confirmed_errors_map[error_key]
        
        # ステータスを更新
        self._update_error_status()
    
    def _hide_errors(self):
        """エラー表示を非表示にする"""
        self.validation_errors = []
        self.error_status_btn.setVisible(False)
    
    def load_settings(self):
        """Setting 読み込み"""
        self.log("\n" + "=" * 50)
        self.log("【① Setting 読み込み開始】")
        self.log("=" * 50)
        
        try:
            self.log("設定ファイルを読み込み中...")
            self.config_loader = ConfigLoader(self.app_config.settings_folder)
            success, msg = self.config_loader.load_all()
            
            if not success:
                QMessageBox.critical(self, "エラー", msg)
                self.log(f"❌ エラー: {msg}")
                return
            
            self.log(f"✓ {msg}")
            self.log(f"✓ ゼッケン数: {len(self.config_loader.entries_dict)}")
            self.log(f"✓ 区間数: {len(self.config_loader.section_dict)}")
            self.log("")
            self.log("Setting 読み込み完了！")
            self.log("次に ② Race読み込み をクリックしてください")
            
        except Exception as e:
            QMessageBox.critical(self, "エラー", f"Setting 読み込み中にエラーが発生しました:\n{str(e)}")
            self.log(f"❌ エラー: {str(e)}")
    
    def load_race(self):
        """Race データ読み込み"""
        if self.config_loader is None:
            QMessageBox.warning(self, "警告", "先に Setting を読み込んでください")
            self.log("⚠ Warning: 先に ① Setting読み込み を実行してください")
            return
        
        self.log("\n" + "=" * 50)
        self.log("【② Race データ読み込み開始】")
        self.log("=" * 50)
        
        try:
            self.log("race ファイルを解析中...")
            self.race_parser = RaceParser(self.app_config.race_folder)
            success, msg = self.race_parser.parse_all()
            
            if not success:
                QMessageBox.critical(self, "エラー", msg)
                self.log(f"❌ エラー: {msg}")
                return
            
            self.log(f"✓ {msg}")
            zekken_count = len(self.race_parser.get_all_zekkens())
            self.log(f"✓ 検出されたゼッケン数: {zekken_count}")
            self.log("")
            
            # データ検証を実行
            self.log("データ検証を実行中...")
            
            # 以前の確認済みステータスを保存
            for error in self.validation_errors:
                error_key = error.get_comparison_key()
                self.confirmed_errors_map[error_key] = error.confirmed
            
            validation_errors = validate_all(
                self.app_config.race_folder,
                self.race_parser.results,
                self.config_loader.section_list
            )
            
            if validation_errors:
                self.log(f"⚠ 警告: {len(validation_errors)}件のエラー/警告が検出されました")
                self._show_errors(validation_errors)
                for i, error in enumerate(validation_errors, 1):
                    error_msg = str(error).split('\n')[0]  # 最初の行のみログに表示
                    self.log(f"  警告{i}: {error_msg}")
            else:
                self.log("✓ データ検証: 問題なし")
                self._hide_errors()
            
            self.log("")
            self.log("Race データ読み込み完了！")
            self.log("次に ③ 計算実行 をクリックしてください")
            
        except Exception as e:
            QMessageBox.critical(self, "エラー", f"Race データ読み込み中にエラーが発生しました:\n{str(e)}")
            self.log(f"❌ エラー: {str(e)}")
    
    def calculate(self):
        """計算実行"""
        if self.config_loader is None or self.race_parser is None:
            QMessageBox.warning(self, "警告", "先に Setting と Race データを読み込んでください")
            self.log("⚠ Warning: 先に ①②を実行してください")
            return
        
        # 未確認エラーがある場合は警告を表示
        unconfirmed_count = sum(1 for err in self.validation_errors if not err.confirmed)
        if unconfirmed_count > 0:
            reply = QMessageBox.question(
                self,
                "データ検証エラー",
                f"データ検証で{unconfirmed_count}件の未確認エラー/警告が検出されています。\n\n計算を続行しますか？\n\n（エラーの詳細は画面上部のボタンをクリックして確認してください）",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply == QMessageBox.No:
                self.log("⚠ 計算を中止しました。エラーを修正してください。")
                return
        
        self.log("\n" + "=" * 50)
        self.log("【③ 計算実行】")
        self.log("=" * 50)
        
        try:
            self.calc_engine = CalculationEngine(
                self.config_loader,
                self.race_parser,
                self.app_config.co_point
            )
            
            # 保存されたステータス設定を適用
            self.calc_engine.status_map = self.app_config.status_map.copy()
            self.calc_engine.final_status = self.app_config.final_status.copy()
            
            # ステータス適用状況をログに表示
            status_count = sum(len(sections) for sections in self.calc_engine.status_map.values())
            final_status_count = len(self.calc_engine.final_status)
            
            if status_count > 0 or final_status_count > 0:
                self.log(f"✓ 保存済みステータス設定を適用中...")
                if status_count > 0:
                    self.log(f"  - 区間ステータス: {status_count}件")
                if final_status_count > 0:
                    self.log(f"  - 最終ステータス: {final_status_count}件")
            
            self.log("計算中...")
            self.calc_engine.calculate_all()
            
            self.log("✓ 通過時間・差分計算 完了")
            self.log("✓ 順位付け 完了")
            self.log("✓ 得点計算 完了")
            self.log("✓ 総合得点算出 完了")
            
            # 計算完了後、計測データ不備チェックを実行
            self.log("")
            self.log("計測データ不備チェックを実行中...")
            
            # 以前の確認済みステータスを保存
            for error in self.validation_errors:
                error_key = error.get_comparison_key()
                self.confirmed_errors_map[error_key] = error.confirmed
            
            # 再度検証を実行（今度はcalc_engineを渡す）
            validation_errors = validate_all(
                self.app_config.race_folder,
                self.race_parser.results,
                self.config_loader.section_list,
                self.calc_engine
            )
            
            if validation_errors:
                new_error_count = len(validation_errors) - len(self.validation_errors)
                if new_error_count > 0:
                    self.log(f"⚠ 計測データ不備チェック: {new_error_count}件の追加エラーが検出されました")
                self._show_errors(validation_errors)
            
            self.log("")
            self.log("計算完了！")
            self.log("次に ④ 結果表示 をクリックしてください")
            
            self.output_formatter = OutputFormatter(self.calc_engine, self.config_loader)
            
        except Exception as e:
            QMessageBox.critical(self, "エラー", f"計算中にエラーが発生しました:\n{str(e)}")
            self.log(f"❌ エラー: {str(e)}")
    
    def show_results(self):
        """結果表示"""
        if self.calc_engine is None:
            QMessageBox.warning(self, "警告", "先に計算を実行してください")
            self.log("⚠ Warning: 先に ③ 計算実行 を実行してください")
            return
        
        self.log("\n" + "=" * 50)
        self.log("【④ 結果表示】")
        self.log("=" * 50)
        
        try:
            # 総合成績タブに表示
            self.summary_widget.set_data(self.calc_engine, self.config_loader, self.app_config)
            self.log("✓ 総合成績を表示しました")
            
            # 全日タブに表示
            self.all_day_widget.set_data(self.calc_engine, self.config_loader)
            self.log("✓ 全日データを表示しました")
            
            # 既存の日別タブをクリア
            while len(self.day_widgets) > 0:
                widget = self.day_widgets.pop()
                # タブから削除（総合成績と全日の後、インデックス2から）
                tab_index = self.tab_widget.indexOf(widget)
                if tab_index >= 0:
                    self.tab_widget.removeTab(tab_index)
            
            # 日別タブを動的に生成（DAY列に基づく）
            max_day = self.config_loader.get_max_day()
            if max_day > 0:
                for day_idx in range(1, max_day + 1):
                    sections = self.config_loader.get_sections_by_day(day_idx)
                    if sections:
                        widget = ResultTableWidget()
                        widget.set_data(self.calc_engine, self.config_loader)
                        widget.set_filter(sections)
                        self.day_widgets.append(widget)
                        self.tab_widget.addTab(widget, f"{day_idx}日目")
                        self.log(f"✓ {day_idx}日目: {len(sections)}区間")
            else:
                # DAY列がない場合、GROUP列で代替
                self.log("⚠ DAY列が見つからないため、GROUP列を使用します")
                for group_idx in range(1, 10):  # 最大10グループまで試す
                    sections = self.config_loader.get_sections_by_group(group_idx)
                    if sections:
                        widget = ResultTableWidget()
                        widget.set_data(self.calc_engine, self.config_loader)
                        widget.set_filter(sections)
                        self.day_widgets.append(widget)
                        self.tab_widget.addTab(widget, f"グループ{group_idx}")
                        self.log(f"✓ グループ{group_idx}: {len(sections)}区間")
                    elif group_idx > 1 and len(self.day_widgets) > 0:
                        # 連続してセクションが見つからなくなったら終了
                        break
            
            # クラス別総合成績タブを追加
            self._update_class_summary_display()
            
            self.log("✓ 結果を表示しました")
            self.log("")
            self.log("Excel/CSV 出力が可能です")
            
        except Exception as e:
            QMessageBox.critical(self, "エラー", f"結果表示中にエラーが発生しました:\n{str(e)}")
            self.log(f"❌ エラー: {str(e)}")
    
    def _update_class_summary_display(self):
        """クラス別総合成績タブを更新"""
        # 既存のクラス別総合成績タブを削除
        if self.class_summary_tab is not None:
            tab_index = self.tab_widget.indexOf(self.class_summary_tab)
            if tab_index >= 0:
                self.tab_widget.removeTab(tab_index)
            self.class_summary_tab = None
        
        self.class_summary_widgets.clear()
        
        # すべてのクラスを取得
        classes = self.output_formatter.get_all_classes()
        
        if not classes:
            self.log("⚠ クラス情報が見つかりません")
            return
        
        # クラス別総合成績タブを作成
        self.class_summary_tab = QWidget()
        class_summary_layout = QVBoxLayout(self.class_summary_tab)
        
        # クラスごとのサブタブを作成
        class_tab_widget = QTabWidget()
        
        # 「全クラス」タブ（全体表示）
        all_class_widget = SummaryTableWidget()
        all_class_widget.set_data(self.calc_engine, self.config_loader, self.app_config)
        class_tab_widget.addTab(all_class_widget, "全クラス")
        self.class_summary_widgets['全クラス'] = all_class_widget
        
        # 各クラスのタブ
        for class_name in classes:
            widget = SummaryTableWidget()
            widget.set_class_data(self.calc_engine, self.config_loader, self.app_config, class_name)
            class_tab_widget.addTab(widget, class_name)
            self.class_summary_widgets[class_name] = widget
            self.log(f"✓ クラス別総合成績: {class_name}")
        
        class_summary_layout.addWidget(class_tab_widget)
        
        # メインタブに追加（総合成績と区間結果の間、インデックス1）
        self.tab_widget.insertTab(1, self.class_summary_tab, "クラス別総合成績")
        
        self.log(f"✓ クラス別総合成績を表示しました（{len(classes)}クラス）")
    
    def export_excel(self):
        """Excel出力"""
        if self.output_formatter is None:
            QMessageBox.warning(self, "警告", "先に計算を実行してください")
            return
        
        filename, _ = QFileDialog.getSaveFileName(
            self, "Excel ファイルを保存", "", "Excel Files (*.xlsx)"
        )
        
        if not filename:
            return
        
        self.log(f"\nExcel ファイルに出力中: {filename}")
        
        try:
            success = self.output_formatter.export_to_excel(filename)
            if success:
                QMessageBox.information(self, "成功", f"Excel ファイルに出力しました:\n{filename}")
                self.log("✓ Excel 出力完了")
            else:
                QMessageBox.critical(self, "エラー", "Excel ファイルの出力に失敗しました")
        except Exception as e:
            QMessageBox.critical(self, "エラー", f"Excel 出力中にエラーが発生しました:\n{str(e)}")
            self.log(f"❌ エラー: {str(e)}")
    
    def export_csv(self):
        """CSV出力"""
        if self.output_formatter is None:
            QMessageBox.warning(self, "警告", "先に計算を実行してください")
            return
        
        filename, _ = QFileDialog.getSaveFileName(
            self, "CSV ファイルを保存", "", "CSV Files (*.csv)"
        )
        
        if not filename:
            return
        
        self.log(f"\nCSV ファイルに出力中: {filename}")
        
        try:
            success = self.output_formatter.export_to_csv(filename)
            if success:
                QMessageBox.information(self, "成功", f"CSV ファイルに出力しました:\n{filename}")
                self.log("✓ CSV 出力完了")
            else:
                QMessageBox.critical(self, "エラー", "CSV ファイルの出力に失敗しました")
        except Exception as e:
            QMessageBox.critical(self, "エラー", f"CSV 出力中にエラーが発生しました:\n{str(e)}")
            self.log(f"❌ エラー: {str(e)}")
    
    def open_status_matrix(self):
        """区間ステータス設定"""
        if self.config_loader is None:
            QMessageBox.warning(self, "警告", "先に Setting を読み込んでください")
            return
        
        dialog = StatusMatrixDialog(self, self.app_config, self.config_loader)
        dialog.exec()
    
    def open_final_status(self):
        """最終ステータス設定"""
        if self.config_loader is None:
            QMessageBox.warning(self, "警告", "先に Setting を読み込んでください")
            return
        
        dialog = FinalStatusDialog(self, self.app_config, self.config_loader)
        dialog.exec()
    
    def set_co_point(self):
        """CO点数設定"""
        from PySide6.QtWidgets import QInputDialog
        
        value, ok = QInputDialog.getInt(
            self, "CO点数設定", "CO クリア時の点数:",
            self.app_config.co_point, 0, 10000, 1
        )
        
        if ok:
            self.app_config.co_point = value
            self.app_config.save()
            self.log(f"✓ CO 点数を {value} に設定しました")
            QMessageBox.information(self, "成功", f"CO 点数を {value} に設定しました")
    
    def set_folders(self):
        """フォルダ設定"""
        dialog = QDialog(self)
        dialog.setWindowTitle("フォルダ設定")
        dialog.setMinimumWidth(600)
        
        layout = QVBoxLayout()
        
        # フォーム部分
        form_layout = QFormLayout()
        
        race_edit = QLineEdit(self.app_config.race_folder)
        form_layout.addRow("race フォルダ:", race_edit)
        
        settings_edit = QLineEdit(self.app_config.settings_folder)
        form_layout.addRow("settings フォルダ:", settings_edit)
        
        layout.addLayout(form_layout)
        
        # ボタン部分
        button_layout = QHBoxLayout()
        
        save_btn = QPushButton("保存")
        def save():
            self.app_config.race_folder = race_edit.text()
            self.app_config.settings_folder = settings_edit.text()
            self.app_config.save()
            self.log(f"✓ フォルダ設定を保存しました")
            self.log(f"  race: {self.app_config.race_folder}")
            self.log(f"  settings: {self.app_config.settings_folder}")
            QMessageBox.information(dialog, "成功", "フォルダ設定を保存しました")
            dialog.accept()
        
        save_btn.clicked.connect(save)
        button_layout.addWidget(save_btn)
        
        cancel_btn = QPushButton("キャンセル")
        cancel_btn.clicked.connect(dialog.reject)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
        
        # サンプル生成ボタン
        sample_btn = QPushButton("サンプル設定ファイル生成")
        sample_btn.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
        
        def generate_samples():
            import os
            
            # 確認ダイアログ
            reply = QMessageBox.question(
                dialog,
                "サンプル生成確認",
                "サンプル設定ファイルを生成しますか？\n\n"
                "アプリと同じフォルダに settings フォルダを作成し、\n"
                "以下の3つのファイルが生成されます:\n"
                "  - entries_sample.csv\n"
                "  - point_sample.csv\n"
                "  - section_sample.csv\n\n"
                "既存のファイルがある場合は上書きされます。",
                QMessageBox.Yes | QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                try:
                    # アプリの実行ディレクトリを取得
                    if getattr(sys, 'frozen', False):
                        # PyInstallerでビルドされた場合
                        base_path = os.path.dirname(sys.executable)
                    else:
                        # 開発環境の場合
                        base_path = os.path.dirname(os.path.abspath(__file__))
                    
                    # サンプルファイルを生成
                    if generate_sample_files(base_path):
                        settings_path = os.path.join(base_path, 'settings')
                        
                        # 成功メッセージ
                        QMessageBox.information(
                            dialog,
                            "成功",
                            f"サンプルファイルを生成しました。\n\n"
                            f"場所: {settings_path}\n\n"
                            f"パスを自動的に設定しました。"
                        )
                        
                        # パスを自動的にセット
                        self.app_config.settings_folder = settings_path
                        self.app_config.save()
                        
                        self.log(f"✓ サンプルファイルを生成しました: {settings_path}")
                        self.log(f"✓ settings フォルダのパスを設定しました")
                        
                        # ダイアログを閉じる
                        dialog.accept()
                    else:
                        QMessageBox.critical(
                            dialog,
                            "エラー",
                            "サンプルファイルの生成に失敗しました。"
                        )
                        self.log("❌ サンプルファイルの生成に失敗しました")
                        
                except Exception as e:
                    QMessageBox.critical(
                        dialog,
                        "エラー",
                        f"サンプルファイルの生成中にエラーが発生しました:\n{str(e)}"
                    )
                    self.log(f"❌ サンプルファイル生成エラー: {str(e)}")
        
        sample_btn.clicked.connect(generate_samples)
        layout.addWidget(sample_btn)
        
        dialog.setLayout(layout)
        dialog.exec()


def main():
    """メイン関数"""
    app = QApplication(sys.argv)
    
    # スタイル設定
    app.setStyle("Fusion")
    
    # デフォルトフォント設定（MS Sans Serifエラー回避）
    default_font = QFont("Yu Gothic UI", 9)
    app.setFont(default_font)
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
