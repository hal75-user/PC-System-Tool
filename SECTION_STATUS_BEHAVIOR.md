# 区間ステータスの挙動詳細

## 📋 概要

区間ステータス（RIT/N.C./BLNK）の正しい挙動を整理し、実装しました。

---

## 🎯 区間ステータスの種類と挙動

### 1. RIT (Retire) - リタイヤ

**意味:** その区間で競技を中止した

**表示挙動:**

| 項目 | 表示内容 |
|------|---------|
| START時刻 | RIT |
| GOAL時刻 | RIT |
| 走行時間 | RIT |
| 差分 | RIT |
| 順位 | RIT |
| 得点 | 0 |

**特徴:**
- ✅ 順位付けから除外
- ✅ タイム表示なし
- ✅ 差分算出なし
- ✅ 得点は0

**使用例:**
```
シナリオ: ゼッケン5がPC2でリタイヤ

表示:
PC2_START: RIT
PC2_GOAL: RIT
PC2_走行時間: RIT
PC2_差分: RIT
PC2_順位: RIT
PC2_得点: 0

結果:
- PC2の得点は0
- 総合得点はPC1 + PC3 + ... + CO
```

---

### 2. N.C. (No Classification) - ノンクラシフィケーション

**意味:** 時間超過や規則違反などで順位付けから除外されるが、走行は記録される

**表示挙動:**

| 項目 | 表示内容 |
|------|---------|
| START時刻 | **実際の時刻** |
| GOAL時刻 | **実際の時刻** |
| 走行時間 | **実際の時間** |
| 差分 | **計算された差分（色付き）** |
| 順位 | N.C. |
| 得点 | **計算された得点** |

**特徴:**
- ✅ 順位付けから除外
- ✅ **タイム表示あり**
- ✅ **差分算出あり**
- ✅ 得点は計算される

**使用例:**
```
シナリオ: ゼッケン10がPC3で時間超過によりN.C.

表示:
PC3_START: 09:15:30
PC3_GOAL: 10:45:20
PC3_走行時間: 01:29:50
PC3_差分: +05:30 （赤字で表示）
PC3_順位: N.C.
PC3_得点: 0

結果:
- タイムは記録される
- 差分も計算される
- 順位付けからは除外
- 得点は0（ペナルティ的な扱い）
```

**N.C.の重要な特徴:**
1. **記録は残る**: START/GOALの時刻が記録される
2. **差分が計算される**: 他の完走者との比較ができる
3. **順位はつかない**: 順位欄には "N.C." と表示
4. **得点は0**: 順位付けから除外されるため

---

### 3. BLNK (Blank) - ブランク

**意味:** データなし、未走行、または記録対象外

**表示挙動:**

| 項目 | 表示内容 |
|------|---------|
| START時刻 | BLNK |
| GOAL時刻 | BLNK |
| 走行時間 | BLNK |
| 差分 | BLNK |
| 順位 | BLNK |
| 得点 | 0 |

**特徴:**
- ✅ 順位付けから除外
- ✅ タイム表示なし
- ✅ 差分算出なし
- ✅ 得点は0

**使用例:**
```
シナリオ: ゼッケン15がPC1をスキップ（未走行）

表示:
PC1_START: BLNK
PC1_GOAL: BLNK
PC1_走行時間: BLNK
PC1_差分: BLNK
PC1_順位: BLNK
PC1_得点: 0

結果:
- PC1の記録なし
- 総合得点はPC2 + PC3 + ... + CO
```

---

## 📊 ステータス比較表

| 項目 | RIT | N.C. | BLNK |
|------|-----|------|------|
| **START時刻** | RIT | ✅ 表示 | BLNK |
| **GOAL時刻** | RIT | ✅ 表示 | BLNK |
| **走行時間** | RIT | ✅ 表示 | BLNK |
| **差分** | RIT | ✅ 計算 | BLNK |
| **順位** | RIT | N.C. | BLNK |
| **得点** | 0 | 0 | 0 |
| **順位付け** | 除外 | 除外 | 除外 |
| **タイム記録** | なし | **あり** | なし |

---

## 💡 使用シナリオ

### シナリオ1: マシントラブルでリタイヤ

```
状況: ゼッケン5がPC2でエンジントラブル

設定: PC2に "RIT" を設定

表示:
- PC2のすべての列に "RIT"
- タイム表示なし
- PC2の得点: 0

総合結果:
- 総合得点: PC1 + PC3 + ... + CO
- 総合順位: 通常通り順位付け（得点は減る）
```

### シナリオ2: 時間超過でペナルティ

```
状況: ゼッケン10がPC3で制限時間を5分超過

設定: PC3に "N.C." を設定

表示:
- PC3_START: 09:15:30
- PC3_GOAL: 10:45:20
- PC3_走行時間: 01:29:50
- PC3_差分: +05:30（赤字）
- PC3_順位: N.C.
- PC3_得点: 0

総合結果:
- タイムは記録に残る
- 差分も確認できる
- PC3の得点: 0
- 総合得点: PC1 + PC2 + PC4 + ... + CO
```

### シナリオ3: 区間未走行

```
状況: ゼッケン15がPC1をスキップ

設定: PC1に "BLNK" を設定

表示:
- PC1のすべての列に "BLNK"
- タイム表示なし
- PC1の得点: 0

総合結果:
- 総合得点: PC2 + PC3 + ... + CO
- 総合順位: 通常通り順位付け（得点は減る）
```

---

## 🎨 UI表示例

