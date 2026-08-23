# Vision 路 DeepSeek Harness (DSH) 瑙嗚鎻掍欢

缁?DeepSeek Harness 鐨?agent 鎻愪緵**鑷姩瑙嗚鑳藉姏**锛氭ā鍨嬭皟鐢?`see` 宸ュ叿锛屽緱鍒颁竴寮?*鐪熷疄鎴浘锛堜綔涓哄浘鐗囷級**锛屼粠鑰?*鍘熺敓鐪嬪埌鐢婚潰**锛堟弿杩般€佽瘑鍒埅鍥炬枃瀛椼€佽鍥捐〃/鏂囨。锛夈€?
杩欐槸涓€涓?**DSH 缁勫悎鍖咃紙bundle锛?*锛岄€氳繃 `dsh plugin add` 瀹夎銆傛彃浠舵敞鍐屽伐鍏?鈫?璺ㄨ瑷€璋冪敤**鍖呭唴鎹嗙粦鐨?Python 鐗?cvision** 鎴睆/OCR 鈫?鍐欏叆 Harness 闄勪欢鏈嶅姟锛坄ctx.attachments.saveImage`锛夋垨杩斿洖鏂囨湰 鈫?浠?**`image` ContentBlock / `text`** 杩斿洖缁欐ā鍨嬨€?
## 宸ュ叿涓€瑙?
| 宸ュ叿 | 璇存槑 |
| --- | --- |
| `see(window?, region?, delay?, maximize?)` | 鎴睆/绐楀彛 鈫?**鍥剧墖**杩斿洖锛堟ā鍨嬪師鐢熺湅锛夈€俙region="x,y,w,h"` 鍙彇涓€鍧楋紙鐪?token锛夛紱`delay=姣` 绛夋覆鏌擄紱`maximize` 榛樿鍏?|
| `ocr(window?, region?, delay?)` | 鎴睆鍚?**OCR** 鈫?杩斿洖**鏂囨湰**锛堢粓绔?缃戦〉/鏂囨。蹇€熻瀛楋紝鐪佹暣鍥?token锛?|
| `list_windows()` | 鍒楀嚭鍙绐楀彛锛堟爣棰?鍙ユ焺+灏哄锛?|
| `capture_tabs(urls?/port?)` | 娴忚鍣ㄩ〉绛?*鑷姩鍒囨崲鍚庨€愰〉鎴浘**锛圕DP锛岃繑鍥炲寮犲浘鐗囷級 |

> 鍏抽敭锛?*榛樿涓嶆渶澶у寲銆佷笉鍒囧墠鍙?*鈥斺€擶GC 鎶撶獥鍙ｅ悎鎴愬唴瀹癸紝涓庡墠鍙?閬尅鏃犲叧銆?
## 鍒嗗彂锛氳嚜甯?Python 鐗?cvision

鎻掍欢**鎵撳寘浜?Python 鐗?cvision**锛堢洰褰?`cvision/`锛変笌 `requirements.txt`銆傚洜姝わ細

- 瀹夎鑰?*鏃犻渶鍏嬮殕 / 鎷疯礉鏈粨搴?*锛屼篃**涓嶉渶瑕佽缃?`CVISION_DIR` 鎸囧悜鏌愪釜缁濆璺緞**锛?- `CVISION_DIR` 榛樿瑙ｆ瀽涓?*鏈彃浠跺畨瑁呯洰褰?*锛坄import.meta.url` 鎺ㄥ锛夛紝鍗冲寘鍐呮崋缁戠増锛?- 鐩爣鏈哄櫒鍙渶鏈?**Python 3**锛屽苟鎵ц涓€娆′緷璧栧畨瑁呫€?
> 娉ㄦ剰锛歚cvision/` 鏄殢鍖呭鍒剁殑婧愮爜蹇収銆備粨搴撴牴 `cvision/` 鐨勬敼鍔ㄤ笉浼氳嚜鍔ㄥ悓姝ュ埌鍖呭唴锛?> 鍗囩骇鏃堕噸鏂版嫹璐?鈫?閲嶆柊 `dsh plugin add` 鍗冲彲銆?
## 鏋勫缓锛堜粎褰撴敼浜?`src/*.ts` 鎵嶉渶瑕侊級

