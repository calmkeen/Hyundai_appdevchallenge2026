#!/usr/bin/env python3
"""Inspect the signed submission APK without keys, installation, AVD, or AI calls."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def inspect(apk, build_tools, environment):
    def tool(name, *arguments):
        return subprocess.run([str(build_tools / name), *map(str, arguments)], env=environment,
                              capture_output=True, text=True, errors="replace", check=True).stdout

    certificate = tool("apksigner", "verify", "--verbose", "--print-certs", apk)
    require("Android Debug" not in certificate, "Android debug signer is forbidden")
    signer = re.search(r"Signer #1 certificate SHA-256 digest: ([0-9a-f]+)", certificate)
    require(signer and len(signer[1]) == 64, "A verified signing certificate is required")
    badging = tool("aapt2", "dump", "badging", apk)
    require("application-debuggable" not in badging, "APK is debuggable")
    require("package: name='com.carcue.app' versionCode='2' versionName='0.1.1-rc1'" in badging,
            "Unexpected package/version")
    require("sdkVersion:'28'" in badging and "targetSdkVersion:'35'" in badging, "Unexpected SDK levels")
    require("android.hardware.type.automotive" in badging and "pleos.car.permission.CAR_DOORS" in badging,
            "Pleos automotive declarations are required")
    require("CONTROL_" not in badging, "Vehicle control permissions are forbidden")
    manifest = tool("aapt2", "dump", "xmltree", "--file", "AndroidManifest.xml", apk)
    require(re.search(r"android:debuggable[^\n]*=false", manifest), "Explicit debuggable=false required")
    require(re.search(r"android:usesCleartextTraffic[^\n]*=false", manifest), "Global cleartext must remain disabled")
    network_reference = re.search(r"android:networkSecurityConfig[^\n]*=@(0x[0-9a-f]+)", manifest)
    resources = tool("aapt2", "dump", "resources", apk)
    require(network_reference and re.search(re.escape(network_reference[1]) + r" xml/submission_network_security_config", resources),
            "Submission profile network config must be selected")
    network = tool("aapt2", "dump", "xmltree", "--file", "res/xml/submission_network_security_config.xml", apk)
    require(network.count("E: domain ") == 1 and '"10.0.2.2"' in network, "Only emulator-host domain may be excepted")
    require(re.search(r"E: base-config[^\n]*\n\s+A: cleartextTrafficPermitted=false", network), "Default cleartext denied")
    require(re.search(r"E: domain-config[^\n]*\n\s+A: cleartextTrafficPermitted=true", network), "Explicit host exception required")
    require("includeSubdomains=false" in network, "Subdomains must not be included")
    fields = {}
    sdk_defined = False
    with zipfile.ZipFile(apk) as archive, tempfile.TemporaryDirectory(prefix="carcue-apk-inspect-") as raw:
        names = archive.namelist()
        require(not any(name.endswith((".jks", ".keystore", ".sqlite", ".sqlite3", ".db", ".properties"))
                        or any(part.startswith(".env") for part in name.split("/")) for name in names),
                "Private key/database/config file found in APK")
        published = 0
        guide_files = sorted((ROOT / "content/guides").glob("*.json"))
        for guide in guide_files:
            bundled = archive.read("assets/guides/" + guide.name)
            require(bundled == guide.read_bytes(), "Bundled guide differs from checked-out content")
            if json.loads(bundled).get("lifecycle") == "PUBLISHED":
                published += 1
        require(published == 12, "Exactly 12 published bundled guides are required")
        for name in names:
            if not re.fullmatch(r"classes\d*\.dex", name):
                continue
            dex = Path(raw) / name
            dex.write_bytes(archive.read(name))
            dump = Path(raw) / "dexdump.txt"
            tool("dexdump", "-e", "-o", dump, dex)
            active = False
            field = None
            with dump.open(encoding="utf-8", errors="replace") as stream:
                for line in stream:
                    if line.startswith("Class #"):
                        active = False
                    if "Class descriptor  : 'Lai/pleos/playground/vehicle/Vehicle;'" in line:
                        sdk_defined = True
                    if "Class descriptor  : 'Lcom/carcue/app/BuildConfig;'" in line:
                        active = True
                    if active:
                        match = re.search(r"name\s+: '([^']+)'", line)
                        if match:
                            field = match[1]
                        match = re.search(r"value\s+: (.+)", line)
                        if match and field:
                            fields[field] = json.loads(match[1])
    expected = {"APPLICATION_ID": "com.carcue.app", "BUILD_TYPE": "release", "DEBUG": False,
                "FLAVOR": "pleos", "IS_MOCK": False, "SERVER_URL": "http://10.0.2.2:8001",
                "ALLOW_STOCK_AVD_BROWSER": True, "VERSION_CODE": 2, "VERSION_NAME": "0.1.1-rc1"}
    require(all(fields.get(key) == value for key, value in expected.items()), "Unexpected APK BuildConfig values")
    require(sdk_defined, "Actual Pleos Vehicle class definition is missing")
    return {"schema_version": 1, "passed": True, "apk_sha256": sha256(apk), "apk_bytes": apk.stat().st_size,
            "signer_certificate_sha256": signer[1], "package": "com.carcue.app", "version_code": 2,
            "version_name": "0.1.1-rc1", "min_sdk": 28, "target_sdk": 35,
            "debuggable": False, "build_config": fields, "pleos_vehicle_class_defined": sdk_defined,
            "bundled_published_guides": published, "private_files_found": False,
            "network_cleartext_default": False, "network_cleartext_hosts": ["10.0.2.2"],
            "installed": False, "avd_executed": False, "physical_vehicle_tested": False,
            "paid_ai_called": False, "model_called": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apk", type=Path, default=ROOT / "apk/CarCue_release.apk")
    parser.add_argument("--build-tools", type=Path,
                        default=Path(os.environ.get("ANDROID_HOME", ROOT / ".tooling/android-sdk")) / "build-tools/35.0.0")
    parser.add_argument("--java-home", type=Path)
    parser.add_argument("--manifest", type=Path, help="Optional recorded manifest to hash/certificate-check")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    environment = os.environ.copy()
    if args.java_home:
        environment["JAVA_HOME"] = str(args.java_home.resolve())
    result = inspect(args.apk.resolve(), args.build_tools.resolve(), environment)
    if args.manifest:
        recorded = json.loads(args.manifest.read_text())
        require(recorded["apk"]["sha256"] == result["apk_sha256"], "Manifest APK hash mismatch")
        require(recorded["apk"]["bytes"] == result["apk_bytes"], "Manifest APK size mismatch")
        require(recorded["apk"]["signer_certificate_sha256"] == result["signer_certificate_sha256"], "Manifest signer mismatch")
    serialized = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.write_text(serialized, encoding="utf-8")
    print(serialized, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
