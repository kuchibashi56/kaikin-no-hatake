# ITEMS.md を index.html から起こし直す。
#
#   python tools/dump_items.py
#
# リポジトリの一番上で実行する。index.html のデータ層を読んで
# ITEMS.md を書き出すだけで、ゲーム本体には触らない。
# アイテムやレシピを足したら、これを走らせれば一覧が追いつく。

# index.html のデータ層（ITEMS / NODES / RECIPES / CROPS / FERT / UPG / AREAS）を
# そのまま読み取る。ゲーム本体には一切触らない。
import io
import re

SRC = io.open('index.html', encoding='utf-8').read()

# const NAME=123 の定数（レシピの中から参照されている）
CONSTS = {}
for m in re.finditer(r'const\s+([A-Z][A-Z0-9_]*)\s*=\s*(\d+)', SRC):
    CONSTS[m.group(1)] = int(m.group(2))


class P(object):
    def __init__(self, s, i):
        self.s = s
        self.i = i

    def ws(self):
        s, n = self.s, len(self.s)
        while self.i < n:
            c = s[self.i]
            if c in ' \t\r\n':
                self.i += 1
            elif s.startswith('/*', self.i):
                self.i = s.index('*/', self.i) + 2
            elif s.startswith('//', self.i):
                j = s.find('\n', self.i)
                self.i = n if j < 0 else j + 1
            else:
                return

    def val(self):
        self.ws()
        s = self.s
        c = s[self.i]
        if c == '{':
            return self.obj()
        if c == '[':
            return self.arr()
        if c in "'\"":
            return self.str()
        m = re.match(r'-?\d+(\.\d+)?', s[self.i:])
        if m:
            self.i += m.end()
            t = m.group(0)
            return float(t) if '.' in t else int(t)
        m = re.match(r'[A-Za-z_$][A-Za-z0-9_$]*', s[self.i:])
        if m:
            self.i += m.end()
            t = m.group(0)
            if t == 'true':
                return True
            if t == 'false':
                return False
            if t == 'null':
                return None
            return CONSTS.get(t, t)
        raise ValueError('unexpected %r at %d' % (s[self.i:self.i + 30], self.i))

    def str(self):
        q = self.s[self.i]
        self.i += 1
        out = []
        while self.s[self.i] != q:
            if self.s[self.i] == '\\':
                self.i += 1
            out.append(self.s[self.i])
            self.i += 1
        self.i += 1
        return ''.join(out)

    def obj(self):
        self.i += 1
        d = {}
        while True:
            self.ws()
            if self.s[self.i] == '}':
                self.i += 1
                return d
            if self.s[self.i] == ',':
                self.i += 1
                continue
            if self.s[self.i] in "'\"":
                k = self.str()
            else:
                m = re.match(r'[A-Za-z_$][A-Za-z0-9_$.]*', self.s[self.i:])
                k = m.group(0)
                self.i += m.end()
            self.ws()
            assert self.s[self.i] == ':', (k, self.s[self.i:self.i + 20])
            self.i += 1
            d[k] = self.val()

    def arr(self):
        self.i += 1
        a = []
        while True:
            self.ws()
            if self.s[self.i] == ']':
                self.i += 1
                return a
            if self.s[self.i] == ',':
                self.i += 1
                continue
            a.append(self.val())


def grab(name):
    m = re.search(r'const\s+%s\s*=\s*' % name, SRC)
    p = P(SRC, m.end())
    return p.val()


ITEMS = grab('ITEMS')
NODES = grab('NODES')
RECIPES = grab('RECIPES')
CROPS = grab('CROPS')
FERT = grab('FERT')
UPG = grab('UPG')
AREAS = grab('AREAS')


# アイテム一覧を index.html のデータ層から起こす。手で書き写さない。
ALLREC = RECIPES

# out が空のレシピは「この先の何か」を示す番人で、作れる物ではない
RECIPES = [r for r in ALLREC if r.get('out')]
SENTINEL = [r for r in ALLREC if not r.get('out')]