鎻掍欢鍏ュ彛 `lib/index.js` 鐢?`src/index.ts` 缂栬瘧鑰屾潵锛圖SH 杩愯鏃跺彧鍔犺浇 JS锛夈€備粨搴撳凡鎻愪氦
缂栬瘧濂界殑 `lib/index.js`锛岃鍖呭嵆鍙敤锛涜嫢浣犳敼浜?`src/index.ts`锛岃鍦ㄦ湰鐩綍鎵ц锛?
```bash
npm run build        # 鍗?tsc -p tsconfig.json锛岄噸鐢熸垚 lib/index.js
```

## CI / 鍙戝竷

- **CI**锛坄.github/workflows/ci.yml`锛夛細姣忔 `push` / `pull_request` 鑷姩锛?  - `npm ci && npm run build`锛屽苟鏍￠獙 `lib/` 缂栬瘧浜х墿涓庢彁浜や竴鑷达紙鏀逛簡 `src` 鍗村繕缂栬瘧浼氬け璐ワ級锛?  - 璺?Python 绾€昏緫鍗曟祴锛坄encoding`/`detect`锛屼粎闇€ Pillow锛夛紝鍦?**ubuntu + macOS** 鐭╅樀涓婅繍琛屻€?- **鍙戝竷**锛氭墦涓€涓?`v*` 鏍囩锛堝 `v0.1.4`锛夋帹閫佸埌 GitHub锛孋I 鍦ㄦ瀯寤?娴嬭瘯閫氳繃鍚庤嚜鍔?  `npm pack` 鍑?`vision-<version>.tgz` 骞跺垱寤?GitHub Release 涓婁紶璇ヤ骇鐗╋紝
  鍙洿鎺?`dsh plugin add ./vision-0.1.4.tgz` 瀹夎銆?
```bash
git tag v0.1.4 && git push origin v0.1.4
```

## 鍓嶆彁

- 鐩爣鏈哄櫒锛歐indows 妗岄潰 + 鏈?Python 3锛堟彃浠堕潬 `child_process` 璋?`python -m cvision.cli_capture`锛夈€?- 瀹夎渚濊禆锛堜緷璧栨枃浠跺凡闅忔彃浠舵墦鍖咃級锛?
```powershell
python -m pip install -r requirements.txt
```

> 鏀惧埌鎻掍欢鐩綍涓嬫墽琛岋紝鎴栧厛 `cd` 鍒拌鐩綍銆?
## 瀹夎锛圖SH Desktop锛?
鍦?DSH Desktop 鐨勭粓绔紙profile 鐩綍锛夐噷锛屼粠鎻掍欢鐩綍鎵ц锛?
```powershell
dsh plugin add <姝ょ洰褰曠殑缁濆璺緞>
```

渚嬪锛圥owerShell锛夛細

```powershell
dsh plugin add C:\Users\14339\Desktop\git\C-Vision\C-Vision
```

