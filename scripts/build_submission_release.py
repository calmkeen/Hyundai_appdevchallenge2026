#!/usr/bin/env python3
"""Build a privately signed Pleos release. No install, model, or backend startup.

--init-signing creates a project-specific key once, then exits without building.
The private directory must be backed up securely to keep future updates possible.
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import secrets
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def initialize(properties: Path, java_home: Path) -> None:
    keystore = properties.parent / "carcue-release.jks"
    if properties.exists() and keystore.exists():
        print("Existing release key preserved; no files changed.")
        return
    if properties.exists() or keystore.exists():
        raise SystemExit("Incomplete signing directory; inspect privately before retrying.")
    properties.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    password = secrets.token_hex(32)
    key_password = secrets.token_hex(32)
    environment = os.environ.copy()
    environment.update(CARCUE_KEYTOOL_STORE_PASSWORD=password, CARCUE_KEYTOOL_KEY_PASSWORD=key_password)
    result = subprocess.run([
        str(java_home / "bin/keytool"), "-genkeypair", "-noprompt", "-storetype", "JKS",
        "-keystore", str(keystore), "-alias", "carcue-release", "-keyalg", "RSA", "-keysize", "3072",
        "-validity", "10000", "-dname", "CN=CarCue Release, O=CarCue, C=KR",
        "-storepass:env", "CARCUE_KEYTOOL_STORE_PASSWORD", "-keypass:env", "CARCUE_KEYTOOL_KEY_PASSWORD",
    ], env=environment, capture_output=True, text=True)
    if result.returncode:
        # Do not echo a keytool command or environment containing credentials.
        raise SystemExit("Release key generation failed; inspect the private signing directory.")
    keystore.chmod(0o600)
    descriptor = os.open(properties, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
        stream.write(f"storeFile={keystore}\nstorePassword={password}\nkeyAlias=carcue-release\nkeyPassword={key_password}\n")
    print("Created private project release key and properties (0600); no build or install performed.")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--init-signing", action="store_true", help="Create missing private key once, then exit")
    parser.add_argument("--signing-properties", type=Path,
                        default=Path(os.environ.get("CARCUE_RELEASE_SIGNING_PROPERTIES", ROOT / ".tooling/signing/carcue-release.properties")))
    parser.add_argument("--java-home", type=Path, default=Path(os.environ.get("JAVA_HOME", ROOT / ".tooling/jdk-17.0.21+9/Contents/Home")))
    parser.add_argument("--android-sdk", type=Path, default=Path(os.environ.get("ANDROID_HOME", ROOT / ".tooling/android-sdk")))
    parser.add_argument("--submission-avd", action="store_true", help="Explicit Pleos API34 AVD HTTP/stock-browser profile")
    parser.add_argument("--server-url", help="HTTPS backend; submission AVD defaults to http://10.0.2.2:8001")
    parser.add_argument("--checks", action="store_true", help="Also run Pleos release JVM tests and Android lint")
    parser.add_argument("--online", action="store_true", help="Allow Gradle dependency downloads for a fresh environment")
    args = parser.parse_args()
    properties = args.signing_properties.expanduser().resolve()
    java_home = args.java_home.expanduser().resolve()
    if args.init_signing:
        initialize(properties, java_home)
        return 0
    if not args.server_url and not args.submission_avd:
        parser.error("An explicit --server-url HTTPS endpoint or --submission-avd profile is required.")
    if not properties.is_file() and not all(os.environ.get(name) for name in (
        "CARCUE_RELEASE_STORE_FILE", "CARCUE_RELEASE_STORE_PASSWORD", "CARCUE_RELEASE_KEY_ALIAS", "CARCUE_RELEASE_KEY_PASSWORD"
    )):
        parser.error("Private release credentials required. Use --init-signing once or supply existing credentials.")
    environment = os.environ.copy()
    environment.update(JAVA_HOME=str(java_home), ANDROID_HOME=str(args.android_sdk.resolve()),
                       ANDROID_SDK_ROOT=str(args.android_sdk.resolve()))
    if properties.is_file():
        environment["CARCUE_RELEASE_SIGNING_PROPERTIES"] = str(properties)
    tasks = [":app:assemblePleosRelease"]
    if args.checks:
        tasks += [":app:testPleosReleaseUnitTest", ":app:lintPleosRelease"]
    command = [
        str(ROOT / "android/gradlew"), "-p", str(ROOT / "android"), *tasks,
        "-PpleosSdkVersion=2.3.2", f"-PcarcueServerUrl={args.server_url or 'http://10.0.2.2:8001'}",
        f"-PcarcueSubmissionAvd={str(args.submission_avd).lower()}",
        "-Dorg.gradle.jvmargs=-Xmx768m -XX:MaxMetaspaceSize=384m -Dfile.encoding=UTF-8",
        "-Pkotlin.compiler.execution.strategy=in-process", "--no-daemon", "--max-workers=1",
    ]
    if not args.online:
        command.append("--offline")
    return subprocess.call(command, env=environment)


if __name__ == "__main__":
    raise SystemExit(main())
