# PC-System-Tool 改善計画

## 🎯 目的
現在のPythonアプリケーションの安定性と保守性を向上させる

## 📋 実施事項（優先度順）

### 🔴 Phase 1: 緊急対応（即座に実施）

#### 1.1 ロギング機能の追加
**目的**: デバッグと問題追跡を容易にする

**実装内容:**
```python
# logging_config.py を新規作成
import logging
import logging.handlers
from pathlib import Path

def setup_logging(log_level=logging.INFO):
    """ロギング設定を初期化"""
    # ログディレクトリ作成
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # ロガー設定
    logger = logging.getLogger("pc_system_tool")
    logger.setLevel(log_level)
    
    # ファイルハンドラ（ローテーション付き）
    file_handler = logging.handlers.RotatingFileHandler(
        log_dir / "app.log",
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)
    
    # コンソールハンドラ
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    
    # フォーマット
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger
```

**適用箇所:**
- 全モジュールの冒頭に追加
- エラーハンドリング箇所でログ出力
- 重要な処理の開始/終了をログ記録

#### 1.2 .gitignore の整備
**目的**: 不要なファイルをリポジトリから除外

```gitignore
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
venv/
ENV/
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# IDE
.vscode/
.idea/
*.swp
*.swo
*~
.DS_Store

# ログファイル
logs/
*.log

# 一時ファイル
tmp/
temp/
*.tmp

# テストカバレッジ
.coverage
htmlcov/
.pytest_cache/

# アプリケーション固有
app_config.json
result*.xlsx
result*.csv
```

#### 1.3 requirements.txt の整備
**目的**: 依存関係を明確化

```txt
# 本番環境
pandas>=1.3.0,<3.0.0
openpyxl>=3.0.0,<4.0.0
PySide6>=6.5.0,<7.0.0

# 開発環境（requirements-dev.txt として分離）
pytest>=7.0.0
pytest-cov>=4.0.0
black>=23.0.0
flake8>=6.0.0
mypy>=1.0.0
```

### 🟡 Phase 2: 品質向上（1-2週間）

#### 2.1 ユニットテストの追加

**ディレクトリ構造:**
```
PC-System-Tool/
├── tests/
│   ├── __init__.py
│   ├── test_config_loader.py
│   ├── test_race_parser.py
│   ├── test_calculation_engine.py
│   ├── test_output_formatter.py
│   ├── fixtures/
│   │   ├── sample_entries.csv
│   │   ├── sample_point.csv
│   │   ├── sample_section.csv
│   │   └── sample_race.csv
│   └── conftest.py
```

**サンプルテスト (test_calculation_engine.py):**
```python
import pytest
from calculation_engine import CalculationEngine, Result
from config_loader import ConfigLoader
from race_parser import RaceParser

class TestCalculationEngine:
    """計算エンジンのテスト"""
    
    @pytest.fixture
    def setup_engine(self, tmp_path):
        """テスト用のエンジンをセットアップ"""
        # テストデータの準備
        config = ConfigLoader()
        race = RaceParser()
        engine = CalculationEngine(config, race)
        return engine
    
    def test_pc_calculation(self, setup_engine):
        """PC区間の計算が正しいか"""
        engine = setup_engine
        # テストロジック
        assert True  # 実際のテストを実装
    
    def test_co_clear_condition(self, setup_engine):
        """CO区間のクリア判定が正しいか"""
        engine = setup_engine
        # 0-59.99秒でクリア
        # それ以外は0点
        assert True  # 実際のテストを実装
    
    def test_total_score_calculation(self, setup_engine):
        """総合得点計算が正しいか"""
        engine = setup_engine
        # (PC + PCG) * 係数 * 年齢係数 + CO
        assert True  # 実際のテストを実装
```

**テスト実行:**
```bash
# 全テスト実行
pytest

# カバレッジ付き
pytest --cov=. --cov-report=html

# 特定のテストのみ
pytest tests/test_calculation_engine.py
```

#### 2.2 コード品質チェックの自動化