鐒跺悗**閲嶅惎 DSH Desktop**銆傜敤 `dsh --dump-config` 鍙湅鍒板鍑?`# == Vision` 閰嶇疆灞傘€?
> 涔熷彲鎵撴垚 tarball 鍒嗗彂锛歚npm pack` 鍚庡湪 DSH 閲?`dsh plugin add ./vision-0.1.4.tgz`锛堟棤闇€鏋勫缓鏉冮檺锛夈€?
## 閰嶇疆锛堝彲閫夛級

榛樿鍗冲彲鐢紱濡傞渶瑕嗙洊锛?
- `CVISION_PYTHON`锛歅ython 鍙墽琛屾枃浠讹紝榛樿 `python`
- `CVISION_DIR`锛歝vision 椤圭洰鏍癸紙鍚?`cvision/` 鍖咃級銆傞粯璁?= 鏈彃浠跺畨瑁呯洰褰曪紙鍖呭唴鎹嗙粦鐗堬級銆傝嫢涓嶄娇鐢ㄥ寘鍐呭壇鏈紝鍙寚鍚戜粨搴撴牴銆?
## 妯″瀷鎬庝箞鐢?
妯″瀷閫夋嫨鏀寔鍥剧墖鐨?`deepseek-v4-flash-vision-exp` 鍚庯細

- "鍒椾竴涓嬪彲瑙佺獥鍙? 鈫?`list_windows()`锛堝厛鎵惧埌鐩爣绐楀彛锛夆啋 "鐢?see 鐪?VS Code" 鈫?`see(window="Visual Studio Code")`銆?- 鐩存帴璇?"鐢?see 鐪嬩竴涓嬪睆骞? 鈫?`see()`銆?- 鍙湅绐楀彛鍐呬竴灏忓潡 鈫?`see(window="X", region="x,y,w,h")`锛涢渶瑕佹覆鏌撴參鐨勯〉闈?鈫?`see(..., delay=800)`銆?- 鍙璇绘枃瀛?鈫?`ocr(window="X")`锛堣瘑鍒睆骞?绐楀彛涓殑鏂囨湰骞惰繑鍥烇紝鐪佸幓鏁村浘 token锛夈€?- 鐪嬫祻瑙堝櫒鍚勯〉绛?鈫?`capture_tabs(urls=[...])`锛堟棤澶村紑椤?閫愪釜鎴浘锛夋垨 `capture_tabs(port=9222)`锛堣繛宸插甫璋冭瘯鍙傛暟鐨勬祻瑙堝櫒锛夈€?
> 璇烽伒瀹堜笅闈㈢殑銆岀粰 AI 鏅鸿兘浣撶殑浣跨敤鎻愮ず銆嶁€斺€?*榛樿涓嶈 `maximize`锛屼篃涓嶈鐢ㄥ畠鍘诲垏鎹?婵€娲诲墠鍙扮獥鍙?*銆?
## 缁?AI 鏅鸿兘浣撶殑浣跨敤鎻愮ず锛堥噸瑕侊級

- **榛樿涓嶈浼?`maximize=true`**锛歐indows Graphics Capture 鎶撶殑鏄獥鍙?*鑷韩鐨勫悎鎴愬唴瀹?*锛?  璺熺獥鍙ｆ槸鍚﹀湪鍓嶅彴銆佹槸鍚﹁鍏跺畠绐楀彛閬尅**鏃犲叧**銆傚洜姝?*涓嶉渶瑕?*鎶婄獥鍙ｅ垏鍒板墠鍙帮紝涔?*涓嶉渶瑕?*鏈€澶у寲銆?- **涓嶈涓轰簡鎴浘鍘绘縺娲?鍒囨崲鍓嶅彴绐楀彛**锛歐GC 璺緞**涓嶆姠鐒︾偣銆佷笉鍒囪蛋浣犳鍦ㄧ敤鐨勭獥鍙?*锛屽叏绋嬫棤鎵撴壈銆?- **浠€涔堟儏鍐垫墠鐢?`maximize=true`**锛氫粎褰撶獥鍙ｅ凡**鏈€灏忓寲**锛堝唴瀹瑰緢灏?鐪嬩笉娓咃級銆佹垨**澶皬**銆?  鎴?*琚叾瀹冪獥鍙ｅ畬鍏ㄦ尅浣忎笖鍐呭璇讳笉鍑烘潵**鏃舵墠鐢ㄣ€傛彃浠舵姄瀹屼細**鑷姩杩樺師**绐楀彛鍘熺姸鎬併€?- **鎺ㄨ崘娴佺▼**锛氬厛 `list_windows()` 鐪嬫湁鍝簺绐楀彛 鈫?鐩存帴 `see(window="<绐楀彛鏍囬>")` 鎶撶洰鏍囩獥鍙ｏ紱
  闇€瑕佹暣灞忕敤 `see()`銆?
## 鐩綍缁撴瀯

```
vision/                      # 浠撳簱鏍?= 鎻掍欢鏈綋
  src/index.ts          # TypeScript 婧愶紙浣滆€呯敤 dsh-tools/cordis/dsh-attachment 绫诲瀷锛?  lib/index.js          # 缂栬瘧浜х墿锛圖SH 瀹為檯鍔犺浇锛沵ain/exports 鎸囧悜瀹冿級
  tsconfig.json         # TS 閰嶇疆锛坧npm build -> tsc锛?  package.json          # 澹版槑 dsh.bundle锛宖iles 鍚?lib/cvision/requirements.txt
  cordis.patch.yml      # bundle 鐨勯厤缃眰锛屾寜鍖呭悕寮曠敤
  requirements.txt      # Python 渚濊禆锛堥殢鍖呭垎鍙戯紱Windows 鍚?pywin32/winsdk锛宮acOS 鍚?pyobjc-Quartz锛?  cvision/              # 鎹嗙粦鐨?Python 鐗?cvision锛堟埅灞忓疄鐜帮紱宸茶鍓负鎻掍欢鎵€闇€锛?    __init__.py         #   鍖呮爣璁?    capturer.py         #   鍏煎灞傦細杞彂鍒板钩鍙版崟鑾峰悗绔紙cvision.capture锛?    capture/            #   骞冲彴鎹曡幏鍚庣锛堥棬闈紝鎸?sys.platform 閫夛級
      __init__.py       #     閫夊悗绔苟鏆撮湶 list_windows/capture_window/capture_screen
      base.py           #     骞冲彴鏃犲叧 Window + CaptureBackend 鍗忚
      windows.py        #     Windows 鍚庣锛圵GC > PrintWindow > 璇诲悎鎴愭闈㈠尯鍩?鍥為€€锛?      macos.py          #     macOS 鍚庣锛圦uartz 鏋氫妇 + screencapture -l 鎶撶獥鍙ｏ級
      linux.py          #     Linux 鍚庣锛圥hase 2锛屾殏涓哄崰浣嶏級
    detect.py           #   绾€昏緫鍒ゅ畾锛圙PU 绫?绌虹櫧甯э級锛屼笉渚濊禆 win32锛屽彲璺ㄥ钩鍙板崟娴?    encoding.py         #   PIL -> base64 data URL锛沜rop_region锛沠it_for_attachment(闄勪欢缂╁浘)
    ocr.py              #   OCR锛圵indows.Media.Ocr 浼樺厛 / pytesseract 鍥為€€锛?    cli_capture.py      #   璺ㄨ瑷€ CLI锛歱ython -m cvision.cli_capture [--list] [--region] [--delay]
    cli_ocr.py          #   OCR CLI锛歱ython -m cvision.cli_ocr [--window] [--region]
    tabs.py             #   Chromium 缃戦〉鏍囩鏋氫妇 + CDP 鎴浘锛堣嚜鍔ㄥ垏鎹㈤〉绛撅級
    cli_tabs.py         #   鏍囩鎴浘 CLI锛歱ython -m cvision.cli_tabs [--launch]
  tests/
    test_detect.py      #   detect 妯″潡鍗曟祴锛圥IL only锛?    test_encoding.py    #   encoding 妯″潡鍗曟祴锛坉ataURL/crop/fit锛孭IL only锛?  README.md
