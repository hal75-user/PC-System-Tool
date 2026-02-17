# 権限設定ガイド

このドキュメントでは、PC-System-Tool の開発に必要な各種権限の設定方法を説明します。

## 📁 ファイルシステムの権限設定

### Windows の場合

#### 方法1: エクスプローラーから設定

1. フォルダを右クリック → **プロパティ**
2. **セキュリティ** タブを選択
3. **編集** ボタンをクリック
4. ユーザーを選択 → **フルコントロール** にチェック
5. **適用** → **OK**

#### 方法2: コマンドプロンプト（管理者権限）

```cmd
# 特定のフォルダに読み取り/書き込み権限を付与
icacls "C:\path\to\PC-System-Tool" /grant Users:F /T

# 現在のユーザーに権限を付与
icacls "C:\path\to\PC-System-Tool" /grant %USERNAME%:F /T
```

**オプション説明:**
- `/grant`: 権限を付与
- `F`: フルコントロール
- `/T`: サブフォルダにも適用

#### 方法3: PowerShell（推奨）

```powershell
# 管理者権限で PowerShell を起動
$path = "C:\path\to\PC-System-Tool"
$acl = Get-Acl $path

# 現在のユーザーにフルコントロール権限を付与
$permission = $env:USERNAME,"FullControl","ContainerInherit,ObjectInherit","None","Allow"
$accessRule = New-Object System.Security.AccessControl.FileSystemAccessRule $permission
$acl.SetAccessRule($accessRule)
Set-Acl $path $acl

Write-Host "権限設定が完了しました: $path"
```

### Mac/Linux の場合

#### 基本的な権限設定

```bash
# フォルダとファイルに読み取り/書き込み/実行権限を付与
chmod -R 755 /path/to/PC-System-Tool

# 特定のファイルに実行権限を付与
chmod +x /path/to/PC-System-Tool/main_pyside6.py
```

**権限の数値表記:**
- `7` = 読み取り(4) + 書き込み(2) + 実行(1)
- `5` = 読み取り(4) + 実行(1)
- `755` = オーナー(7), グループ(5), その他(5)

#### 所有者の変更（必要な場合）

```bash
# 所有者を現在のユーザーに変更
sudo chown -R $USER:$USER /path/to/PC-System-Tool
```

## 🐍 Python環境の権限設定

### 仮想環境の作成（推奨）

仮想環境を使用することで、システムPythonに影響を与えずに作業できます。

#### Windows

```cmd
# 仮想環境の作成
python -m venv venv

# 仮想環境の有効化
venv\Scripts\activate

# 確認
python --version
pip --version
```

#### Mac/Linux

```bash
# 仮想環境の作成
python3 -m venv venv

# 仮想環境の有効化
source venv/bin/activate

# 確認
python --version
pip --version
```

### パッケージインストール権限

#### ユーザーレベルインストール（権限不要）

```bash
# --user オプションでユーザーディレクトリにインストール
pip install --user pandas openpyxl PySide6
```

#### システムレベルインストール（管理者権限必要）

**Windows (管理者権限):**
```cmd
# コマンドプロンプトを管理者として実行
pip install pandas openpyxl PySide6
```

**Mac/Linux:**
```bash
# sudo を使用
sudo pip install pandas openpyxl PySide6

# または pip3
sudo pip3 install pandas openpyxl PySide6
```

**⚠️ 注意**: システムレベルインストールは推奨されません。仮想環境を使用してください。

## 🔐 GitHub リポジトリの権限設定

### 1. 個人リポジトリの設定

#### リポジトリへのアクセス権限を付与

1. GitHub リポジトリページを開く
2. **Settings** タブをクリック
3. 左サイドバーから **Collaborators** を選択
4. **Add people** ボタンをクリック
5. ユーザー名またはメールアドレスを入力
6. 権限レベルを選択:
   - **Read**: 閲覧のみ
   - **Triage**: Issue管理
   - **Write**: コードの変更・プッシュ可能
   - **Maintain**: リポジトリ管理
   - **Admin**: 全ての権限

7. **Add [username] to this repository** をクリック

### 2. ブランチ保護ルールの設定

#### mainブランチの保護

1. **Settings** → **Branches**
2. **Add branch protection rule** をクリック
3. **Branch name pattern** に `main` を入力
4. 推奨設定:
   ```
   ✅ Require a pull request before merging
     ✅ Require approvals (1以上)
   ✅ Require status checks to pass before merging
   ✅ Require conversation resolution before merging
   ✅ Include administrators
   ```
5. **Create** をクリック

### 3. GitHub Actions の権限設定

#### ワークフローの権限設定

1. **Settings** → **Actions** → **General**
2. **Workflow permissions** セクション:
   ```
   ○ Read repository contents and packages permissions
   ● Read and write permissions  # 推奨
   
   ✅ Allow GitHub Actions to create and approve pull requests
   ```
3. **Save** をクリック

### 4. Personal Access Token (PAT) の作成

コマンドラインから GitHub にアクセスする場合に必要です。