NM = lambda k: (ITEMS[k]['icon'] + ITEMS[k]['name']) if k in ITEMS else k
AREA = dict((a['id'], a['name']) for a in AREAS)
NODE = dict((n['id'], n) for n in NODES)
KINDJA = {'material': '素材', 'tool': '道具', 'station': '設備',
          'plot': '区画', 'storage': '収納', 'villager': '住民'}

# ---- 索引 ----
fromNode = {}   # item -> [node]
for n in NODES:
    for k in n['yield']:
        fromNode.setdefault(k, []).append(n)
fromCrop = dict((k, v) for k, v in CROPS.items())
fromRec = {}    # item -> [recipe]
usedIn = {}     # item -> [recipe]
for r in RECIPES:
    for k in r['out']:
        fromRec.setdefault(k, []).append(r)
    for k in r['inputs']:
        usedIn.setdefault(k, []).append(r)
    if r.get('limit'):
        usedIn.setdefault(r['limit']['from'], []).append(r)


opens = {}      # item -> [解禁されるもの]


def addopen(item, what):
    opens.setdefault(item, [])
    if what not in opens[item]:
        opens[item].append(what)


for c in [(r, cond) for r in RECIPES for cond in r.get('unlock', [])]:
    r, cond = c
    p = cond.split(':')
    if p[0] in ('got', 'have') and p[1] in ITEMS:
        addopen(p[1], NM(list(r['out'].keys())[0]))
    if p[0] == 'min':
        addopen(p[1], NM(list(r['out'].keys())[0]) + '（' + p[2] + '個所持）')
for n in NODES:
    if n.get('requires'):
        p = n['requires'].split(':')
        if p[1] in ITEMS:
            addopen(p[1], n['icon'] + n['name'] + '（' + AREA[n['area']] + '）')
for a in AREAS:
    p = a['unlock'].split(':')
    if len(p) > 1 and p[1] in ITEMS:
        addopen(p[1], a['icon'] + a['name'] + 'エリア')
for k, cr in CROPS.items():
    p = cr['unlock'].split(':')
    if len(p) > 1 and p[1] in ITEMS:
        addopen(p[1], cr['icon'] + cr['name'] + 'の種')


def source(k):
    """その物の入手手段"""
    out = []
    for n in fromNode.get(k, []):
        y = n['yield'][k]
        out.append('採取 %s%s（%s）%d〜%d' %
                   (n['icon'], n['name'], AREA[n['area']], y[0], y[1]))
    if k in fromCrop:
        out.append('畑で育てる（%d秒・%d収穫）' % (fromCrop[k]['grow'], fromCrop[k]['yield']))
    for r in fromRec.get(k, []):
        st = '／'.join(ITEMS[s]['name'] if s in ITEMS else s
                       for s in (r.get('station') or ['手仕事']))
        n = r['out'][k]
        out.append('%s%s%s<br>　%s' % (
            st, '（%d秒）' % r['time'] if r.get('time') else '',
            ' ×%d' % n if n > 1 else '', ingr(r)))
    return '<br>'.join(out) or '—'


def ingr(r):
    return '＋'.join('%s×%d' % (NM(k), v) for k, v in r['inputs'].items())


def uses(k, lim=4):
    """何に使うか"""
    out = []
    for r in usedIn.get(k, []):
        for o in r['out']:
            nm = NM(o)
            if nm not in out:
                out.append(nm)
    if k in FERT:
        out.append('畑の肥料')
    for f, ups in UPG.items():
        for u in ups:
            if u['item'] == k:
                out.append(ITEMS[f]['name'] + 'に据え付け')
    if len(out) > lim:
        return '　'.join(out[:lim]) + ' 他%d件' % (len(out) - lim)
    return '　'.join(out) or '—'


def cond(c):
    p = c.split(':')
    if p[0] == 'start':
        return '最初から'
    if p[0] == 'never':
        return '—'
    if p[0] == 'got':
        return NM(p[1]) + 'を作ると'
    if p[0] == 'have':
        return NM(p[1]) + 'を持っていると'
    if p[0] == 'min':
        return NM(p[1]) + 'を' + p[2] + '個持っていると'
    return c


