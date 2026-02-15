from pathlib import Path

from setuptools import setup


def read_requirements() -> list[str]:
    req_file = Path(__file__).with_name("requirements.txt")
    if not req_file.exists():
        return []
    lines = req_file.read_text(encoding="utf-8").splitlines()
    return [line.strip() for line in lines if line.strip() and not line.strip().startswith("#")]


setup(
    name="vtu-autodiary",
    version="0.1.0",
    description="Auto uploader for VTU internship diary entries",
    py_modules=[],
    install_requires=read_requirements(),
)
