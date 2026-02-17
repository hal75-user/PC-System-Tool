"""
GUI メインモジュール（PySide6版）
PySide6 を使った高機能 GUI アプリケーション
"""

import sys
import pandas as pd
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

# ロギング初期化
init_app_logging()
logger = get_logger(__name__)


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
        self.setMinimumSize(400, 500)
        
        self.zekkens = sorted(config_loader.entries_dict.keys())
        self.status_options = ["", "RIT", "N.C.", "BLNK"]
        
        # 現在選択されているステータス
        self.current_status = ""
        
        self._create_widgets()
        self._load_current_status()
    
    def _create_widgets(self):
        layout = QVBoxLayout()
        
        # 説明
        label = QLabel("セルをクリックして選択し、選択中のステータスを適用します")
        layout.addWidget(label)
        
        # トグルボタン配置
        button_layout = QHBoxLayout()
        button_layout.addWidget(QLabel("ステータス選択:"))
        
        self.status_buttons = {}
        for status in self.status_options:
            btn_text = "空白" if status == "" else status
            btn = QPushButton(btn_text)
            btn.setCheckable(True)
            btn.setMinimumWidth(80)
            if status == "":
                btn.setChecked(True)  # デフォルトで空白を選択
            btn.clicked.connect(lambda checked, s=status: self._on_status_selected(s))
            self.status_buttons[status] = btn
            button_layout.addWidget(btn)
        
        button_layout.addStretch()
        layout.addLayout(button_layout)
        
        # テーブル
        self.table = QTableWidget()
        self.table.setRowCount(len(self.zekkens))
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels(["ゼッケン", "最終ステータス"])
        
        # 複数セル選択を有効化
        self.table.setSelectionMode(QTableWidget.MultiSelection)
        
        # セルクリック/変更イベント
        self.table.itemClicked.connect(self._on_cell_clicked)
        self.table.itemSelectionChanged.connect(self._on_selection_changed)
        
        for row_idx, zekken in enumerate(self.zekkens):
            # ゼッケン列
            zekken_item = QTableWidgetItem(str(zekken))
            zekken_item.setFlags(Qt.ItemIsEnabled)
            zekken_item.setBackground(QBrush(QColor(240, 240, 240)))
            self.table.setItem(row_idx, 0, zekken_item)
            
            # ステータス列
            status_item = QTableWidgetItem("")
            status_item.setTextAlignment(Qt.AlignCenter)
            status_item.setData(Qt.UserRole, zekken)
            self.table.setItem(row_idx, 1, status_item)
        
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
        """現在のステータス設定を読み込んでテーブルに反映"""
        for row_idx, zekken in enumerate(self.zekkens):
            current_status = self.app_config.get_final_status(zekken) or ""
            item = self.table.item(row_idx, 1)
            if item:
                item.setText(current_status)
                self._update_cell_color(item, current_status)
    
    def _on_status_selected(self, status):
        """ステータスボタンが選択された時"""
        # 他のボタンをオフにする
        for s, btn in self.status_buttons.items():
            btn.setChecked(s == status)
        
        self.current_status = status
    
    def _on_cell_clicked(self, item):
        """セルがクリックされた時"""
        if item.column() == 0:  # ゼッケン列はスキップ
            return
        
        # 現在選択されているステータスを適用
        self._apply_status_to_item(item)
    
    def _on_selection_changed(self):
        """選択が変更された時（複数選択）"""
        selected_items = self.table.selectedItems()
        for item in selected_items:
            if item.column() == 1:  # ステータス列のみ
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
    
    def _save(self):
        """ステータスを保存"""
        self.app_config.final_status = {}
        
        for row_idx, zekken in enumerate(self.zekkens):
            item = self.table.item(row_idx, 1)
            if item:
                status = item.text()
                if status:
                    self.app_config.set_final_status(zekken, status)
        
        self.app_config.save()
        QMessageBox.information(self, "成功", "最終ステータス設定を保存しました")
        self.accept()
    
    def _clear_all(self):
        """すべてクリア"""
        reply = QMessageBox.question(self, "確認", "すべての最終ステータス設定をクリアしますか？")
        if reply == QMessageBox.Yes:
            for row_idx in range(self.table.rowCount()):
                item = self.table.item(row_idx, 1)
                if item:
                    item.setText("")
                    self._update_cell_color(item, "")


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
        
        # フィルターボタン（スクロール可能、折り返し対応）
        filter_container = QWidget()
        filter_container_layout = QVBoxLayout(filter_container)
        filter_container_layout.setContentsMargins(0, 0, 0, 0)
        
        # 「すべて表示」ボタン
        self.all_btn = QPushButton("すべて表示")
        self.all_btn.clicked.connect(lambda: self.set_filter(None))
        filter_container_layout.addWidget(self.all_btn)
        
        # 区間ジャンプボタン用のスクロールエリア
        button_scroll = QScrollArea()
        button_scroll.setWidgetResizable(True)
        button_scroll.setMaximumHeight(120)  # 3-4行程度の高さ
        button_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        button_widget = QWidget()
        self.filter_button_layout = QGridLayout(button_widget)  # QGridLayoutで折り返し対応
        self.filter_button_layout.setSpacing(5)
        self.filter_button_layout.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        
        button_scroll.setWidget(button_widget)
        filter_container_layout.addWidget(button_scroll)
        
        layout.addWidget(filter_container)
        
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
        
        self._create_filter_buttons()
        self._populate_table()
    
    def _create_filter_buttons(self):
        """区間ジャンプボタンを作成（フィルターに応じて絞る）"""
        # 既存のボタンをクリア
        while self.filter_button_layout.count() > 0:
            item = self.filter_button_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # 表示する区間を決定（フィルターがあればそれを使う）
        if self.filter_sections is None:
            sections = self.config_loader.get_section_order()
        else:
            sections = self.filter_sections
        
        # 区間ボタンをグリッドに配置（1行に10個まで）
        cols_per_row = 10
        for idx, section in enumerate(sections):
            row = idx // cols_per_row
            col = idx % cols_per_row
            btn = QPushButton(section)
            btn.setMaximumWidth(80)
            btn.clicked.connect(lambda checked, s=section: self.jump_to_section(s))
            self.filter_button_layout.addWidget(btn, row, col)
    
    def jump_to_section(self, section):
        """指定した区間にスクロールしてジャンプ"""
        # 表示中の区間リストを使用
        if self.filter_sections is None:
            sections = self.config_loader.get_section_order()
        else:
            sections = self.filter_sections
        
        try:
            section_idx = sections.index(section)
            # 4個の固定列 + (section_idx * 6列)
            col_idx = 4 + (section_idx * 6)
            # その列にスクロール
            if self.table.rowCount() > 0 and self.table.item(0, col_idx):
                self.table.scrollToItem(self.table.item(0, col_idx), QAbstractItemView.PositionAtCenter)
        except (ValueError, AttributeError):
            pass
    
    def set_filter(self, sections):
        """フィルターを設定"""
        self.filter_sections = sections
        self._create_filter_buttons()  # ボタンも再生成
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
        else:
            sections = self.filter_sections
        
        # ゼッケン一覧
        zekkens = sorted(self.calc_engine.results.keys())
        
        # カラム構成（2段ヘッダー：改行で区切る）
        columns = ["ゼッケン", "ドライバー名", "総合得点", "総合順位"]
        
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
            
            total_score = self.calc_engine.get_total_score(zekken)
            self._set_item(row_idx, 2, str(total_score))
            
            # 総合順位を表示
            rank_str = "-"
            if hasattr(self, 'summary_df'):
                rank_row = self.summary_df[self.summary_df['ゼッケン'] == zekken]
                if not rank_row.empty:
                    rank_value = rank_row.iloc[0]['順位']
                    if pd.notna(rank_value):
                        if isinstance(rank_value, (int, float)):
                            rank_str = str(int(rank_value))
                        else:
                            rank_str = str(rank_value)
            
            self._set_item(row_idx, 3, rank_str)
            
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
                            self._color_diff_cell(item, result.diff)
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
                    
                    # 差分（色付き）- 秒単位で±00.00形式
                    diff_str = self._format_diff_simple(result.diff) if result.diff is not None else "ー"
                    item = self._set_item(row_idx, col_idx, diff_str)
                    if result.diff is not None:
                        self._color_diff_cell(item, result.diff)
                    col_idx += 1
                    
                    # 順位（色付き）
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
            elif col_name == "総合得点":
                self.table.setColumnWidth(col_idx, 70)
            elif col_name == "総合順位":
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
    
    def _color_diff_cell(self, item, diff):
        """差分セルに色を付ける"""
        abs_diff = abs(diff)
        
        if abs_diff <= 0.5:
            color = QColor(0, 150, 0)  # 濃い緑
        elif abs_diff <= 1.0:
            color = QColor(0, 200, 0)  # 緑
        elif abs_diff <= 2.0:
            color = QColor(150, 255, 150)  # 薄い緑
        elif abs_diff <= 5.0:
            color = QColor(255, 255, 0)  # 黄色
        elif abs_diff <= 10.0:
            color = QColor(255, 165, 0)  # オレンジ
        else:
            color = QColor(255, 100, 100)  # 赤
        
        item.setBackground(QBrush(color))
    
    def _color_rank_cell(self, item, rank):
        """順位セルに色を付ける"""
        if rank == 1:
            color = QColor(255, 215, 0)  # 金色
        elif rank == 2:
            color = QColor(192, 192, 192)  # 銀色
        elif rank == 3:
            color = QColor(205, 127, 50)  # 銅色
        elif rank <= 10:
            color = QColor(173, 216, 230)  # 薄い青
        else:
            return
        
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
            
            # 車両製造年
            year_item = QTableWidgetItem(str(row.get('車両製造年', '')))
            year_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row_idx, 5, year_item)
            
            # CarClass
            class_item = QTableWidgetItem(str(row.get('CarClass', '')))
            class_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row_idx, 6, class_item)
            
            # Point (純粋な得点)
            point_item = QTableWidgetItem(str(row.get('Point', 0)))
            point_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row_idx, 7, point_item)
            
            # H.C.L Point
            hcl_item = QTableWidgetItem(str(hcl_point))
            hcl_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row_idx, 8, hcl_item)
            
            # Penalty(-) - 赤字表記（0の場合も表示）
            penalty_item = QTableWidgetItem(str(int(penalty)))
            penalty_item.setTextAlignment(Qt.AlignCenter)
            if penalty > 0:
                penalty_item.setForeground(QBrush(QColor(255, 0, 0)))  # 赤字
            self.table.setItem(row_idx, 9, penalty_item)
            
            # TotalPoint
            total_item = QTableWidgetItem(str(int(total_point)))
            total_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row_idx, 10, total_item)


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
            self.log("フォルダを設定してから ① Setting読み込み をクリックしてください")
            self.log("")
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
                self.log("手動で ① Setting読み込み をクリックしてください")
        except Exception as e:
            self.log(f"⚠ 自動読み込みエラー: {str(e)}")
            self.log("手動で ① Setting読み込み をクリックしてください")
        
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
        
        main_layout.addWidget(self.tab_widget, stretch=3)
        
        central_widget.setLayout(main_layout)
    
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
            
            self.log("✓ 結果を表示しました")
            self.log("")
            self.log("Excel/CSV 出力が可能です")
            
        except Exception as e:
            QMessageBox.critical(self, "エラー", f"結果表示中にエラーが発生しました:\n{str(e)}")
            self.log(f"❌ エラー: {str(e)}")
    
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
        
        layout = QFormLayout()
        
        race_edit = QLineEdit(self.app_config.race_folder)
        layout.addRow("race フォルダ:", race_edit)
        
        settings_edit = QLineEdit(self.app_config.settings_folder)
        layout.addRow("settings フォルダ:", settings_edit)
        
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
        
        layout.addRow(button_layout)
        
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
