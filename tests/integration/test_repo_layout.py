from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_foundational_files_exist() -> None:
    expected = [
        ROOT / "docker-compose.yml",
        ROOT / "pyproject.toml",
        ROOT / "README.md",
        ROOT / "docs" / "architecture" / "overview.md",
        ROOT / "infra" / "kafka" / "create-topics.sh",
        ROOT / "infra" / "postgres" / "alembic" / "versions" / "20260420_0001_phase1_foundation.py",
    ]
    for path in expected:
        assert path.exists(), f"missing expected path: {path}"
