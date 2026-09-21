# HACS Custom Refresh

[![GitHub Release](https://img.shields.io/github/v/release/AureaAurum/hacs-custom-refresh)](https://github.com/AureaAurum/hacs-custom-refresh/releases)
[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/default)

Home Assistant の HACS において、ダウンロード済みカスタムリポジトリ（Custom Repository）の更新情報を手動または自動で即座に再取得（refresh）するための Custom Integration です。

---

## 背景と目的

HACS 2.0.5 の内部実装では、ダウンロード済みカスタムリポジトリの更新確認タスク (`async_update_downloaded_custom_repositories`) は約48時間周期（`timedelta(hours=48)`）でスケジュールされています。

バックアップ等の目的で Home Assistant を約24時間ごとに定期再起動している環境では、次回実行までのタイマーが再起動のたびにリセットされるため、カスタムリポジトリの更新情報（GitHub release / update）が長期間検知されない問題が発生します。

本インテグレーションは、HACS 内部の更新再取得処理およびキュー処理を Home Assistant の action / service (`hacs_custom_refresh.refresh`) として公開し、以下のことを可能にします。

* 開発者ツール（Developer Tools）やダッシュボードのボタンから手動で即座にカスタムリポジトリの更新を再取得する。
* Home Assistant の起動時オートメーション等から自動実行し、定期再起動環境でもカスタムリポジトリの更新通知を確実に受信する。

※ repository discovery、GitHub API 処理、version 比較はすべて HACS 本体の既存ロジックを利用します。

---

## 機能

### Action / Service: `hacs_custom_refresh.refresh`

HACS のダウンロード済みカスタムリポジトリのメタデータおよび GitHub Release 情報を再取得し、HACS のキューを即時実行して利用可能なアップデート（Update Entity）を検知可能な状態にします。

#### 実行フロー
1. HACS インスタンス（`hass.data["hacs"]`）を取得
2. HACS が稼働中かつ startup 完了状態であることを確認
3. HACS 内部の `async_update_downloaded_custom_repositories()` を呼び出し、各カスタムリポジトリの更新タスクをキューに登録
4. `async_process_queue()` を即時呼び出し、キュー内のタスクを実行
5. 全リポジトリの更新完了後、Update Coordinator が発火して Home Assistant 上の update エンティティに最新バージョンが反映される

---

## インストール方法

### HACS 経由でのインストール（推奨）

1. Home Assistant のサイドバーから **HACS** を開きます。
2. 右上のメニュー（3点リーダー）から **Custom repositories** を選択します。
3. リポジトリの追加:
   * **Repository**: `https://github.com/AureaAurum/hacs-custom-refresh`
   * **Type / Category**: `Integration`
4. **Add** をクリックします。
5. リストに追加された **HACS Custom Refresh** を開き、**Download** をクリックします。
6. Home Assistant を再起動します。

### 手動インストール

1. 本リポジトリの `custom_components/hacs_custom_refresh` フォルダを、Home Assistant の `config/custom_components/` ディレクトリ配下にコピーします。
2. Home Assistant を再起動します。

---

## 設定方法

本インテグレーションは YAML 設定不要です（Single Instance）。

1. Home Assistant の **Settings（設定）** -> **Devices & services（デバイスとサービス）** を開きます。
2. 右下の **Add Integration（統合を追加）** をクリックします。
3. **HACS Custom Refresh** を検索して選択します。
4. 確認ダイアログが表示されるので、そのまま送信（Submit）をクリックして完了します。

---

## 使い方

### 開発者ツールから手動実行

1. **Developer Tools（開発者ツール）** -> **Actions（アクション）** を開きます。
2. アクションに `hacs_custom_refresh.refresh` を選択します。
3. **Perform Action（アクションを実行）** をクリックします。

### オートメーションによる自動実行例

Home Assistant 起動完了から数分後に自動でカスタムリポジトリの更新を確認する例:

```yaml
alias: "Refresh HACS Custom Repositories on Startup"
trigger:
  - platform: homeassistant
    event: start
action:
  - delay: "00:03:00"
  - action: hacs_custom_refresh.refresh
mode: single
```

---

## HACS 内部 API への依存性について

本インテグレーションは、HACS 内部の以下の private API を呼び出すことで実現しています。

* `hass.data["hacs"]` (`HacsBase`)
* `hacs.async_update_downloaded_custom_repositories()`
* `hacs.async_process_queue()`
* `hacs.stage` / `hacs.status.startup` / `hacs.system.disabled`

> [!WARNING]
> 本インテグレーションは **HACS 2.0.5** を対象に検証・設計されています。
> HACS の将来のメジャーアップデート等により内部メソッドのシグネチャや構造が変更された場合、エラーとなる可能性があります。
> 本インテグレーションでは内部 API の存在チェック (`hasattr`) を備えており、互換性がない場合は Home Assistant 上に安全なエラーメッセージを返します。

---

## ライセンス

MIT License