```

> 娉細MCP server 鐩稿叧鐨?`config.py`/`deepseek.py`/`server.py` 宸蹭粠鎹嗙粦鍖呯Щ闄わ紙鎻掍欢鎴睆鏃犻渶瀹冧滑锛屼篃鍏嶅幓浜?`DEEPSEEK_API_KEY` 渚濊禆锛夈€?
## OCR 鏂囨湰璇嗗埆

`ocr` 宸ュ叿瀵规埅灞?绐楀彛鍋氭枃瀛楄瘑鍒細
- **Windows**锛氱敤 `Windows.Media.Ocr`锛坄winsdk`锛岀郴缁熻瑷€鍖咃紝鍏嶉澶栦簩杩涘埗锛夛紱
- 鍥為€€锛氳 `pytesseract` + Tesseract 鍚庣敤鍏惰瘑鍒紙璺ㄥ钩鍙帮級銆?
## 娴忚鍣ㄧ綉椤垫爣绛炬埅鍥撅紙瀹為獙鎬э級

瀵?**Chrome/Edge 绛?Chromium**锛岀敤 CDP 鏋氫妇椤电銆佽嚜鍔ㄥ垏鎹㈠埌姣忛〉骞舵埅鍙?*椤甸潰鍐呭**锛堜笉鏄祻瑙堝櫒绐楀彛锛屼笌鍓嶅彴/閬尅鏃犲叧锛夛細

