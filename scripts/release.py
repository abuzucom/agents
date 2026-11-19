#!/usr/bin/env python3
"""Build and check the files of a tagged release.

The repository owner pushes a vX.Y.Z tag on a main commit.
.github/workflows/release.yml then runs these subcommands from the repository
root:

    python scripts/release.py check-tag v2.27.0
    python scripts/release.py build 2.27.0 <asset-folder>
    python scripts/release.py check-assets <asset-folder> 2.27.0
    python scripts/release.py checksums <asset-folder>
    python scripts/release.py notes 2.27.0 <output-file> --since v2.26.2

check-tag fails unless the tag equals "v" plus the top CHANGELOG.md version
and policy-digests.json holds an entry for that version.
build writes the adoptable policy, the shared gate archive, and the digest
entry of one version. Each build of one commit yields identical bytes. A
rerun of the release job therefore matches the files already on the draft.
check-assets fails unless a folder holds exactly the release files.
checksums writes SHA256SUMS.txt in the sha256sum format.
notes writes every changelog section newer than the previous stable release,
then a fixed adoption block. The repository owner chooses pre-release or
stable when publishing the draft. The notes therefore never name a channel.
"""
import argparse
import gzip
import hashlib
import importlib.util
import io
import json
import re
import stat
import sys
import tarfile
from pathlib import Path
from types import MappingProxyType, ModuleType

ROOT = Path(__file__).resolve().parent.parent
TAG_PREFIX = "v"
CHECKSUM_FILE = "SHA256SUMS.txt"
CHANGELOG_FILE = "CHANGELOG.md"
DIGEST_INDEX_FILE = "policy-digests.json"
SOURCE_REPOSITORY = "abuzucom/agents"
CHECK_FAILED = 1
JSON_INDENT = 2
# A bound on the tag list read from standard input. Tens of thousands of
# release tags fit well below it.
MAX_TAG_LIST_CHARACTERS = 1024 * 1024
ARCHIVE_EXECUTABLE_MODE = 0o755
ARCHIVE_FILE_MODE = 0o644
# Release files carry a zero timestamp and owner. Two builds of one commit
# then produce identical archive bytes.
ARCHIVE_TIMESTAMP = 0
# The permissions of the release job, the only job that writes. The
# workflow test compares release.yml against this mapping. The proxy keeps a
# caller from widening the expected set in place.
RELEASE_JOB_PERMISSIONS = MappingProxyType({
    "contents": "write",
    "id-token": "write",
    "attestations": "write",
    "artifact-metadata": "write",
})
# Three decimal parts without leading zeros and without a suffix. Every
# part is one bounded token. The pattern holds no nested quantifier.
VERSION_PATTERN = re.compile(r"(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)")
CHANGELOG_HEADING = re.compile(r"^## \[([0-9.]+)\]", re.MULTILINE)
ADOPTION_NOTES = """\
## Adopting this release

- Pin the commit this tag names. Write the full commit SHA and put
  `# v{version}` beside it.
- `{policy}` holds the adoptable policy. It equals the output of
  `python scripts/sync.py --print-adoptable` at this commit.
- `{archive}` holds the shared gate files and `shared-files.json`.
- `{digests}` holds the SHA-256 digests recorded for this version.
- Check each file against `SHA256SUMS.txt`.
- Verify the build provenance of a file with
  `gh attestation verify <file> --repo {repository} --signer-workflow {repository}/.github/workflows/release.yml`.
- A pre-release marks a development build. Adopt a stable release for
  normal use.
"""


