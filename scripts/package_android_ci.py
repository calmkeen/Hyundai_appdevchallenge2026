"""Label CI APKs only after checking the actual package/flavor metadata.

This does not install or run an APK, a vehicle SDK, a backend or an AI provider.
"""
import argparse
import hashlib
import json
import re
import shutil
import subprocess
from pathlib import Path


def verify_badging(text: str, variant: str) -> dict:
    package_line = next((line for line in text.splitlines() if line.startswith("package: ")), "")
    attributes = dict(re.findall(r"([A-Za-z]+)='([^']*)'", package_line))
    expected = "com.carcue.app.demo" if variant == "demo" else "com.carcue.app"
    if attributes.get("name") != expected:
        raise ValueError("APK_PACKAGE_DOES_NOT_MATCH_CI_VARIANT")
    version = attributes.get("versionName", "")
    if not version or version.endswith("-mock") != (variant == "demo"):
        raise ValueError("APK_MOCK_VERSION_LABEL_MISMATCH")
    sdk = re.search(r"^targetSdkVersion:'(\d+)'$", text, re.MULTILINE)
    if sdk is None or sdk.group(1) != "35":
        raise ValueError("APK_TARGET_SDK_35_REQUIRED")
    if attributes.get("compileSdkVersion") != "35":
        raise ValueError("APK_COMPILE_SDK_35_REQUIRED")
    return {"package": expected, "version_name": version, "target_sdk": 35}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--variant", choices=("demo", "pleos"), required=True)
    parser.add_argument("--apk", type=Path, required=True)
    parser.add_argument("--aapt2", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--commit", required=True)
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    if re.fullmatch(r"[a-f0-9]{40}", args.commit) is None or not args.run_id.isdigit():
        raise ValueError("GITHUB_PROVENANCE_REQUIRED")
    result = subprocess.run([str(args.aapt2), "dump", "badging", str(args.apk)],
                            check=True, capture_output=True, text=True, timeout=30)
    metadata = verify_badging(result.stdout, args.variant)
    label = "MOCK" if args.variant == "demo" else "COMPILE_ONLY"
    filename = f"carcue-{args.variant}-{label}-debug.apk"
    args.output_dir.mkdir(parents=True, exist_ok=False)
    target = args.output_dir / filename
    shutil.copyfile(args.apk, target)
    checksum = hashlib.sha256(target.read_bytes()).hexdigest()
    metadata.update({
        "schema_version": 1, "variant": args.variant, "artifact_label": label,
        "apk": filename, "sha256": checksum, "source_commit": args.commit,
        "github_run_id": args.run_id, "java_major": 17, "gradle_version": "8.10.2",
        "compile_sdk": 35, "build_tools": "35.0.0",
        "vehicle_mode": "MOCK" if args.variant == "demo" else "PLEOS",
        "validation_scope": "DEMO_JVM_TESTS_AND_APK_BUILD" if args.variant == "demo"
                            else "PLEOS_APK_COMPILE_ONLY",
        "runtime_validation_performed": False, "sdk_vehicle_readings_verified": False,
        "ai_validation_performed": False, "physical_vehicle_tested": False,
        "backend_url": "http://10.0.2.2:8000", "backend_started_by_ci": False,
    })
    (args.output_dir / "artifact.json").write_text(json.dumps(metadata, indent=2) + "\n")
    (args.output_dir / "SHA256SUMS.txt").write_text(f"{checksum}  {filename}\n")
    print(json.dumps(metadata, indent=2))


if __name__ == "__main__":
    main()
