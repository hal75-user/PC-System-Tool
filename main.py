"""
GUI メインモジュール
tkinter を使った GUI アプリケーション
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
import os
from config_loader import ConfigLoader
from race_parser import RaceParser
from calculation_engine import CalculationEngine
from output_formatter import OutputFormatter
from app_config import AppConfig


class StatusMatrixDialog:
    """ステータス設定マトリックスダイアログ"""
    
    def __init__(self, parent, app_config, config_loader):
        self.app_config = app_config
        self.config_loader = config_loader
        
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("区間ステータス設定")
        self.dialog.geometry("900x600")
        
        # ゼッケンと区間のリストを取得
        self.zekkens = sorted(config_loader.entries_dict.keys())
        self.sections = config_loader.get_section_order()
        
        # ステータス選択肢
        self.status_options = ["", "RIT", "N.C.", "BLNK"]
        
        # コンボボックスの辞書
        self.combos = {}
        
        self._create_widgets()
    
    def _create_widgets(self):
        """ウィジェット作成"""
        # 説明ラベル
        ttk.Label(self.dialog, text="各ゼッケン・区間にステータスを設定してください（空欄=通常）").pack(pady=5)
        
        # スクロール可能なフレーム
        canvas = tk.Canvas(self.dialog)
        scrollbar_y = ttk.Scrollbar(self.dialog, orient="vertical", command=canvas.yview)
        scrollbar_x = ttk.Scrollbar(self.dialog, orient="horizontal", command=canvas.xview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar_y.set, xscrollcommand=scrollbar_x.set)
        
        # ヘッダー行（区間名）
        ttk.Label(scrollable_frame, text="ゼッケン", font=("", 9, "bold")).grid(row=0, column=0, padx=2, pady=2, sticky="ew")
        
        for col_idx, section in enumerate(self.sections, start=1):
            ttk.Label(scrollable_frame, text=section, font=("", 8, "bold")).grid(row=0, column=col_idx, padx=2, pady=2)
        
        # 各ゼッケン行
        for row_idx, zekken in enumerate(self.zekkens, start=1):
            # ゼッケン番号
            ttk.Label(scrollable_frame, text=str(zekken), font=("", 9, "bold")).grid(row=row_idx, column=0, padx=2, pady=2, sticky="ew")
            
            # 各区間のコンボボックス
            for col_idx, section in enumerate(self.sections, start=1):
                # 現在のステータスを取得
                current_status = self.app_config.get_section_status(zekken, section)
                if current_status is None:
                    current_status = ""
                
                combo = ttk.Combobox(scrollable_frame, values=self.status_options, width=6, state="readonly")
                combo.set(current_status)
                combo.grid(row=row_idx, column=col_idx, padx=1, pady=1)
                
                self.combos[(zekken, section)] = combo
        
        canvas.pack(side="left", fill="both", expand=True, padx=5, pady=5)
        scrollbar_y.pack(side="right", fill="y")
        scrollbar_x.pack(side="bottom", fill="x")
        
        # ボタンフレーム
        button_frame = ttk.Frame(self.dialog)
        button_frame.pack(side="bottom", fill="x", padx=5, pady=5)
        
        ttk.Button(button_frame, text="保存", command=self._save).pack(side="left", padx=5)
        ttk.Button(button_frame, text="キャンセル", command=self.dialog.destroy).pack(side="left", padx=5)
        ttk.Button(button_frame, text="すべてクリア", command=self._clear_all).pack(side="left", padx=5)
    
    def _save(self):
        """ステータスを保存"""
        # すべてのステータスをクリア
        self.app_config.status_map = {}
        
        # コンボボックスから値を取得
        for (zekken, section), combo in self.combos.items():
            status = combo.get()
            if status and status != "":
                self.app_config.set_section_status(zekken, section, status)
        
        # 保存
        self.app_config.save()
        messagebox.showinfo("成功", "ステータス設定を保存しました")
        self.dialog.destroy()
    
    def _clear_all(self):
        """すべてクリア"""
        if messagebox.askyesno("確認", "すべてのステータス設定をクリアしますか？"):
            for combo in self.combos.values():
                combo.set("")


class FinalStatusDialog:
    """最終ステータス設定ダイアログ"""
    
    def __init__(self, parent, app_config, config_loader):
        self.app_config = app_config
        self.config_loader = config_loader
        
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("最終ステータス設定")
        self.dialog.geometry("400x500")
        
        # ゼッケンのリストを取得
        self.zekkens = sorted(config_loader.entries_dict.keys())
        
        # ステータス選択肢
        self.status_options = ["", "RIT", "N.C.", "BLNK"]
        
        # コンボボックスの辞書
        self.combos = {}
        
        self._create_widgets()
    
    def _create_widgets(self):
        """ウィジェット作成"""
        # 説明ラベル
        ttk.Label(self.dialog, text="各ゼッケンの最終ステータスを設定してください（空欄=通常）").pack(pady=5)
        
        # スクロール可能なフレーム
        canvas = tk.Canvas(self.dialog)
        scrollbar = ttk.Scrollbar(self.dialog, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # ヘッダー
        ttk.Label(scrollable_frame, text="ゼッケン", font=("", 9, "bold")).grid(row=0, column=0, padx=5, pady=5)
        ttk.Label(scrollable_frame, text="最終ステータス", font=("", 9, "bold")).grid(row=0, column=1, padx=5, pady=5)
        
        # 各ゼッケン行
        for idx, zekken in enumerate(self.zekkens, start=1):
            ttk.Label(scrollable_frame, text=str(zekken)).grid(row=idx, column=0, padx=5, pady=2)
            
            # 現在のステータスを取得
            current_status = self.app_config.get_final_status(zekken)
            if current_status is None:
                current_status = ""
            
            combo = ttk.Combobox(scrollable_frame, values=self.status_options, width=10, state="readonly")
            combo.set(current_status)
            combo.grid(row=idx, column=1, padx=5, pady=2)
            
            self.combos[zekken] = combo
        
        canvas.pack(side="left", fill="both", expand=True, padx=5, pady=5)
        scrollbar.pack(side="right", fill="y")
        
        # ボタンフレーム
        button_frame = ttk.Frame(self.dialog)
        button_frame.pack(side="bottom", fill="x", padx=5, pady=5)
        
        ttk.Button(button_frame, text="保存", command=self._save).pack(side="left", padx=5)
        ttk.Button(button_frame, text="キャンセル", command=self.dialog.destroy).pack(side="left", padx=5)
        ttk.Button(button_frame, text="すべてクリア", command=self._clear_all).pack(side="left", padx=5)
    
    def _save(self):
        """ステータスを保存"""
        # すべてのステータスをクリア
        self.app_config.final_status = {}
        
        # コンボボックスから値を取得
        for zekken, combo in self.combos.items():
            status = combo.get()
            if status and status != "":
                self.app_config.set_final_status(zekken, status)
        
        # 保存
        self.app_config.save()
        messagebox.showinfo("成功", "最終ステータス設定を保存しました")
        self.dialog.destroy()
    
    def _clear_all(self):
        """すべてクリア"""
        if messagebox.askyesno("確認", "すべての最終ステータス設定をクリアしますか？"):
            for combo in self.combos.values():
                combo.set("")


class MainWindow:
    """メインウィンドウクラス"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("PC System Tool")
        self.root.geometry("1400x800")
        
        # 各モジュールの初期化
        self.app_config = AppConfig()
        self.config_loader = None
        self.race_parser = None
        self.calc_engine = None
        self.output_formatter = None
        
        # GUI 構築
        self._create_widgets()
    
    def _create_widgets(self):
        """ウィジェットを作成"""
        # メニューバー
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # ファイルメニュー
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="ファイル", menu=file_menu)
        file_menu.add_command(label="Setting 読み込み", command=self.load_settings)
        file_menu.add_command(label="Race データ読み込み", command=self.load_race)
        file_menu.add_separator()
        file_menu.add_command(label="Excel出力", command=self.export_excel)
        file_menu.add_command(label="CSV出力", command=self.export_csv)
        file_menu.add_separator()
        file_menu.add_command(label="終了", command=self.root.quit)
        
        # ステータスメニュー
        status_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="ステータス", menu=status_menu)
        status_menu.add_command(label="区間ステータス設定", command=self.open_status_matrix)
        status_menu.add_command(label="最終ステータス設定", command=self.open_final_status)
        
        # 設定メニュー
        settings_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="設定", menu=settings_menu)
        settings_menu.add_command(label="CO点数設定", command=self.set_co_point)
        settings_menu.add_command(label="フォルダ設定", command=self.set_folders)
        
        # ツールバー
        toolbar = ttk.Frame(self.root)
        toolbar.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)
        
        ttk.Button(toolbar, text="① Setting読み込み", command=self.load_settings, width=18).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="② Race読み込み", command=self.load_race, width=18).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="③ 計算実行", command=self.calculate, width=18).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="④ 結果表示", command=self.show_results, width=18).pack(side=tk.LEFT, padx=2)
        
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=10)
        
        ttk.Button(toolbar, text="Excel出力", command=self.export_excel, width=12).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="CSV出力", command=self.export_csv, width=12).pack(side=tk.LEFT, padx=2)
        
        # メインフレーム（ログと結果を分離）
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 左側: ログパネル
        left_frame = ttk.LabelFrame(main_frame, text="処理ログ", width=350)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, padx=5)
        left_frame.pack_propagate(False)
        
        # ステータス表示
        log_scroll = ttk.Scrollbar(left_frame)
        log_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.status_text = tk.Text(left_frame, height=10, width=40, yscrollcommand=log_scroll.set)
        self.status_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        log_scroll.config(command=self.status_text.yview)
        
        # 右側: 結果表示エリア（タブ形式）
        right_frame = ttk.LabelFrame(main_frame, text="結果表示")
        right_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)
        
        # タブコントロール
        self.notebook = ttk.Notebook(right_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # タブ1: 詳細結果
        detail_frame = ttk.Frame(self.notebook)
        self.notebook.add(detail_frame, text="詳細結果")
        
        # スクロールバー付きテキストエリア（詳細）
        detail_scroll_y = ttk.Scrollbar(detail_frame, orient=tk.VERTICAL)
        detail_scroll_x = ttk.Scrollbar(detail_frame, orient=tk.HORIZONTAL)
        
        self.detail_text = tk.Text(detail_frame, 
                                   yscrollcommand=detail_scroll_y.set,
                                   xscrollcommand=detail_scroll_x.set,
                                   wrap=tk.NONE,
                                   font=("Courier New", 9))
        
        detail_scroll_y.config(command=self.detail_text.yview)
        detail_scroll_x.config(command=self.detail_text.xview)
        
        detail_scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        detail_scroll_x.pack(side=tk.BOTTOM, fill=tk.X)
        self.detail_text.pack(fill=tk.BOTH, expand=True)
        
        # タブ2: 総合順位
        summary_frame = ttk.Frame(self.notebook)
        self.notebook.add(summary_frame, text="総合順位")
        
        # スクロールバー付きテキストエリア（総合順位）
        summary_scroll = ttk.Scrollbar(summary_frame, orient=tk.VERTICAL)
        
        self.summary_text = tk.Text(summary_frame, 
                                    yscrollcommand=summary_scroll.set,
                                    font=("Courier New", 11))
        
        summary_scroll.config(command=self.summary_text.yview)
        
        summary_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.summary_text.pack(fill=tk.BOTH, expand=True)
        
        # 初期メッセージ
        self.log("=" * 50)
        self.log("PC System Tool を起動しました")
        self.log("=" * 50)
        self.log(f"race フォルダ: {self.app_config.race_folder}")
        self.log(f"settings フォルダ: {self.app_config.settings_folder}")
        self.log(f"CO 点数: {self.app_config.co_point}")
        self.log("")
        self.log("①〜④の順にボタンをクリックしてください")
    
    def log(self, message: str):
        """ログメッセージを表示"""
        self.status_text.insert(tk.END, message + "\n")
        self.status_text.see(tk.END)
        self.status_text.update()
    
    def load_settings(self):
        """設定ファイルを読み込む"""
        self.log("\n" + "=" * 50)
        self.log("【① Setting 読み込み開始】")
        self.log("=" * 50)
        
        try:
            # 設定ファイル読み込み
            self.log("設定ファイルを読み込み中...")
            self.config_loader = ConfigLoader(self.app_config.settings_folder)
            success, msg = self.config_loader.load_all()
            
            if not success:
                messagebox.showerror("エラー", msg)
                self.log(f"❌ エラー: {msg}")
                return
            
            self.log(f"✓ {msg}")
            self.log(f"✓ ゼッケン数: {len(self.config_loader.entries_dict)}")
            self.log(f"✓ 区間数: {len(self.config_loader.section_dict)}")
            self.log("")
            self.log("Setting 読み込み完了！")
            self.log("次に ② Race読み込み をクリックしてください")
            
        except Exception as e:
            messagebox.showerror("エラー", f"Setting 読み込み中にエラーが発生しました:\n{str(e)}")
            self.log(f"❌ エラー: {str(e)}")
    
    def load_race(self):
        """race ファイルを読み込む"""
        if self.config_loader is None:
            messagebox.showwarning("警告", "先に Setting を読み込んでください")
            self.log("⚠ Warning: 先に ① Setting読み込み を実行してください")
            return
        
        self.log("\n" + "=" * 50)
        self.log("【② Race データ読み込み開始】")
        self.log("=" * 50)
        
        try:
            # race ファイル解析
            self.log("race ファイルを解析中...")
            self.race_parser = RaceParser(self.app_config.race_folder)
            success, msg = self.race_parser.parse_all()
            
            if not success:
                messagebox.showerror("エラー", msg)
                self.log(f"❌ エラー: {msg}")
                return
            
            self.log(f"✓ {msg}")
            zekken_count = len(self.race_parser.get_all_zekkens())
            self.log(f"✓ 検出されたゼッケン数: {zekken_count}")
            self.log("")
            self.log("Race データ読み込み完了！")
            self.log("次に ③ 計算実行 をクリックしてください")
            
        except Exception as e:
            messagebox.showerror("エラー", f"Race データ読み込み中にエラーが発生しました:\n{str(e)}")
            self.log(f"❌ エラー: {str(e)}")
    
    def calculate(self):
        """計算を実行"""
        if self.config_loader is None or self.race_parser is None:
            messagebox.showwarning("警告", "先に Setting と Race データを読み込んでください")
            self.log("⚠ Warning: 先に ①②を実行してください")
            return
        
        self.log("\n" + "=" * 50)
        self.log("【③ 計算実行】")
        self.log("=" * 50)
        
        try:
            # 計算エンジン初期化
            self.calc_engine = CalculationEngine(
                self.config_loader, 
                self.race_parser, 
                self.app_config.co_point
            )
            
            # アプリ設定からステータスを読み込み
            self.calc_engine.status_map = self.app_config.status_map.copy()
            self.calc_engine.final_status = self.app_config.final_status.copy()
            
            self.log("計算中...")
            
            # 計算実行
            self.calc_engine.calculate_all()
            self.log("✓ 通過時間・差分計算 完了")
            self.log("✓ 順位付け 完了")
            self.log("✓ 得点計算 完了")
            self.log("✓ 総合得点算出 完了")
            self.log("")
            self.log("計算完了！")
            self.log("次に ④ 結果表示 をクリックしてください")
            
            # 出力フォーマッター初期化
            self.output_formatter = OutputFormatter(self.calc_engine, self.config_loader)
            
        except Exception as e:
            messagebox.showerror("エラー", f"計算中にエラーが発生しました:\n{str(e)}")
            self.log(f"❌ エラー: {str(e)}")
    
    def show_results(self):
        """結果を表示"""
        if self.output_formatter is None:
            messagebox.showwarning("警告", "先に計算を実行してください")
            self.log("⚠ Warning: 先に ③ 計算実行 を実行してください")
            return
        
        self.log("\n" + "=" * 50)
        self.log("【④ 結果表示】")
        self.log("=" * 50)
        
        try:
            # 詳細結果 DataFrame 作成
            detail_df = self.output_formatter.create_dataframe()
            
            # 詳細タブにクリア
            self.detail_text.delete(1.0, tk.END)
            
            # DataFrame を文字列に変換して表示
            detail_str = detail_df.to_string(index=False, max_colwidth=15)
            self.detail_text.insert(1.0, detail_str)
            
            # 総合順位 DataFrame 作成
            summary_df = self.output_formatter.get_summary_dataframe()
            
            # 総合順位タブにクリア
            self.summary_text.delete(1.0, tk.END)
            
            # ヘッダー
            self.summary_text.insert(tk.END, "\n")
            self.summary_text.insert(tk.END, "=" * 60 + "\n")
            self.summary_text.insert(tk.END, "                    総合順位表\n")
            self.summary_text.insert(tk.END, "=" * 60 + "\n\n")
            
            # 総合順位を整形して表示
            self.summary_text.insert(tk.END, f"{'順位':<8}{'ゼッケン':<12}{'総合得点':<15}\n")
            self.summary_text.insert(tk.END, "-" * 60 + "\n")
            
            for _, row in summary_df.iterrows():
                rank = row['順位']
                zekken = row['ゼッケン']
                score = row['総合得点']
                
                if isinstance(rank, str):
                    # ステータス（RIT/N.C./BLNK）
                    self.summary_text.insert(tk.END, f"{rank:<8}{zekken:<12}{score:<15}\n")
                else:
                    # 通常の順位
                    self.summary_text.insert(tk.END, f"{rank:<8}{zekken:<12}{score:<15}\n")
            
            self.summary_text.insert(tk.END, "\n" + "=" * 60 + "\n")
            
            # タブを総合順位に切り替え
            self.notebook.select(1)
            
            self.log("✓ 結果を表示しました")
            self.log("")
            self.log("Excel/CSV 出力が可能です")
            
        except Exception as e:
            messagebox.showerror("エラー", f"結果表示中にエラーが発生しました:\n{str(e)}")
            self.log(f"❌ エラー: {str(e)}")
    
    def export_excel(self):
        """Excel ファイルに出力"""
        if self.output_formatter is None:
            messagebox.showwarning("警告", "先に計算を実行してください")
            return
        
        filename = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel files", "*.xlsx"), ("All files", "*.*")]
        )
        
        if not filename:
            return
        
        self.log(f"\nExcel ファイルに出力中: {filename}")
        
        try:
            success = self.output_formatter.export_to_excel(filename)
            if success:
                messagebox.showinfo("成功", f"Excel ファイルに出力しました:\n{filename}")
                self.log("✓ Excel 出力完了")
            else:
                messagebox.showerror("エラー", "Excel ファイルの出力に失敗しました")
        
        except Exception as e:
            messagebox.showerror("エラー", f"Excel 出力中にエラーが発生しました:\n{str(e)}")
            self.log(f"❌ エラー: {str(e)}")
    
    def export_csv(self):
        """CSV ファイルに出力"""
        if self.output_formatter is None:
            messagebox.showwarning("警告", "先に計算を実行してください")
            return
        
        filename = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        
        if not filename:
            return
        
        self.log(f"\nCSV ファイルに出力中: {filename}")
        
        try:
            success = self.output_formatter.export_to_csv(filename)
            if success:
                messagebox.showinfo("成功", f"CSV ファイルに出力しました:\n{filename}")
                self.log("✓ CSV 出力完了")
            else:
                messagebox.showerror("エラー", "CSV ファイルの出力に失敗しました")
        
        except Exception as e:
            messagebox.showerror("エラー", f"CSV 出力中にエラーが発生しました:\n{str(e)}")
            self.log(f"❌ エラー: {str(e)}")
    
    def open_status_matrix(self):
        """区間ステータス設定ダイアログを開く"""
        if self.config_loader is None:
            messagebox.showwarning("警告", "先に Setting を読み込んでください")
            return
        
        StatusMatrixDialog(self.root, self.app_config, self.config_loader)
    
    def open_final_status(self):
        """最終ステータス設定ダイアログを開く"""
        if self.config_loader is None:
            messagebox.showwarning("警告", "先に Setting を読み込んでください")
            return
        
        FinalStatusDialog(self.root, self.app_config, self.config_loader)
    
    def set_co_point(self):
        """CO 点数を設定"""
        dialog = tk.Toplevel(self.root)
        dialog.title("CO 点数設定")
        dialog.geometry("350x180")
        
        frame = ttk.Frame(dialog, padding=20)
        frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(frame, text="CO クリア時の点数:", font=("", 10)).pack(pady=10)
        
        entry = ttk.Entry(frame, width=15, font=("", 11))
        entry.insert(0, str(self.app_config.co_point))
        entry.pack(pady=5)
        
        def save():
            try:
                value = int(entry.get())
                self.app_config.co_point = value
                self.app_config.save()
                self.log(f"✓ CO 点数を {value} に設定しました")
                messagebox.showinfo("成功", f"CO 点数を {value} に設定しました")
                dialog.destroy()
            except ValueError:
                messagebox.showerror("エラー", "数値を入力してください")
        
        button_frame = ttk.Frame(frame)
        button_frame.pack(pady=20)
        
        ttk.Button(button_frame, text="保存", command=save, width=10).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="キャンセル", command=dialog.destroy, width=10).pack(side=tk.LEFT, padx=5)
    
    def set_folders(self):
        """フォルダ設定"""
        dialog = tk.Toplevel(self.root)
        dialog.title("フォルダ設定")
        dialog.geometry("500x220")
        
        frame = ttk.Frame(dialog, padding=20)
        frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(frame, text="race フォルダ:", font=("", 10)).grid(row=0, column=0, padx=5, pady=10, sticky=tk.W)
        race_entry = ttk.Entry(frame, width=40)
        race_entry.insert(0, self.app_config.race_folder)
        race_entry.grid(row=0, column=1, padx=5, pady=10)
        
        ttk.Label(frame, text="settings フォルダ:", font=("", 10)).grid(row=1, column=0, padx=5, pady=10, sticky=tk.W)
        settings_entry = ttk.Entry(frame, width=40)
        settings_entry.insert(0, self.app_config.settings_folder)
        settings_entry.grid(row=1, column=1, padx=5, pady=10)
        
        def save():
            self.app_config.race_folder = race_entry.get()
            self.app_config.settings_folder = settings_entry.get()
            self.app_config.save()
            self.log(f"✓ フォルダ設定を保存しました")
            self.log(f"  race: {self.app_config.race_folder}")
            self.log(f"  settings: {self.app_config.settings_folder}")
            messagebox.showinfo("成功", "フォルダ設定を保存しました")
            dialog.destroy()
        
        button_frame = ttk.Frame(frame)
        button_frame.grid(row=2, column=0, columnspan=2, pady=20)
        
        ttk.Button(button_frame, text="保存", command=save, width=10).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="キャンセル", command=dialog.destroy, width=10).pack(side=tk.LEFT, padx=5)


def main():
    """メイン関数"""
    root = tk.Tk()
    app = MainWindow(root)
    root.mainloop()


if __name__ == "__main__":
    main()