**setup.cfg の作成:**
```ini
[flake8]
max-line-length = 100
exclude = .git,__pycache__,venv,build,dist
ignore = E203,W503

[mypy]
python_version = 3.7
warn_return_any = True
warn_unused_configs = True
disallow_untyped_defs = False

[tool:pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
```

**実行方法:**
```bash
# コードフォーマット
black .

# リント
flake8 .

# 型チェック
mypy *.py

# 全チェック実行
black . && flake8 . && mypy *.py && pytest
```

#### 2.3 エラーハンドリングの改善

**各モジュールで実装:**
```python
import logging
from typing import Tuple, Optional

logger = logging.getLogger(__name__)

class RaceParserError(Exception):
    """RaceParser固有のエラー"""
    pass

def parse_all(self) -> Tuple[bool, str]:
    """すべてのCSVファイルを解析"""
    try:
        csv_files = glob.glob(os.path.join(self.race_folder, "*.csv"))
        
        if len(csv_files) == 0:
            error_msg = "race フォルダに CSV ファイルが見つかりません"
            logger.warning(error_msg)
            return False, error_msg
        
        logger.info(f"{len(csv_files)}件のCSVファイルを発見")
        
        for csv_file in csv_files:
            logger.debug(f"解析中: {csv_file}")
            success, msg = self._parse_file(csv_file)
            if not success:
                error_msg = f"{os.path.basename(csv_file)}: {msg}"
                logger.error(error_msg)
                return False, error_msg
        
        success_msg = f"{len(csv_files)}件のファイルを解析しました"
        logger.info(success_msg)
        return True, success_msg
        
    except Exception as e:
        error_msg = f"予期しないエラー: {str(e)}"
        logger.exception(error_msg)
        raise RaceParserError(error_msg) from e
```

### 🟢 Phase 3: 機能改善（2-4週間）

#### 3.1 設定ファイルの拡張

**config.yaml の導入:**
```yaml
# config.yaml
application:
  name: "PC System Tool"
  version: "1.0.0"

paths:
  race_folder: "sample/race"
  settings_folder: "sample/setting"
  output_folder: "output"
  log_folder: "logs"

scoring:
  co_point: 500
  default_coefficient: 1.0
  default_age_coefficient: 1.0

ui:
  theme: "light"  # light or dark
  language: "ja"  # ja or en
  table_font_size: 10
  
performance:
  max_file_size_mb: 100
  chunk_size: 10000

export:
  excel_engine: "openpyxl"
  csv_encoding: "utf-8-sig"
  include_timestamp: true
```

**読み込み処理:**
```python
import yaml
from pathlib import Path

class AppConfigYAML:
    def __init__(self, config_file="config.yaml"):
        self.config_file = Path(config_file)
        self.config = self._load_config()
    
    def _load_config(self):
        if not self.config_file.exists():
            return self._default_config()
        
        with open(self.config_file, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    
    def _default_config(self):
        # デフォルト設定を返す
        pass
```

#### 3.2 パフォーマンス最適化

**大量データ対応:**
```python
def parse_all_optimized(self) -> Tuple[bool, str]:
    """最適化版：大量ファイル対応"""
    csv_files = glob.glob(os.path.join(self.race_folder, "*.csv"))
    
    # 並列処理（ProcessPoolExecutor）
    from concurrent.futures import ProcessPoolExecutor, as_completed
    
    with ProcessPoolExecutor(max_workers=4) as executor:
        futures = {
            executor.submit(self._parse_file, file): file 
            for file in csv_files
        }
        
        for future in as_completed(futures):
            file = futures[future]
            try:
                success, msg = future.result()
                if not success:
                    return False, f"{file}: {msg}"
            except Exception as e:
                return False, f"{file}: エラー - {str(e)}"
    
    return True, f"{len(csv_files)}件のファイルを解析しました"
```

#### 3.3 GUI改善

