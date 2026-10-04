#!/usr/bin/env python3
"""把 飞书正文.md 转成「占位符 + 分块」形式，供飞书分块粘贴。"""
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
src = open(os.path.join(ROOT, "飞书正文.md"), encoding="utf-8").read()

mapping = {}
n = [0]


def repl(m):
    alt, path = m.group(1), m.group(2)
    if path.startswith(("http", "#")):
        return m.group(0)
    n[0] += 1
    tag = f"ZZIMG{n[0]:02d}ZZ"
    mapping[tag] = {"path": path, "alt": alt,
                    "exists": os.path.exists(os.path.join(ROOT, path))}
    return f"{tag}  [{alt}]"


out = re.sub(r'!\[([^\]]*)\]\(([^)]+)\)', repl, src)

paras = [p for p in re.split(r'\n\s*\n', out) if p.strip()]
chunks, cur, tot = [], [], 0
for p in paras:
    if cur and tot + len(p) > 1600:
        chunks.append('\n\n'.join(cur))
        cur, tot = [], 0
    cur.append(p)
    tot += len(p)
if cur:
    chunks.append('\n\n'.join(cur))

json.dump(chunks, open(os.path.join(ROOT, ".chunks.json"), "w"), ensure_ascii=False)
json.dump(mapping, open(os.path.join(ROOT, ".imgmap.json"), "w"), ensure_ascii=False)

print(f"占位符 {n[0]} 个，分 {len(chunks)} 块，最大 {max(len(c) for c in chunks)} 字符")
for k, v in mapping.items():
    print(f"  {k} {'OK ' if v['exists'] else 'MISS'} {v['path']}")
