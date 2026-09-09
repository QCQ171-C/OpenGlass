#!/usr/bin/env python3
"""Audit the Legacy Aero Peek highlight/reflection projection subset."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
from typing import Any

import audit_symbol_resolution as AUDIT


WATCH_SYMBOLS: dict[str, tuple[str, ...]] = {
    "udwm": (
        "CTopLevelWindow::CloneVisualTreeForLivePreview",
        "CTopLevelWindow::GetActualWindowRect",
        "CTopLevelWindow::TreatAsActiveWindow",
        "CLivePreview::_UpdateResources",
        "CLivePreview::_FadeOutToGlass",
        "CLivePreview::_UpdateInstructions",
        "CLivePreview::_UpdateResourcesForMonitorHelper",
    ),
    "dwmcore": (
        "CVisual::GetTopLevelWindow",
        "CDrawingContext::GetCurrentVisual",
        "CDrawingContext::PreSubgraph",
        "CImageLegacyMilBrush::`vftable'",
        "CRenderData::TryDrawCommandAsDrawList.pre22000",
        "CRenderData::TryDrawCommandAsDrawList.22000",
        "CRenderData::DrawImageResource_FillMode.pre19041",
        "CRenderData::DrawImageResource_FillMode.19041",
        "CRenderData::DrawImageResource_FillMode.22000",
        "CRenderData::DrawImageResource_FillMode.26100.2454",
    ),
}


FILENAMES = {
    "udwm": "uDWM.dll",
    "dwmcore": "dwmcore.dll",
}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("repo", nargs="?", type=Path, default=Path("."))
    parser.add_argument(
        "--samples-root",
        type=Path,
        default=Path("OGDcomplie"),
        help="directory containing uDWM.dll/dwmcore.dll samples",
    )
    parser.add_argument(
        "--symbol-path",
        type=Path,
        default=Path("Cache") / "symbol-catalog" / "symbols",
        help="local symbol cache or exact PDB path",
    )
    parser.add_argument("--dbghelp", type=Path, help="DbgHelp DLL used for complete-name undecoration")
    parser.add_argument("--module", choices=("udwm", "dwmcore", "both"), default="both")
    parser.add_argument("--configuration", choices=("debug", "release"), default="release")
    parser.add_argument("--min-build", type=int, help="include only samples at or above this build")
    parser.add_argument("--max-build", type=int, help="include only samples at or below this build")
    parser.add_argument("--show-inactive", action="store_true", help="also print inactive watched symbols")
    parser.add_argument(
        "--allow-missing-pdb",
        action="store_true",
        help="report missing PDBs without making the script fail",
    )
    return parser.parse_args(argv)


def resolved_under_repo(repo: Path, path: Path) -> Path:
    return path.resolve() if path.is_absolute() else (repo / path).resolve()


def selected_modules(value: str) -> tuple[str, ...]:
    return ("udwm", "dwmcore") if value == "both" else (value,)


def iter_images(samples_root: Path, modules: tuple[str, ...]) -> list[tuple[str, Path]]:
    images: list[tuple[str, Path]] = []
    for module in modules:
        filename = FILENAMES[module].lower()
        for image in samples_root.rglob("*"):
            if image.is_file() and image.name.lower() == filename:
                images.append((module, image.resolve()))
    return sorted(images, key=lambda item: (str(item[1]).lower(), item[0]))


def build_allowed(args: argparse.Namespace, version: AUDIT.Version) -> bool:
    if args.min_build is not None and version.build < args.min_build:
        return False
    if args.max_build is not None and version.build > args.max_build:
        return False
    return True


def descriptor_is_bad(descriptor: dict[str, Any]) -> bool:
    return (
        descriptor["requirement"] == "required" and
        descriptor["status"] not in {"inactive", "unique"}
    )


def audit_image(
    args: argparse.Namespace,
    repo: Path,
    symbol_path: Path,
    module: str,
    image: Path,
) -> tuple[bool, str]:
    version = AUDIT.image_version(image)
    if version is None:
        return False, f"FAIL {module} {image}: missing PE version"
    if not build_allowed(args, version):
        return True, ""

    label = f"{version.build}.{version.revision}"
    try:
        report = AUDIT.inspect(argparse.Namespace(
            repo=repo,
            architecture="legacy",
            module=module,
            version=label,
            image=image,
            symbol_path=symbol_path,
            dbghelp=args.dbghelp.resolve() if args.dbghelp else None,
            configuration=args.configuration,
            stable_id=None,
        ))
    except AUDIT.AuditError as error:
        ok = args.allow_missing_pdb and "pdb" in str(error).casefold()
        status = "WARN" if ok else "FAIL"
        return ok, f"{status} {module} {label}: {error}"

    if not report["module_supported"]:
        return True, f"SKIP {module} {label}: outside legacy module range"

    watched = set(WATCH_SYMBOLS[module])
    descriptors = [item for item in report["descriptors"] if item["id"] in watched]
    present = {item["id"] for item in descriptors}
    missing_ids = sorted(watched - present)
    active = [item for item in descriptors if item["status"] != "inactive"]
    bad = [item for item in active if descriptor_is_bad(item)]

    lines = [
        f"{'OK' if not missing_ids and not bad else 'FAIL'} {module} {label}: "
        f"active={len(active)}, bad={len(bad)}, evidence={report['evidence']}"
    ]
    for symbol_id in missing_ids:
        lines.append(f"  missing schema id: {symbol_id}")
    for item in descriptors:
        if item["status"] == "inactive" and not args.show_inactive:
            continue
        rvas = ", ".join(item["rvas"]) or "-"
        prefix = "  BAD" if item in bad else "  "
        lines.append(f"{prefix} {item['id']}: {item['status']} ({rvas})")
    return not missing_ids and not bad, "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    repo = args.repo.resolve()
    samples_root = resolved_under_repo(repo, args.samples_root)
    symbol_path = resolved_under_repo(repo, args.symbol_path)
    modules = selected_modules(args.module)
    images = iter_images(samples_root, modules)
    if not images:
        print(f"no DWM samples found below {samples_root}", file=sys.stderr)
        return 2

    ok = True
    emitted = False
    for module, image in images:
        item_ok, text = audit_image(args, repo, symbol_path, module, image)
        ok = ok and item_ok
        if text:
            emitted = True
            print(text)
    if not emitted:
        print("no samples matched the selected build filters", file=sys.stderr)
        return 2
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