**非同期処理の導入:**
```python
from PySide6.QtCore import QThread, Signal

class DataLoadWorker(QThread):
    """データ読み込み用ワーカースレッド"""
    progress = Signal(int)  # 進捗状況
    finished = Signal(bool, str)  # 完了シグナル
    
    def __init__(self, race_parser):
        super().__init__()
        self.race_parser = race_parser
    
    def run(self):
        """バックグラウンドで実行"""
        try:
            success, msg = self.race_parser.parse_all()
            self.finished.emit(success, msg)
        except Exception as e:
            self.finished.emit(False, str(e))

# 使用例
def load_race_data(self):
    """レースデータを非同期で読み込み"""
    self.worker = DataLoadWorker(self.race_parser)
    self.worker.finished.connect(self._on_load_finished)
    self.worker.progress.connect(self._on_progress)
    self.worker.start()
    
    # ローディング表示
    self.statusBar().showMessage("データ読み込み中...")

def _on_load_finished(self, success, message):
    """読み込み完了時の処理"""
    if success:
        QMessageBox.information(self, "成功", message)
    else:
        QMessageBox.warning(self, "エラー", message)
    
    self.statusBar().clearMessage()
```

### 🔵 Phase 4: CI/CD構築（オプション）

#### 4.1 GitHub Actions ワークフロー

**.github/workflows/test.yml:**
```yaml
name: Test and Lint

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main, develop ]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: [3.7, 3.8, 3.9, '3.10', '3.11']
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python ${{ matrix.python-version }}
      uses: actions/setup-python@v4
      with:
        python-version: ${{ matrix.python-version }}
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install pytest pytest-cov black flake8
    
    - name: Lint with flake8
      run: |
        flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
        flake8 . --count --exit-zero --max-complexity=10 --max-line-length=100 --statistics
    
    - name: Check formatting with black
      run: |
        black --check .
    
    - name: Test with pytest
      run: |
        pytest --cov=. --cov-report=xml
    
    - name: Upload coverage to Codecov
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml
```

## 📊 実施スケジュール

### Week 1-2: Phase 1 & 2
- [x] ロギング機能追加
- [x] .gitignore 整備
- [ ] ユニットテスト作成
- [ ] コード品質チェック導入

### Week 3-4: Phase 3
- [ ] 設定ファイル拡張
- [ ] パフォーマンス最適化
- [ ] GUI改善
- [ ] ドキュメント更新

### Week 5-6: Phase 4 (オプション)
- [ ] CI/CD構築
- [ ] リリースプロセス整備
- [ ] パフォーマンステスト

## 🎓 開発者向けガイド

### 開発環境のセットアップ

```bash
# リポジトリのクローン
git clone https://github.com/hal75-user/PC-System-Tool.git
cd PC-System-Tool

# 仮想環境の作成
python -m venv venv

# Windows
venv\Scripts\activate

# Mac/Linux
source venv/bin/activate

# 依存パッケージのインストール
pip install -r requirements.txt
pip install -r requirements-dev.txt

# プリコミットフックの設定（オプション）
pre-commit install
```

### コーディング規約

1. **コードスタイル**: PEP 8 に準拠
2. **フォーマッタ**: Black を使用
3. **型ヒント**: 全ての関数に型ヒントを追加
4. **docstring**: Google スタイルで記述
5. **命名規則**:
   - クラス: PascalCase
   - 関数/変数: snake_case
   - 定数: UPPER_CASE

### コミットメッセージ規約

```
<type>: <subject>

<body>

<footer>
```

**Type:**
- `feat`: 新機能
- `fix`: バグ修正
- `docs`: ドキュメント
- `style`: フォーマット
- `refactor`: リファクタリング
- `test`: テスト
- `chore`: その他

**例:**
```
feat: ロギング機能を追加

- logging モジュールの導入
- ファイルローテーション対応
- 各モジュールにロガーを追加

Closes #123
```

## 📞 サポート

質問や問題がある場合:
1. GitHub Issues で報告
2. ドキュメントを確認
3. ログファイルを確認

---

**最終更新**: 2026年2月17日
