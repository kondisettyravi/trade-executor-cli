"""Setup script for the Claude Trading Orchestrator."""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="claude-trading-orchestrator",
    version="1.0.0",
    author="Trading Systems",
    author_email="contact@tradingsystems.com",
    description="24/7 automated trading orchestrator using Claude CLI",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/tradingsystems/claude-trading-orchestrator",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Financial and Insurance Industry",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Office/Business :: Financial :: Investment",
    ],
    python_requires=">=3.9",
    install_requires=[
        "typer>=0.9.0",
        "rich>=13.7.0",
        "PyYAML>=6.0.1",
        "structlog>=23.2.0",
        "flask>=2.3.0",
        "requests>=2.25.0",
    ],
    entry_points={
        'console_scripts': [
            'claude-trader=src.cli.claude_cli:cli_main',
            'btc-check=btc_check:main',
        ],
    },
    include_package_data=True,
    package_data={
        "": ["*.yaml", "*.yml"],
    },
    zip_safe=False,
)