def _load_sync() -> ModuleType:
    """Load sync.py by fixed sibling path, never through sys.path."""
    path = Path(__file__).resolve().parent / "sync.py"
    if path.is_symlink() or not path.is_file():
        raise ImportError("trusted sibling sync.py is missing or not a regular file")
    spec = importlib.util.spec_from_file_location("_release_sync", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


SYNC = _load_sync()


def parse_version(text: str) -> tuple[int, int, int]:
    """Return the three integer parts of an X.Y.Z version.

    A suffix, a leading zero, or any other shape raises ValueError.
    """
    match = VERSION_PATTERN.fullmatch(text)
    if match is None:
        raise ValueError(f"{text!r} is not a version in X.Y.Z form without a suffix.")
    major, minor, patch = (int(part) for part in match.groups())
    return major, minor, patch


def strip_tag_prefix(text: str) -> str:
    """Return a version from either a vX.Y.Z tag or a plain X.Y.Z version."""
    return text.removeprefix(TAG_PREFIX)


def _parse_stable_tag(tag: str):
    """Return the version parts of a vX.Y.Z tag, or None for another name."""
    if not tag.startswith(TAG_PREFIX):
        return None
    try:
        return parse_version(strip_tag_prefix(tag))
    except ValueError:
        return None


def select_latest_stable(tags: list[str]) -> str:
    """Return the vX.Y.Z tag with the highest version, or an empty string.

    GitHub lists releases by creation time. A stable release published
    after a newer one would otherwise become the notes floor.
    """
    parsed = [(_parse_stable_tag(tag), tag) for tag in tags]
    versions = [(parts, tag) for parts, tag in parsed if parts is not None]
    return max(versions)[1] if versions else ""


def asset_names(version: str) -> tuple[str, str, str]:
    """Return the policy, gate archive, and digest file names of a version."""
    return (f"agents-policy-{version}.md",
            f"agents-gate-set-{version}.tar.gz",
            f"agents-digests-{version}.json")


def bundle_name(version: str) -> str:
    """Return the Sigstore bundle name that attests the release files."""
    return f"agents-{version}.sigstore.json"


def _changelog_problem(version: str, root: Path) -> str | None:
    """Return why the top changelog version differs from the tag, if it does."""
    path = root / CHANGELOG_FILE
    if not path.is_file():
        return f"{CHANGELOG_FILE} is missing from the checkout."
    heading = SYNC.read_release_version(path.read_text(encoding="utf-8"))
    if heading != version:
        return (f"{CHANGELOG_FILE} names version {heading!r} at the top, "
                f"but the tag names {version!r}.")
    return None


def _digest_problem(version: str, root: Path) -> str | None:
    """Return why the digest index lacks the tag version, if it does."""
    if not (root / DIGEST_INDEX_FILE).is_file():
        return f"{DIGEST_INDEX_FILE} is missing from the checkout."
    versions = SYNC.read_digest_index(root)
    if versions is None:
        return f"{DIGEST_INDEX_FILE} is unreadable. Restore it from version control."
    if version not in versions:
        return (f"{DIGEST_INDEX_FILE} has no entry for version {version}. "
                "Run python scripts/sync.py on the release commit.")
    return None


def tag_problems(tag: str, root: Path) -> list[str]:
    """Return one line per reason the tag cannot release this checkout."""
    if not tag.startswith(TAG_PREFIX):
        return [f"Tag {tag!r} does not start with {TAG_PREFIX!r}."]
    version = strip_tag_prefix(tag)
    try:
        parse_version(version)
    except ValueError:
        return [f"Tag {tag!r} must name a version in X.Y.Z form without a suffix."]
    problems = (_changelog_problem(version, root), _digest_problem(version, root))
    return [problem for problem in problems if problem is not None]


def _list_heading_blocks(changelog: str) -> list[tuple[str, str]]:
    """Return each changelog version with its section text, newest first."""
    headings = list(CHANGELOG_HEADING.finditer(changelog))
    ends = [heading.start() for heading in headings[1:]] + [len(changelog)]
    return [(heading.group(1), changelog[heading.start():end].strip())
            for heading, end in zip(headings, ends)]


def _is_selected(key: tuple, target: tuple, floor: tuple | None) -> bool:
    """Return whether a section version belongs in the release notes."""
    if floor is None:
        return key == target
    return floor < key <= target


def changelog_sections(changelog: str, version: str, since: str | None) -> str:
    """Return the changelog sections of a release, newest first.

    Without a previous stable version, only the release's own section
    appears. With one, every section newer than it and not newer than the
    release appears. The comparison uses version numbers. A same-day merge
    can rename the previous stable heading. The comparison then still finds
    every newer section.
    """
    target = parse_version(version)
    floor = parse_version(since) if since is not None else None
    if floor is not None and floor >= target:
        raise ValueError(f"Previous stable version {since} is not older than {version}.")
    blocks = _list_heading_blocks(changelog)
    if version not in (name for name, _ in blocks):
        raise ValueError(f"{CHANGELOG_FILE} has no section for version {version}.")
    selected = [text for name, text in blocks
                if _is_selected(parse_version(name), target, floor)]
    return "\n\n".join(selected) + "\n"


def release_notes(root: Path, version: str, since: str | None) -> str:
    """Return the changelog sections followed by the adoption block."""
    changelog = (root / CHANGELOG_FILE).read_text(encoding="utf-8")
    policy, archive, digests = asset_names(version)
    adoption = ADOPTION_NOTES.format(
        version=version, policy=policy, archive=archive, digests=digests,
        repository=SOURCE_REPOSITORY)
    return f"{changelog_sections(changelog, version, since)}\n{adoption}"


def _archive_member(root: Path, name: str) -> tuple[tarfile.TarInfo, bytes]:
    """Return a normalized archive header and the bytes of one file."""
    path = root / name
    content = path.read_bytes()
    info = tarfile.TarInfo(name)
    info.size = len(content)
    executable = path.stat().st_mode & stat.S_IXUSR
    info.mode = ARCHIVE_EXECUTABLE_MODE if executable else ARCHIVE_FILE_MODE
    info.mtime = ARCHIVE_TIMESTAMP
    return info, content


def _build_tar_bytes(root: Path, names: list[str]) -> bytes:
    """Return an uncompressed tar of the named files in the given order."""
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w", format=tarfile.USTAR_FORMAT) as archive:
        for name in names:
            info, content = _archive_member(root, name)
            archive.addfile(info, io.BytesIO(content))
    return buffer.getvalue()


def write_gate_archive(root: Path, output: Path) -> None:
    """Write the shared gate files and the shared manifest as a stable tar.gz."""
    names = sorted(SYNC.SHARED_FILES + [SYNC.SHARED_MANIFEST])
    tar_bytes = _build_tar_bytes(root, names)
    with output.open("wb") as handle:
        with gzip.GzipFile(filename="", mode="wb", fileobj=handle,
                           mtime=ARCHIVE_TIMESTAMP) as compressed:
            compressed.write(tar_bytes)


def _require_empty_folder(folder: Path) -> None:
    """Create the asset folder, or fail when it already holds entries."""
    if folder.exists() and not folder.is_dir():
        raise ValueError(f"{folder} is not a folder. Pass a new or empty folder.")
    if folder.exists() and any(folder.iterdir()):
        raise ValueError(f"{folder} is not empty. Pass a new or empty folder.")
    folder.mkdir(parents=True, exist_ok=True)


def build_assets(root: Path, version: str, folder: Path) -> list[Path]:
    """Write the three release files of a version and return the file paths."""
    parse_version(version)
    versions = SYNC.read_digest_index(root)
    if versions is None or version not in versions:
        raise ValueError(f"{DIGEST_INDEX_FILE} has no entry for version {version}.")
    _require_empty_folder(folder)
    policy, archive, digests = (folder / name for name in asset_names(version))
    adoptable = SYNC.adoptable_content(SYNC.policy_bytes(root).decode("ascii"))
    policy.write_bytes(adoptable.encode("ascii"))
    write_gate_archive(root, archive)
    entry = {"version": version, **versions[version]}
    digests.write_bytes(
        (json.dumps(entry, indent=JSON_INDENT, sort_keys=True) + "\n").encode("ascii"))
    return [policy, archive, digests]


def asset_problems(folder: Path, version: str, require_bundle: bool = False) -> list[str]:
    """Return one line per missing release file and per extra entry."""
    expected = set(asset_names(version))
    if require_bundle:
        expected.add(bundle_name(version))
    present = {path.name for path in folder.iterdir()}
    missing = [f"{name} is missing." for name in sorted(expected.difference(present))]
    extra = [f"{name} is not a release file of version {version}."
             for name in sorted(present.difference(expected))]
    return missing + extra


def file_sha256(path: Path) -> str:
    """Return the SHA-256 hex digest of one file."""
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def write_checksums(folder: Path) -> Path:
    """Write SHA256SUMS.txt for every other file in the folder."""
    files = sorted(path for path in folder.iterdir()
                   if path.is_file() and path.name != CHECKSUM_FILE)
    output = folder / CHECKSUM_FILE
    output.write_bytes("".join(
        f"{file_sha256(path)}  {path.name}\n" for path in files).encode("ascii"))
    return output


def _run_check_tag(arguments: argparse.Namespace, root: Path) -> int:
    """Print each tag problem and return a blocking status."""
    problems = tag_problems(arguments.tag, root)
    for problem in problems:
        print(f"release: {problem}")
    if problems:
        print("release: align the tag with CHANGELOG.md and policy-digests.json, "
              "then push a new tag.")
        return CHECK_FAILED
    print(f"release: tag {arguments.tag} matches the changelog and digest index.")
    return 0


def _run_build(arguments: argparse.Namespace, root: Path) -> int:
    """Build the release files and report the folder."""
    try:
        build_assets(root, arguments.version, arguments.folder)
    except ValueError as error:
        print(f"release: {error}")
        return CHECK_FAILED
    print(f"release: wrote the release files to {arguments.folder}")
    return 0


def _run_check_assets(arguments: argparse.Namespace, root: Path) -> int:
    """Print each asset problem and return a blocking status."""
    problems = asset_problems(arguments.folder, arguments.version,
                              require_bundle=arguments.require_bundle)
    for problem in problems:
        print(f"release: {problem}")
    if problems:
        print("release: rebuild the release files for this tag, then rerun the job.")
        return CHECK_FAILED
    print(f"release: {arguments.folder} holds the release files of {arguments.version}.")
    return 0


def _run_checksums(arguments: argparse.Namespace, root: Path) -> int:
    """Write the checksum file and report its path."""
    print(f"release: wrote {write_checksums(arguments.folder)}")
    return 0


def _run_notes(arguments: argparse.Namespace, root: Path) -> int:
    """Write the release notes, or report why the inputs yield no notes."""
    since = strip_tag_prefix(arguments.since) if arguments.since else None
    try:
        notes = release_notes(root, arguments.version, since)
    except ValueError as error:
        print(f"release: {error} Pass the previous stable tag, or omit --since.")
        return CHECK_FAILED
    arguments.output.write_bytes(notes.encode("utf-8"))
    print(f"release: wrote {arguments.output}")
    return 0


def _run_latest_stable(arguments: argparse.Namespace, root: Path) -> int:
    """Print the highest vX.Y.Z tag named on standard input, if any."""
    text = sys.stdin.read(MAX_TAG_LIST_CHARACTERS + 1)
    if len(text) > MAX_TAG_LIST_CHARACTERS:
        print("release: the tag list exceeds the size limit. Check the release list.",
              file=sys.stderr)
        return CHECK_FAILED
    latest = select_latest_stable([line.strip() for line in text.splitlines()])
    if latest:
        print(latest)
    return 0


def _build_parser() -> argparse.ArgumentParser:
    """Return the argument parser with one subparser per subcommand."""
    parser = argparse.ArgumentParser(description="Release helpers for release.yml.")
    commands = parser.add_subparsers(dest="command", required=True)
    check = commands.add_parser("check-tag", help="Check a tag against the version sources.")
    check.add_argument("tag")
    build = commands.add_parser("build", help="Write the release files of a version.")
    build.add_argument("version")
    build.add_argument("folder", type=Path)
    assets = commands.add_parser("check-assets", help="Check the release file names.")
    assets.add_argument("folder", type=Path)
    assets.add_argument("version")
    assets.add_argument("--require-bundle", action="store_true",
                        help="Require the Sigstore bundle beside the release files.")
    sums = commands.add_parser("checksums", help="Write SHA256SUMS.txt for a folder.")
    sums.add_argument("folder", type=Path)
    notes = commands.add_parser("notes", help="Write the release notes of a version.")
    notes.add_argument("version")
    notes.add_argument("output", type=Path)
    notes.add_argument("--since", help="The previous stable tag or version.")
    commands.add_parser("latest-stable",
                        help="Print the highest vX.Y.Z tag read from standard input.")
    return parser


HANDLERS = {
    "check-tag": _run_check_tag,
    "build": _run_build,
    "check-assets": _run_check_assets,
    "checksums": _run_checksums,
    "notes": _run_notes,
    "latest-stable": _run_latest_stable,
}


def main(argv: list[str] | None = None, root: Path = ROOT) -> int:
    """Run one subcommand and return 0 on success or 1 on a failed check."""
    parser = _build_parser()
    arguments = parser.parse_args(argv)
    folder = getattr(arguments, "folder", None)
    if arguments.command in ("check-assets", "checksums") and not folder.is_dir():
        parser.error(f"{folder} is not a folder. Pass the folder of release files.")
    return HANDLERS[arguments.command](arguments, root)


if __name__ == "__main__":
    sys.exit(main())