1. GitHub の **Settings** → **Developer settings**
2. **Personal access tokens** → **Tokens (classic)**
3. **Generate new token** → **Generate new token (classic)**
4. トークンの設定:
   - **Note**: `PC-System-Tool Development`
   - **Expiration**: 90 days（または希望の期間）
   - **Select scopes**:
     ```
     ✅ repo (全て)
     ✅ workflow
     ✅ write:packages
     ✅ read:packages
     ```
5. **Generate token** をクリック
6. **トークンをコピーして安全な場所に保存**（二度と表示されません）

#### トークンの使用方法

```bash
# Git の認証情報として設定（Windows）
git config --global credential.helper wincred

# Git の認証情報として設定（Mac）
git config --global credential.helper osxkeychain

# Git の認証情報として設定（Linux）
git config --global credential.helper cache

# リモートリポジトリのURLにトークンを含める
git clone https://<TOKEN>@github.com/hal75-user/PC-System-Tool.git

# または、プッシュ時にユーザー名とパスワード（トークン）を入力
# ユーザー名: あなたのGitHubユーザー名
# パスワード: 作成したPersonal Access Token
```

## 🛠️ 開発ツールの権限設定

### Visual Studio Code

#### ワークスペースの信頼設定

1. VSCode でフォルダを開く
2. 「このフォルダーを信頼しますか？」というダイアログが表示される
3. **はい、作成者を信頼します** を選択

#### 拡張機能の権限

1. **ファイル** → **ユーザー設定** → **設定**
2. 検索: `python.linting`
3. 以下を有効化:
   ```
   ✅ Python › Linting: Enabled
   ✅ Python › Linting: Flake8 Enabled
   ```

### PyCharm

#### プロジェクトインタープリターの設定

1. **File** → **Settings** → **Project** → **Python Interpreter**
2. 歯車アイコン → **Add**
3. **Virtualenv Environment** を選択
4. **Location** に `venv` フォルダを指定
5. **OK** をクリック

## 🔒 セキュリティのベストプラクティス

### 1. 機密情報の管理

**絶対にコミットしてはいけないもの:**
- パスワード
- APIキー
- データベース接続文字列
- Personal Access Token

**対策:**

**.gitignore に追加:**
```gitignore
# 機密情報
.env
secrets.json
*.key
*.pem
config_local.py
```

**環境変数の使用:**
```python
import os
from dotenv import load_dotenv

load_dotenv()  # .env ファイルから読み込み

API_KEY = os.getenv('API_KEY')
DB_PASSWORD = os.getenv('DB_PASSWORD')
```

**.env ファイルの例:**
```env
# .env (このファイルは .gitignore に含める)
API_KEY=your_api_key_here
DB_PASSWORD=your_password_here
```

### 2. ファイルアクセス権限のベストプラクティス

**最小権限の原則:**
- 必要最小限の権限のみを付与
- 実行ファイル以外には実行権限を付与しない
- 機密ファイルには適切なアクセス制限を設定

**推奨設定（Unix/Linux）:**
```bash
# ディレクトリ
chmod 755 /path/to/PC-System-Tool

# Pythonスクリプト（実行不要）
chmod 644 *.py

# 設定ファイル（読み取りのみ）
chmod 400 config/secrets.json

# ログファイル（書き込み可能）
chmod 664 logs/*.log
```

## 📝 トラブルシューティング

### 問題: "Permission denied" エラー

**原因:**
- ファイルやフォルダへのアクセス権限が不足

**解決方法:**

**Windows:**
```cmd
# 管理者権限でコマンドプロンプトを実行
icacls "C:\path\to\file" /grant %USERNAME%:F
```

**Mac/Linux:**
```bash
# 所有者を変更
sudo chown $USER:$USER /path/to/file

# 権限を付与
chmod 644 /path/to/file
```

### 問題: Git push が失敗する

**原因:**
- 認証情報が設定されていない
- Personal Access Token が無効

**解決方法:**

1. Personal Access Token を再生成
2. 認証情報を更新:

```bash
# 認証情報をクリア（Windows）
git credential-manager uninstall

# 認証情報をクリア（Mac）
git credential-osxkeychain erase
host=github.com
protocol=https

# 認証情報をクリア（Linux）
git config --global --unset credential.helper
```

3. 再度プッシュを試行（新しいトークンを入力）

### 問題: Python パッケージのインストールが失敗する

**原因:**
- 権限不足
- 仮想環境が有効化されていない

**解決方法:**

```bash
# 仮想環境が有効化されているか確認
which python  # Unix/Linux
where python  # Windows

# 仮想環境を有効化
source venv/bin/activate  # Unix/Linux
venv\Scripts\activate     # Windows

# 再度インストール
pip install -r requirements.txt
```

## 🎓 参考リンク

- [GitHub Docs - Managing access to your repositories](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/managing-repository-settings/managing-teams-and-people-with-access-to-your-repository)
- [Python Virtual Environments](https://docs.python.org/3/tutorial/venv.html)
- [Git Credential Storage](https://git-scm.com/book/en/v2/Git-Tools-Credential-Storage)

---

**最終更新**: 2026年2月17日