### RIT の表示

```
┌──────┬──────┬──────────┬──────┬────┬────┐
│ START│ GOAL │ 走行時間 │ 差分 │順位│得点│
├──────┼──────┼──────────┼──────┼────┼────┤
│ RIT  │ RIT  │   RIT    │ RIT  │RIT │ 0  │
└──────┴──────┴──────────┴──────┴────┴────┘
```

### N.C. の表示

```
┌──────────┬──────────┬──────────┬──────────┬────┬────┐
│  START   │   GOAL   │ 走行時間 │   差分   │順位│得点│
├──────────┼──────────┼──────────┼──────────┼────┼────┤
│ 09:15:30 │ 10:45:20 │ 01:29:50 │ +05:30   │N.C.│ 0  │
│          │          │          │  (赤字)  │    │    │
└──────────┴──────────┴──────────┴──────────┴────┴────┘
```

### BLNK の表示

```
┌──────┬──────┬──────────┬──────┬────┬────┐
│ START│ GOAL │ 走行時間 │ 差分 │順位│得点│
├──────┼──────┼──────────┼──────┼────┼────┤
│ BLNK │ BLNK │   BLNK   │ BLNK │BLNK│ 0  │
└──────┴──────┴──────────┴──────┴────┴────┘
```

---

## 🔧 実装詳細

### main_pyside6.py - ResultTableWidget

**N.C.の特別処理:**
```python
if result.status:
    if result.status == "N.C.":
        # N.C.の場合: タイム表示あり、差分算出、順位は除外
        # START時刻を表示
        start_time = self._get_time_str(zekken, section, "START")
        self._set_item(row_idx, col_idx, start_time)
        col_idx += 1
        
        # GOAL時刻を表示
        goal_time = self._get_time_str(zekken, section, "GOAL")
        self._set_item(row_idx, col_idx, goal_time)
        col_idx += 1
        
        # 走行時間を表示
        passage_str = self.calc_engine.format_time(result.passage_time)
        self._set_item(row_idx, col_idx, passage_str)
        col_idx += 1
        
        # 差分を計算して表示（色付き）
        diff_str = self._format_diff_simple(result.diff)
        item = self._set_item(row_idx, col_idx, diff_str)
        self._color_diff_cell(item, result.diff)
        col_idx += 1
        
        # 順位: N.C.を表示
        self._set_item(row_idx, col_idx, result.status)
        col_idx += 1
        
        # 得点を表示
        self._set_item(row_idx, col_idx, str(result.point))
        col_idx += 1
    else:
        # RIT, BLNKの場合: タイム表示無し
        for _ in range(6):
            self._set_item(row_idx, col_idx, result.status)
            col_idx += 1
```

### output_formatter.py - create_dataframe

**N.C.の特別処理:**
```python
if result.status:
    if result.status == "N.C.":
        # N.C.の場合: タイム表示あり、差分算出、順位は除外
        row_data[f'{section}_通過時間'] = self.calc.format_time(result.passage_time)
        row_data[f'{section}_差分'] = self.calc.format_diff(result.diff)
        row_data[f'{section}_順位'] = result.status
        row_data[f'{section}_得点'] = result.point
    else:
        # RIT, BLNKの場合: タイム表示無し
        row_data[f'{section}_通過時間'] = result.status
        row_data[f'{section}_差分'] = result.status
        row_data[f'{section}_順位'] = result.status
        row_data[f'{section}_得点'] = 0
```

---

## ✅ テストシナリオ

### テスト1: RIT表示の確認

```
手順:
1. ステータス設定画面でPC2に "RIT" を設定
2. 結果表示画面を確認

期待結果:
- PC2のすべての列に "RIT" と表示
- START, GOAL, 走行時間, 差分, 順位すべて "RIT"
- 得点は 0
```

### テスト2: N.C.表示の確認

```
手順:
1. ステータス設定画面でPC3に "N.C." を設定
2. 結果表示画面を確認

期待結果:
- PC3_START: 実際の時刻
- PC3_GOAL: 実際の時刻
- PC3_走行時間: 計算された時間
- PC3_差分: 計算された差分（色付き）
- PC3_順位: "N.C."
- PC3_得点: 0
```

### テスト3: BLNK表示の確認

```
手順:
1. ステータス設定画面でPC1に "BLNK" を設定
2. 結果表示画面を確認

期待結果:
- PC1のすべての列に "BLNK" と表示
- START, GOAL, 走行時間, 差分, 順位すべて "BLNK"
- 得点は 0
```

### テスト4: Excel/CSV出力の確認

```
手順:
1. RIT, N.C., BLNKを設定
2. Excel/CSVに出力
3. ファイルを開いて確認

期待結果:
- RIT: すべてRIT
- N.C.: タイムと差分が表示、順位はN.C.
- BLNK: すべてBLNK
```

---

## 📝 まとめ

### 重要なポイント

1. **RIT**: 完全にリタイヤ、タイム記録なし
2. **N.C.**: タイムは記録、順位付けから除外
3. **BLNK**: データなし、未走行

### N.C.の特殊性

**N.C.だけが特別:**
- タイムが記録される唯一のステータス
- 差分が計算される唯一のステータス
- 「走行はしたが、順位はつかない」という状態

### 使い分け

- **マシントラブル、事故等**: RIT
- **時間超過、規則違反等**: N.C.
- **未走行、データなし**: BLNK

---

**更新日**: 2026年2月17日  
**バージョン**: v5.0  
**実装完了**: ✅
