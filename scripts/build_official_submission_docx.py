#!/usr/bin/env python3
"""Fill the exact official application without rebuilding its OOXML structures.

Run with the bundled workspace Python returned by load_workspace_dependencies.
Download the template separately; the official template is intentionally not
vendored. This builder never writes participant information or consent/signatures.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import html
import json
from pathlib import Path
import re
from zipfile import ZipFile

from lxml import etree

TEMPLATE_URL = "https://appdevchallenge.auto-hmg.io/downloads/contest-application-consent.docx"
TEMPLATE_SHA256 = "07be893d58b0e96ab7788f0d189d6829f0e59a2cee4bc18cb90ec37eeda2f5fd"
NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
SLOTS = (
    "app_summary", "planning_background", "vehicle_scenario", "key_features",
    "pleos_plan", "reference_files", "reference_link", "shortform_link",
)
BODY_SLOTS = {31: "app_summary", 33: "planning_background", 35: "vehicle_scenario",
              37: "key_features", 39: "pleos_plan", 41: "reference_files",
              43: "reference_link", 45: "shortform_link"}


def digest(data: bytes) -> str:
    return sha256(data).hexdigest()


def paragraphs(source: Path) -> dict[str, str]:
    raw = source.read_text(encoding="utf-8")
    result = {}
    for match in re.finditer(r"<!-- slot:([a-z_]+) -->\s*\n(.*?)(?=<!-- slot:|<!-- end-slots -->)", raw, re.S):
        result[match[1]] = match[2].strip()
    if tuple(result) != SLOTS:
        raise ValueError(f"Unexpected source slots: {tuple(result)}")
    if any(not result[k] for k in SLOTS[:-1]):
        raise ValueError("Required project response is blank")
    if result["shortform_link"]:
        raise ValueError("Published shortform URL has not been supplied; keep it blank")
    return result


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--template", type=Path, required=True)
    ap.add_argument("--source", type=Path, default=Path("Docs/OFFICIAL_SUBMISSION_PROPOSAL.md"))
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--evidence-dir", type=Path, required=True)
    args = ap.parse_args()
    if args.template.resolve() == args.output.resolve():
        raise ValueError("Output must differ from retained template")
    template_data = args.template.read_bytes()
    if digest(template_data) != TEMPLATE_SHA256:
        raise ValueError("Official template hash changed; inspect and distill again")
    values = paragraphs(args.source)
    with ZipFile(args.template) as zin:
        parts = {item.filename: zin.read(item.filename) for item in zin.infolist()}
        infos = zin.infolist()
    original = parts["word/document.xml"]
    xml = original.decode("utf-8")
    original_root = etree.fromstring(original)
    body = original_root.find("w:body", NS)
    assert body is not None
    for index, tag in BODY_SLOTS.items():
        actual = body[index].find(".//w:sdtPr/w:tag", NS)
        assert actual is not None and actual.get(f"{{{NS['w']}}}val") == tag
    assert len(original_root.findall(".//w:sdt", NS)) == 8
    replacements = []
    for tag in SLOTS:
        pattern = re.compile(r'<w:sdt>(?:(?!</w:sdt>).)*?<w:tag w:val="' + tag + r'"/>(?:(?!</w:sdt>).)*?</w:sdt>', re.S)
        found = pattern.findall(xml)
        if len(found) != 1:
            raise ValueError(f"Ambiguous SDT {tag}")
        old = found[0]
        control = original_root.xpath(f'.//w:sdt[w:sdtPr/w:tag[@w:val="{tag}"]]', namespaces=NS)[0]
        assert control.find("w:sdtPr/w:text", NS) is not None, "Not a plain-text SDT"
        assert len(control.findall(".//w:t", NS)) == 1
        # Preserve the existing plain-text control, paragraph and run. In the
        # four multiline controls, represent plain-text newlines as OOXML
        # line breaks within that same run; Word/LO collapse LF inside w:t.
        value = values[tag] or " "
        if tag in {"planning_background", "vehicle_scenario", "key_features", "pleos_plan"}:
            lines = [line for line in value.splitlines() if line.strip()]
            encoded = '</w:t><w:br/><w:t xml:space="preserve">'.join(html.escape(line, quote=False) for line in lines)
        else:
            encoded = html.escape(" ".join(value.splitlines()), quote=False)
        new = re.sub(r'(<w:t\b[^>]*>).*?(</w:t>)', lambda m: m[1] + encoded + m[2], old, count=1, flags=re.S)
        # The only source highlight is a yellow blank placeholder in field6.
        # Clear it only inside this editable response, retaining every control.
        if tag == "reference_files":
            new = new.replace('<w:highlight w:val="yellow"/>', '<w:highlight w:val="none"/>')
        xml = xml.replace(old, new, 1)
        replacements.append((old, new))
    # Replace underscore text only in the three known project-name paragraphs; the final one is non-consent metadata.
    name_edits = []
    for match in re.finditer(r'<w:p\b[^>]*>.*?</w:p>', xml, re.S):
        frag = match[0]
        text = "".join(html.unescape(x) for x in re.findall(r'<w:t\b[^>]*>(.*?)</w:t>', frag, re.S))
        if text.startswith("앱명 / 프로젝트명:") and "_" in text:
            name_edits.append(frag)
    if len(name_edits) != 3:
        raise ValueError("Expected exactly three project-name fields")
    for old in name_edits:
        first = True
        def fill_name(m):
            nonlocal first
            if "_" not in m[2]:
                return m[0]
            def replace_blank(blank):
                nonlocal first
                value = "CarCue(카큐)" if first else ""
                first = False
                return value
            return m[1] + re.sub(r"_+", replace_blank, m[2]) + m[3]
        new = re.sub(r'(<w:t\b[^>]*>)(.*?)(</w:t>)', fill_name, old, flags=re.S)
        xml = xml.replace(old, new, 1)
        replacements.append((old, new))
    # Whole-part reversible proof: no undocumented main-document edit.
    reverted = xml
    for old, new in reversed(replacements):
        assert new in reverted
        reverted = reverted.replace(new, old, 1)
    assert reverted == original.decode("utf-8")
    final_xml = xml.encode("utf-8")
    root = etree.fromstring(final_xml)
    final_body = root.find("w:body", NS)
    assert final_body is not None
    assert len(body) == len(final_body)
    for i in range(47, len(body)):
        if i != 76:  # Explicitly authorized known app name only.
            assert etree.tostring(body[i]) == etree.tostring(final_body[i]), f"Legal/signature change at body {i}"
    for i in range(24):
        if i != 12:
            assert etree.tostring(body[i]) == etree.tostring(final_body[i]), f"Participant change at body {i}"
    assert len(root.findall(".//w:sdt", NS)) == 8
    for i in [12,29,76]:
        name_text = "".join(final_body[i].xpath(".//w:t/text()", namespaces=NS))
        assert name_text.startswith("앱명 / 프로젝트명: CarCue(카큐)"), name_text
    assert etree.tostring(root.find(".//w:sectPr", NS)) == etree.tostring(original_root.find(".//w:sectPr", NS))
    project_text = "".join(root.xpath("/w:document/w:body/*[position() >= 25 and position() <= 47]//w:t/text()", namespaces=NS))
    assert "@" not in project_text, "Personal email in project section"
    for term in ["12개", "4주제", "606개", "미완료", "실측값은 없습니다", "다른 빌드"]:
        assert term in project_text, term
    assert project_text.count("CarCue(카큐)") >= 2
    settings = parts["word/settings.xml"]
    assert b"<w:updateFields" not in settings
    updated_settings = settings.replace(b"</w:settings>", b'<w:updateFields w:val="true"/></w:settings>')
    assert updated_settings != settings
    parts["word/document.xml"] = final_xml
    parts["word/settings.xml"] = updated_settings
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(args.output, "w") as zout:
        for info in infos:
            zout.writestr(info, parts[info.filename])
    with ZipFile(args.output) as zout, ZipFile(args.template) as zin:
        unchanged = [name for name in parts if name not in {"word/document.xml", "word/settings.xml"}]
        assert all(zout.read(name) == zin.read(name) for name in unchanged)
        assert zout.namelist() == zin.namelist()
    assert args.template.read_bytes() == template_data
    args.evidence_dir.mkdir(parents=True, exist_ok=True)
    inventory = [{"part": name, "bytes": len(data), "sha256": digest(data)} for name, data in parts.items()]
    baseline = []
    with ZipFile(args.template) as zin:
        baseline = [{"part": n, "bytes": len(zin.read(n)), "sha256": digest(zin.read(n))} for n in zin.namelist()]
    (args.evidence_dir / "template-parts.json").write_text(json.dumps(baseline, ensure_ascii=False, indent=2)+"\n")
    report = {
        "template_url": TEMPLATE_URL, "template_sha256": TEMPLATE_SHA256,
        "source_path": str(args.source.resolve()), "source_sha256": digest(args.source.read_bytes()),
        "output_path": str(args.output.resolve()), "output_sha256": digest(args.output.read_bytes()),
        "changed_parts": ["word/document.xml", "word/settings.xml"],
        "main_document_scope": "7 responses in8 preserved plain-text controls and3 project-name values; existing multiline inputs represented by w:br within source runs; field6 blank highlight cleared",
        "settings_scope": "updateFields=true for native PAGE refresh on Word opening",
        "unchanged_parts": unchanged, "all_legal_and_signature_nodes_identical_except_known_app_name": True,
        "legal_appname_only_exception_body_index": 76,
        "participant_fields_except_project_name_identical": True,
        "all_controls_and_geometry_preserved": True,
        "optional_shortform_blank": True,
        "slot_characters": {k: len(v) for k,v in values.items()}, "output_parts": inventory,
    }
    (args.evidence_dir / "content-and-fidelity.json").write_text(json.dumps(report, ensure_ascii=False, indent=2)+"\n")
    print(json.dumps({"output":str(args.output.resolve()), "sha256":report["output_sha256"], "slots":report["slot_characters"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