- **浣滀负鎻掍欢宸ュ叿**锛歚capture_tabs(urls=[...])` 鎴?`capture_tabs(port=9222)`锛岀洿鎺ヨ繑鍥炴瘡椤垫埅鍥撅紙鍥剧墖锛夈€?- **鎺у埗宸叉墦寮€鐨勬祻瑙堝櫒**锛氶渶娴忚鍣ㄥ惎鍔ㄦ椂甯?  `--remote-debugging-port=9222 --remote-allow-origins=*`锛堟柊鐗?Chrome 涓嶅姞鍚庤€?WebSocket 浼氳 403 鎷掞級銆?- 鎴?*鏂板缓**涓€涓甫璋冭瘯绔彛鐨勫疄渚嬪苟鎶?URL 浣滀负椤电锛?  ```bash
  python -m cvision.cli_tabs --launch --headless --urls https://a.com https://b.com --out tabcaps
  # 鎴栬繛鎺ュ凡鏈夌殑锛?  python -m cvision.cli_tabs --port 9222 --out tabcaps
  ```
- 杈撳嚭 JSON锛堟瘡椤电鏍囬/URL/淇濆瓨璺緞锛夛紝鎴浘瀛樺湪 `--out` 鐩綍銆?- 渚濊禆锛歚requests`銆乣websocket-client`锛堝凡鍐欏叆 `requirements.txt`锛夈€?
## 澶氬钩鍙版敮鎸?
- **Windows**锛氬畬鏁存敮鎸侊紙WGC/PrintWindow/妗岄潰鍖哄煙鍥為€€锛夛紝鏈€绋炽€?- **macOS**锛歅hase 1 宸叉敮鎸侊紙`Quartz/CGWindowList` 鏋氫妇 + `screencapture -l` 鎶撶獥鍙ｏ紝涓庡墠鍙版棤鍏筹級锛涢渶鍦ㄣ€岀郴缁熻缃?鈫?闅愮涓庡畨鍏?鈫?灞忓箷褰曞埗銆嶆巿鏉冿紝鍚﹀垯鏍囬涓虹┖/鍙兘鎶撳埌澹佺焊銆?- **Linux**锛歅hase 2 鍗犱綅锛堟湭瑙?`capture/linux.py` 瀹炵幇鍓嶈皟鐢ㄤ細 `NotImplementedError`锛夈€?
## 璇存槑涓庨檺鍒?
- 璺ㄨ瑷€锛氭彃浠剁敤 `child_process` 璋?`python -m cvision.cli_capture`锛岄渶鐩爣鏈哄櫒妗岄潰 + Python锛圵indows 鐢?pywin32锛宮acOS 鐢?pyobjc-Quartz锛夈€?- 鎴浘鑳藉姏锛歚capture_window` 渚濇灏濊瘯锛?*Windows Graphics Capture**锛堢湡瀹炲悎鎴愬唴瀹癸紝鎶?GPU/Chromium/琚伄鎸＄獥鍙ｆ渶鍑嗭紝闇€ `winsdk`锛夆啋 `PrintWindow`锛堟櫘閫?GDI 绐楀彛锛夆啋 璇诲悎鎴愭闈㈠尯鍩燂紙鍏滃簳锛夈€傝 `cvision/capture/windows.py`銆傛湭瑁?`winsdk` 鏃惰嚜鍔ㄨ烦杩?WGC銆?- 闄勪欢闄愬埗锛欻arness attachment 鍗曞浘婧?鈮?0MiB銆佸崟杈?鈮?192px銆佹瘡鏉℃秷鎭?鈮?0 寮狅紱鎴浘杈撳嚭鍓嶄細鑷姩缂╂斁鍒伴檺鍒跺唴锛坄encoding.fit_for_attachment`锛夛紝瓒呭ぇ灞忎篃涓嶄細琚嫆銆?- 鐪?token锛歚see`/`ocr` 鏀寔 `region="x,y,w,h"` 鍙鐞嗕竴鍧楋紱`ocr` 鐩存帴杩斿洖鏂囨湰锛涜秴澶у浘鑷姩闄嶉噰鏍枫€?- 鎴浘灏介噺涓嶆墦鎵帮細**WGC 鎶撳彇涓嶅垏鍓嶅彴銆佷笉鎶㈢劍鐐广€侀粯璁や笉鏈€澶у寲**锛涗粎褰?WGC 澶辨晥鍥為€€鍒?璇诲悎鎴愭闈㈠尯鍩?鏃舵墠鍙兘缃墠锛屼笖鎶撳畬绔嬪嵆杩樺師绐楀彛鐘舵€併€?- WGC 璁惧澶嶇敤锛氬崟杩涚▼鍐呯紦瀛?Direct3D 璁惧锛屽娆℃姄灞忔洿蹇紙CLI 姣忔鐙珛杩涚▼鐢ㄤ笉鍒帮紱MCP/寰幆閲囬泦鍙楃泭锛夈€?- 鎻掍欢鏈綋锛坄src/index.ts` 鈫?`lib/index.js`锛夋湭鍦ㄦ湰鐜绔埌绔窇杩囷紙鏃?DSH 杩愯鏃讹級锛涙寜 `@deepseek-ai/dsh-tools` / `ctx.attachments.saveImage` 瀹樻柟鎺ュ彛缂栧啓锛岄渶鍦ㄤ綘鐨?DSH Desktop 涓?`dsh plugin add` + 閲嶅惎鍚庨獙璇併€?