L = []
w = L.append

w('# 解禁の畑 — アイテム一覧')
w('')
w('index.html のデータ層（ITEMS / NODES / RECIPES / CROPS / FERT / UPG）から')
w('そのまま起こした一覧。手で書いた物ではないので、中身とずれない。')
w('')
cnt = {}
for it in ITEMS.values():
    cnt[it['kind']] = cnt.get(it['kind'], 0) + 1
w('| 種類 | 数 |')
w('|---|---:|')
for k in ['material', 'tool', 'station', 'storage', 'plot', 'villager']:
    w('| %s | %d |' % (KINDJA[k], cnt.get(k, 0)))
w('| **合計** | **%d** |' % len(ITEMS))
w('')
w('ほかに 採取場所 %d か所、レシピ %d 種、エリア %d か所、作物 %d 種。'
  % (len(NODES), len(RECIPES), len(AREAS), len(CROPS)))
if SENTINEL:
    w('')
    w('※ レシピにはもう1件、作れる物のない「%s」が入っている。'
      % SENTINEL[0]['hint'])
    w('　全解禁したあとに見える札で、ここでは数に入れていない。')
w('')

# ---------------- 素材 ----------------
w('## 素材（%d）' % cnt['material'])
w('')
w('並びは index.html の中の順。おおむね手に入る順になっている。')
w('')
w('入手の欄の秒数は、仕掛けてから出来上がるまでの待ち時間。')
w('秒数が書いていない物はその場で出来る。')
w('')
w('| | 名前 | 入手 | 使い道 |')
w('|---|---|---|---|')
for k, it in ITEMS.items():
    if it['kind'] != 'material':
        continue
    nm = it['name'] + ('<br>〈食料〉' if it.get('cat') == 'food' else '')
    w('| %s | %s | %s | %s |' % (it['icon'], nm, source(k), uses(k)))
w('')
w('〈食料〉の物は、保存食棚を建てると置ける量が増える（+60）。')
w('')

# ---------------- 道具 ----------------
w('## 道具（%d）' % cnt['tool'])
w('')
w('持っているだけで効く。材料として消えることはない。')
w('')
w('| | 名前 | 材料 | 開くもの | 効果 |')
w('|---|---|---|---|---|')
for k, it in ITEMS.items():
    if it['kind'] != 'tool':
        continue
    r = fromRec.get(k, [None])[0]
    mods = it.get('mods') or []
    eff = []
    for m in mods:
        kk, mu = m['k'], m.get('mul')
        base = kk.split('.')
        tgt = NM(base[1]) if base[1] in ITEMS else (
            NODE[base[1]]['name'] if base[1] in NODE else base[1])
        if base[0] == 'cd':
            eff.append('%sの待ち時間 ×%s' % (tgt, mu))
        elif base[0] == 'grow':
            eff.append('%sの成長 ×%s' % (tgt, mu))
        else:
            eff.append('%s ×%s' % (kk, mu))
    w('| %s | %s | %s | %s | %s |' %
      (it['icon'], it['name'], ingr(r) if r else '—',
       '<br>'.join(opens.get(k, [])) or '—', '<br>'.join(eff) or '—'))
w('')

