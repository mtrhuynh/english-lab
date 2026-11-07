#!/usr/bin/env python3
"""Build lessons.json for English Lab from the IELTS lesson extracts package.
Source: ~/workspace/language-lab-study/ielts-lesson-extracts-v1.0.0 (index.json + per-lesson .md)
Output: lessons.json next to this script. Re-run whenever the extracts are updated.
"""
import json, re, sys
from pathlib import Path

SRC = Path.home() / "workspace/language-lab-study/ielts-lesson-extracts-v1.0.0"
OUT = Path(__file__).with_name("lessons.json")
MAX_TRANSCRIPT = 12000

QA_RE = re.compile(r"\*\*Q\d+\.\s*(.*?)\*\*\s*\nModel answer:\s*(.*?)(?=\n\*\*Q\d+\.|\n## |\Z)", re.S)
VOCAB_HEAD = "## Target vocabulary"
VOCAB_RE = re.compile(r"^- \*\*(.+?)\*\* — (.+)$", re.M)
CUE_RE = re.compile(r"\*\*Cue card task:\*\*\s*(.+?)\n\*\*You should say:\*\*\s*(.+?)\n", re.S)
TRANSCRIPT_RE = re.compile(r"\*\*Source transcript \(model performance\):\*\*\s*(.*?)(?=\n## |\Z)", re.S)
EP_RE = re.compile(r"\s*\((?:S\d+E\d+|Part\s*\d+)\)\s*$")

def sentences_split(text, target=550):
    """Split a long transcript into readable paragraph chunks at sentence ends."""
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) <= target:
        return [text] if text else []
    parts, buf = [], ""
    for sent in re.split(r"(?<=[.!?])\s+", text):
        if len(buf) + len(sent) > target and buf:
            parts.append(buf.strip()); buf = sent
        else:
            buf = (buf + " " + sent).strip()
    if buf:
        parts.append(buf.strip())
    return parts

def parse_lesson(entry):
    md = (SRC / entry["file"]).read_text(encoding="utf-8")
    title = entry["title"].strip()
    topic = EP_RE.sub("", title).strip()
    lesson = {"id": entry["id"], "part": str(entry["part"]), "no": entry["no"],
              "title": title, "topic": topic, "qa": [], "vocab": [], "cue": None, "paras": []}
    for q, a in QA_RE.findall(md):
        lesson["qa"].append({"q": re.sub(r"\s+", " ", q).strip(),
                              "a": re.sub(r"\s+", " ", a).strip()})
    if VOCAB_HEAD in md:
        vsec = md.split(VOCAB_HEAD, 1)[1]
        for term, rest in VOCAB_RE.findall(vsec):
            ex = ""
            m = re.search(r"\(Example:\s*(.*?)\)\s*$", rest)
            if m:
                ex = m.group(1).strip(); rest = rest[:m.start()].strip()
            lesson["vocab"].append({"t": term.strip(), "d": rest.strip(), "e": ex})
    cue = CUE_RE.search(md)
    if cue:
        lesson["cue"] = {"task": re.sub(r"\s+", " ", cue.group(1)).strip(),
                         "say": re.sub(r"\s+", " ", cue.group(2)).strip()}
        tr = TRANSCRIPT_RE.search(md)
        if tr:
            lesson["paras"] = sentences_split(tr.group(1)[:MAX_TRANSCRIPT])
    elif not lesson["qa"]:
        # Fallback: keep the cleaned body so no lesson renders empty.
        body = re.sub(r"^#.*$|^Part:.*$|^Lesson ID:.*$", "", md, flags=re.M)
        lesson["paras"] = sentences_split(body[:MAX_TRANSCRIPT])
    return lesson

def main():
    idx = json.loads((SRC / "index.json").read_text(encoding="utf-8"))
    lessons = [parse_lesson(e) for e in idx]
    data_dir = Path(__file__).with_name("data"); data_dir.mkdir(exist_ok=True)
    lite = []
    for l in lessons:
        (data_dir / f"{l['id']}.json").write_text(json.dumps(l, ensure_ascii=False), encoding="utf-8")
        lite.append({"id": l["id"], "part": l["part"], "no": l["no"], "title": l["title"],
                     "topic": l["topic"], "nq": len(l["qa"]), "nv": len(l["vocab"]),
                     "cue": bool(l["cue"])})
    lite_path = Path(__file__).with_name("index-lite.json")
    lite_path.write_text(json.dumps(lite, ensure_ascii=False), encoding="utf-8")
    nq = sum(len(l["qa"]) for l in lessons); nv = sum(len(l["vocab"]) for l in lessons)
    total = sum(f.stat().st_size for f in data_dir.glob("*.json"))
    print(f"lessons={len(lessons)} qa_pairs={nq} vocab={nv} cue={sum(1 for l in lessons if l['cue'])} "
          f"lite={lite_path.stat().st_size/1e3:.0f} KB data_total={total/1e6:.1f} MB")
    empty = [l["id"] for l in lessons if not l["qa"] and not l["paras"]]
    print("empty lessons:", len(empty), empty[:5])

if __name__ == "__main__":
    sys.exit(main())
