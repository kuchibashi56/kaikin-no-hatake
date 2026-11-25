# 解禁の畑（名前は仮）

スマホ向けの放置・クラフト系ブラウザゲーム。単一 HTML ファイル構成で、PWA としてホーム画面に追加でき、オフラインでも動作する。

**公開URL: https://kuchibashi56.github.io/kaikin-no-hatake/**

## ファイル構成

| ファイル | 役割 |
|---|---|
| `index.html` | ゲーム本体。HTML / CSS / JS とデータ層（ITEMS / NODES / RECIPES / CROPS）をすべて含む |
| `manifest.json` | PWA の定義（名前・アイコン・standalone 表示・テーマ色 `#14110e`） |
| `sw.js` | Service Worker。オフライン動作のためのキャッシュ制御 |
| `icon-512.png` / `icon-192.png` | ホーム画面用アイコン（背景 `#14110e` に麦の穂 `#c9a227`） |

セーブデータは `localStorage` に保存される。オリジンごとに独立しているため、ローカルで遊んだデータと公開版のデータは共有されない。

## ゲームを更新する手順

`sw.js` のキャッシュは **cache-first**（キャッシュにあればネットワークを見ない）なので、
**キャッシュ版番号を上げないと、push しても端末側に新しい版が永久に届かない。**

### 1. `index.html` を編集する

### 2. `sw.js` の版番号を上げる

```js
const CACHE = 'kaikin-v1';   // ← 'kaikin-v2' に変更する
```

### 3. コミットして push

```bash
git add -A && git commit -m "ゲーム更新 + cache v2" && git push
```

### 4. 端末側で反映される流れ

1. Chrome が `sw.js` を再取得する（Service Worker のスクリプトは HTTP キャッシュを迂回するため、`Cache-Control: max-age=600` の影響を受けない）
2. 中身が1バイトでも変われば「新しい Service Worker」と判定され、`install` で `kaikin-v2` に新しいファイル一式が入る
3. `skipWaiting()` により即座に有効化され、`activate` で古い `kaikin-v1` が削除される
4. `clients.claim()` で、開いているページも新しい Service Worker の管理下に入る

体感としては、**アプリを一度閉じて開き直すと新しい版が表示される**。初回起動時はまだ古い画面が出ることがあるため、「閉じて開き直す」を1回挟むのが確実。

> **push しても画面が変わらないときは、まず版番号の上げ忘れを疑う。**
> エラーが出ないので気付きにくい。PWA で最もハマりやすい箇所。

## ローカルでの動作確認

Service Worker は `https` か `localhost` でしか動作しないため、ファイルを直接開く（`file://`）のではなくローカルサーバーを立てる。

```bash
python -m http.server 8000
```

`http://127.0.0.1:8000/` を開く。Service Worker の状態は DevTools（F12）の Application タブ → Service Workers で確認できる。

## Android Chrome でホーム画面に追加する

1. Chrome で公開URLを開く
2. 右上の **⋮** → **ホーム画面に追加**
3. 名前が「解禁の畑」になっていることを確認して **追加**

アイコンから起動するとアドレスバーなしの全画面（standalone）になり、機内モードでも動作する。

## 公開設定

GitHub Pages を `main` ブランチのルート（`/`）から配信している。設定は Settings → Pages から確認できる。
