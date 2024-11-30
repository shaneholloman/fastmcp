import json
from fastmcp import FastMCP
import pytest
from pathlib import Path


@pytest.fixture()
def test_dir(tmp_path_factory) -> Path:
    """Create a temporary directory with test files."""
    tmp = tmp_path_factory.mktemp("test_files")

    # Create test files
    (tmp / "example.py").write_text("print('hello world')")
    (tmp / "readme.md").write_text("# Test Directory\nThis is a test.")
    (tmp / "config.json").write_text('{"test": true}')

    return tmp


@pytest.fixture
def mcp() -> FastMCP:
    mcp = FastMCP()

    return mcp


@pytest.fixture(autouse=True)
def resources(mcp: FastMCP, test_dir: Path) -> None:
    @mcp.resource("dir://test_dir")
    def list_test_dir() -> list[str]:
        """List the files in the test directory"""
        return [str(f) for f in test_dir.iterdir()]

    @mcp.resource("file://test_dir/example.py")
    def read_example_py() -> str:
        """Read the example.py file"""
        try:
            return (test_dir / "example.py").read_text()
        except FileNotFoundError:
            return "File not found"

    @mcp.resource("file://test_dir/readme.md")
    def read_readme_md() -> str:
        """Read the readme.md file"""
        try:
            return (test_dir / "readme.md").read_text()
        except FileNotFoundError:
            return "File not found"

    @mcp.resource("file://test_dir/config.json")
    def read_config_json() -> str:
        """Read the config.json file"""
        try:
            return (test_dir / "config.json").read_text()
        except FileNotFoundError:
            return "File not found"

    return mcp


@pytest.fixture(autouse=True)
def tools(mcp: FastMCP, test_dir: Path) -> None:
    @mcp.tool()
    def delete_file(path: str) -> bool:
        # ensure path is in test_dir
        if Path(path).resolve().parent != test_dir:
            raise ValueError(f"Path must be in test_dir: {path}")
        Path(path).unlink()
        return True


async def test_list_resources(mcp: FastMCP):
    resources = await mcp.list_resources()
    assert len(resources) == 4

    assert [str(r.uri) for r in resources] == [
        "dir://test_dir",
        "file://test_dir/example.py",
        "file://test_dir/readme.md",
        "file://test_dir/config.json",
    ]


async def test_read_resource_dir(mcp: FastMCP):
    files = await mcp.read_resource("dir://test_dir")
    files = json.loads(files)

    assert sorted([Path(f).name for f in files]) == [
        "config.json",
        "example.py",
        "readme.md",
    ]


async def test_read_resource_file(mcp: FastMCP):
    result = await mcp.read_resource("file://test_dir/example.py")
    assert result == "print('hello world')"


async def test_delete_file(mcp: FastMCP, test_dir: Path):
    await mcp.call_tool(
        "delete_file", arguments=dict(path=str(test_dir / "example.py"))
    )
    assert not (test_dir / "example.py").exists()


async def test_delete_file_and_check_resources(mcp: FastMCP, test_dir: Path):
    await mcp.call_tool(
        "delete_file", arguments=dict(path=str(test_dir / "example.py"))
    )
    result = await mcp.read_resource("file://test_dir/example.py")
    assert result == "File not found"