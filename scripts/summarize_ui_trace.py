#!/usr/bin/env python3
"""Summarize native presentation deadlines; reject hidden or empty captures.

Export hitches, hitches-updates, and hitches-frame-lifetimes together with xctrace.
Frame intervals below are differences between presentation timestamps, never the
inverse of a frame's pipeline lifetime. Static periods legitimately update slowly.
"""
from __future__ import annotations

import argparse
from datetime import datetime
import json
from pathlib import Path
import re
import sys
import xml.etree.ElementTree as ET


def summarize(toc: Path, metrics: Path, workload: Path | None = None) -> dict:
    run = ET.parse(toc).getroot().find("run")
    target = run.find("./info/target/process")
    pid = int(target.attrib["pid"])
    duration = float(run.findtext("./info/summary/duration"))
    trace_start = datetime.fromisoformat(run.findtext("./info/summary/start-date")).timestamp()
    tables = run.findall("./data/table")
    root = ET.parse(metrics).getroot()
    refs = {element.attrib["id"]: element for element in root.iter() if "id" in element.attrib}

    def resolve(element):
        return refs[element.attrib["ref"]] if "ref" in element.attrib else element

    def number(element):
        return float(resolve(element).text)

    def is_target(element):
        process = resolve(element)
        return process.tag == "process" and int(number(process.find("pid"))) == pid

    data = {}
    for node in root.findall("node"):
        index = int(re.search(r"table\[(\d+)\]", node.attrib["xpath"])[1]) - 1
        data[tables[index].attrib["schema"]] = node.findall("row")
    required = {"hitches", "hitches-updates", "hitches-frame-lifetimes"}
    if not required.issubset(data):
        raise ValueError("Missing native hitch/update/frame tables")
    updates = {int(number(row[4])): number(row[0])/1e9
               for row in data["hitches-updates"] if is_target(row[2])}
    presentations = sorted({number(row[0])/1e9 + number(row[1])/1e9
                            for row in data["hitches-frame-lifetimes"]
                            if int(number(row[3])) in updates})
    if len(presentations) < 2:
        raise ValueError("No usable app-specific native presentation samples")
    hitches = [{"start_seconds": number(row[0])/1e9, "missed_deadline_ms": number(row[1])/1e6}
               for row in data["hitches"] if is_target(row[2])]
    phases = []
    visible = None
    if workload is not None:
        benchmark = json.loads(workload.read_text())
        visible = benchmark.get("native_visible_capture", False)
        windows = benchmark.get("phase_windows") or []
        if not windows:
            raise ValueError("Workload has no phase time windows")
        for window in windows:
            start = window["start_epoch_s"] - trace_start
            end = window["end_epoch_s"] - trace_start
            points = [value for value in presentations if start <= value < end]
            gaps = [(b-a)*1000 for a, b in zip(points, points[1:])]
            missed = [hitch for hitch in hitches if start <= hitch["start_seconds"] < end]
            phases.append({"phase": window["phase"], "seconds": end-start,
                           "presentations": len(points), "hitches": len(missed),
                           "max_presentation_interval_ms": max(gaps, default=None),
                           "presentation_intervals_over_25ms": sum(gap > 25 for gap in gaps)})
        start = windows[0]["start_epoch_s"] - trace_start
        end = windows[-1]["end_epoch_s"] - trace_start
        hitches = [hitch for hitch in hitches if start <= hitch["start_seconds"] < end]
    valid = visible is not False and all(phase["presentations"] > 1 for phase in phases)
    passed = valid and not hitches
    return {"target": target.attrib["name"], "recording_seconds": duration,
            "app_presentations": len(presentations), "visible_workload": visible,
            "valid_capture": valid, "deadline_check_passed": passed,
            "hitch_count": len(hitches), "total_hitch_ms": sum(h["missed_deadline_ms"] for h in hitches),
            "longest_hitch_ms": max((h["missed_deadline_ms"] for h in hitches), default=0),
            "phases": phases, "hitches": hitches,
            "limitations": "Recorded machine/workload only. Native presentation gaps include intentional idle time. CPU paint and timer timings are not FPS. A hidden, incomplete, or empty workload cannot pass."}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("toc", type=Path)
    parser.add_argument("metrics", type=Path)
    parser.add_argument("--workload", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        result = summarize(args.toc, args.metrics, args.workload)
    except (OSError, ValueError, KeyError, IndexError, AttributeError, TypeError, ET.ParseError) as error:
        print(f"Invalid performance capture: {error}", file=sys.stderr)
        return 2
    encoded = json.dumps(result, indent=2) + "\n"
    if args.output:
        args.output.write_text(encoded)
    print(encoded)
    return 0 if result["deadline_check_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
