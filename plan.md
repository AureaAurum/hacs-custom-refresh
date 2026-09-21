Home Assistant 用の HACS Custom Integration を新規作成してください。

目的は、HACS が内部で持っている「ダウンロード済み Custom Repository の更新情報を再取得する処理」を、Home Assistant の action/service から手動実行できるようにすることです。

背景:

* HACS 2.0.5 を使用しています。
* 通常/default repository の更新通知は正常です。
* Custom Repository の更新だけ長期間検知されない事象があります。
* Home Assistant はバックアップのため約24時間ごとに再起動しています。
* HACS のコード上、downloaded custom repositories の更新処理は約48時間周期で scheduling されているように見えます。
* HACS UI の `Update information` を手動実行すると、未検知だった更新が即座に検知されます。
* この integration は、原因確認用のテストハーネス兼暫定 workaround として使います。

## リポジトリ

```text
Repository: hacs-custom-refresh
Domain: hacs_custom_refresh
Display name: HACS Custom Refresh
```

HACS Custom Integration としてインストール可能な標準構造にしてください。

```text
hacs-custom-refresh/
├── README.md
├── hacs.json
└── custom_components/
    └── hacs_custom_refresh/
        ├── __init__.py
        ├── config_flow.py
        ├── const.py
        ├── manifest.json
        ├── services.yaml
        ├── strings.json
        └── translations/
            ├── en.json
            └── ja.json
```

## 機能

Home Assistant に次の action/service を登録してください。

```text
hacs_custom_refresh.refresh
```

この action は、HACS の Custom Repository の repository metadata / release information を再取得し、利用可能な update を検知可能な状態にします。

HACS の repository discovery、GitHub API 処理、version comparison は HACS 本体の既存実装を利用してください。

現行 HACS 2.0.5 のソースコードを確認し、HACS が48時間周期で使用している downloaded custom repositories refresh 処理をそのまま呼び出してください。

現時点では以下の内部 API を想定しています。

```python
hacs.async_update_downloaded_custom_repositories()
hacs.async_process_queue()
```

実装前に HACS 2.0.5 のコードを確認し、

* HACS instance の正しい取得方法
* `async_update_downloaded_custom_repositories()` の実際の挙動
* repository update がその場で完了するのか、queue に積まれるのか
* `async_process_queue()` の明示実行が必要か
* HACS startup 完了状態を確認する正しい方法
* 同時実行時の挙動

を確認してください。

service 実行時の流れは以下を意図しています。

```text
hacs_custom_refresh.refresh
  ↓
HACS instance 取得
  ↓
HACS が利用可能な状態か確認
  ↓
HACS 既存の downloaded custom repositories refresh 処理を実行
  ↓
必要なら HACS queue を即時処理
  ↓
完了
```

repository の対象選別も HACS 本体の `async_update_downloaded_custom_repositories()` に委ねてください。Custom Repository 一覧や repository URL をこの integration 側で保持しないでください。

## Config Flow

YAML 設定不要にしてください。

`Settings -> Devices & services -> Add integration` から追加できる Config Flow を実装してください。

設定項目はありません。

single instance にしてください。

## エラー処理

action 実行時に以下を検出し、Home Assistant の action 呼び出し側へ意味のあるエラーを返してください。

* HACS が利用できない
* HACS startup が完了していない
* HACS が disabled
* 必要な HACS 内部 API が存在しない

HACS の private/internal API を使用するため、その依存関係を README に明記してください。

## ログ

INFO レベルでは最低限、

```text
HACS custom repository refresh started
HACS custom repository refresh completed
```

を出してください。

repository ごとの詳細は HACS 本体のログに任せてください。

## manifest

初期 version は `0.1.0` としてください。

GitHub owner は `AureaAurum` としてください。

現在の Home Assistant / HACS Custom Integration の要件に従って `manifest.json` を作成してください。

基本情報は以下です。

```json
{
  "domain": "hacs_custom_refresh",
  "name": "HACS Custom Refresh",
  "version": "0.1.0"
}
```

`documentation`、`issue_tracker`、`codeowners` など必要な metadata を追加してください。

## HACS metadata

repository root に `hacs.json` を置き、HACS の Custom Repository で category `Integration` として正常に追加できる状態にしてください。

## README

README には以下を記載してください。

* integration の目的
* HACS の downloaded custom repository refresh 処理を手動実行すること
* `hacs_custom_refresh.refresh` の使い方
* update 情報の再取得を行う integration であること
* HACS 内部 API に依存していること
* インストール方法
* HACS 2.0.5 を対象に初期検証していること

## 検証

この integration 自身を HACS Custom Repository として `v0.1.0` release からインストールします。

その後 GitHub に `v0.1.1` release/tag を作成し、以下を確認できる状態にしてください。

```text
v0.1.0 installed
↓
GitHub release v0.1.1 created
↓
Home Assistant restart
↓
HACS が自動で v0.1.1 を検知するか確認
↓
未検知なら hacs_custom_refresh.refresh を手動実行
↓
v0.1.1 が update として検知されるか確認
```

この検証は GitHub release metadata の refresh を確認する目的なので、`manifest.json` の version 更新には依存しない形で成立するか、HACS 2.0.5 の実装を確認してください。

## 実装後の報告

実装後に以下を報告してください。

1. 作成したファイル一覧
2. 使用した HACS 2.0.5 の内部 API
3. `async_update_downloaded_custom_repositories()` の実際の挙動
4. `async_process_queue()` を呼ぶ必要があったか、その理由
5. private API 依存による破壊可能性
6. HACS への追加手順
7. Home Assistant への integration 追加手順
8. `hacs_custom_refresh.refresh` の実行方法
9. syntax/lint/test の結果

HACS 内部 API の仕様は推測せず、対象コードを確認してから実装してください。