# ---------------- 設備・区画・収納 ----------------
w('## 設備・区画・収納（%d）' % (cnt.get('station', 0) + cnt.get('plot', 0) + cnt.get('storage', 0)))
w('')
w('| | 名前 | 種類 | 材料 | できること |')
w('|---|---|---|---|---|')
for k, it in ITEMS.items():
    if it['kind'] not in ('station', 'plot', 'storage'):
        continue
    r = fromRec.get(k, [None])[0]
    made = []
    for x in RECIPES:
        if x.get('station') and k in x['station']:
            for o in x['out']:
                if NM(o) not in made:
                    made.append(NM(o))
    note = ''
    if made:
        note = 'ここで作る物 %d 種：%s' % (
            len(made), '　'.join(made[:6]) + (' 他' if len(made) > 6 else ''))
    if it.get('caps'):
        note = '置ける量が増える（%s +%d）' % (
            '食料' if it['caps'][0]['cat'] == 'food' else it['caps'][0]['cat'],
            it['caps'][0]['add'])
    if k == 'crate':
        note = 'すべての物の置ける量が増える（+40）'
    if k == 'vault':
        note = '置ける量が大きく増える（+150）。収納箱を作れる数も増える'
    if k == 'farm':
        note = '作物を育てる区画。1つにつき区画が1つ増える'
    w('| %s | %s | %s | %s | %s |' %
      (it['icon'], it['name'], KINDJA[it['kind']], ingr(r) if r else '—', note))
w('')
w('炉だけは1台ずつ手入れでき、据え付けた物はその台にしか効かない。')
w('')
w('| 据え付ける物 | 置ける場所 | 効果 |')
w('|---|---|---|')
for f, ups in UPG.items():
    for u in ups:
        w('| %s | %s | %s |' % (NM(u['item']), ITEMS[f]['name'], u['note']))
w('')

# ---------------- 住民 ----------------
w('## 住民（%d）' % cnt.get('villager', 0))
w('')
w('| | 名前 | 顔を覚えてもらう条件 | 回してくれる物 |')
w('|---|---|---|---|')
for k, it in ITEMS.items():
    if it['kind'] != 'villager':
        continue
    r = fromRec.get(k, [None])[0]
    rs = [x for x in RECIPES if x.get('station') and k in x['station']]
    deal = '<br>'.join('%s → %s' % (ingr(x), '　'.join(
        '%s×%d' % (NM(o), x['out'][o]) for o in x['out'])) for x in rs)
    w('| %s | %s | %s | %s |' %
      (it['icon'], it['name'],
       ingr(r) + ('（' + '／'.join(cond(c) for c in r['unlock']) + '）' if r else '')
       if r else '—', deal or '—'))
w('')

# ---------------- 採取場所 ----------------
w('## 採取場所（%d）' % len(NODES))
w('')
w('| | 場所 | エリア | 待ち時間 | 取れる物 | 必要な物 |')
w('|---|---|---|---|---|---|')
for n in NODES:
    y = '　'.join('%s %d〜%d' % (NM(k), v[0], v[1]) for k, v in n['yield'].items())
    w('| %s | %s | %s | %d秒 | %s | %s |' %
      (n['icon'], n['name'], AREA[n['area']], n['cd'], y,
       cond(n['requires']) if n.get('requires') else '—'))
w('')
w('### エリア')
w('')
w('| | エリア | 入れるようになる条件 |')
w('|---|---|---|')
for a in AREAS:
    w('| %s | %s | %s |' % (a['icon'], a['name'], cond(a['unlock'])))
w('')

# ---------------- 作物・肥料 ----------------
w('## 作物（%d）' % len(CROPS))
w('')
w('| | 作物 | 育つ時間 | 収穫 | 植えられる条件 |')
w('|---|---|---|---|---|')
for k, c in CROPS.items():
    w('| %s | %s | %d秒 | %d | %s |' %
      (c['icon'], c['name'], c['grow'], c['yield'], cond(c['unlock'])))
w('')
w('### 肥料')
w('')
w('| | 肥料 | 成長 | 収穫量 | 中身 |')
w('|---|---|---|---|---|')
for k, f in FERT.items():
    w('| %s | %s | ×%s | %s | %s |' %
      (ITEMS[k]['icon'], ITEMS[k]['name'], f['grow'],
       ('+%d' % f['yield']) if f['yield'] else '変わらない', f['note']))
w('')
w('肥料は区画ごとに入れる。1区画に1種類まで。')

io.open('ITEMS.md', 'w', encoding='utf-8', newline='\n').write('\n'.join(L) + '\n')
print('ITEMS.md written:', len(L), 'lines')
