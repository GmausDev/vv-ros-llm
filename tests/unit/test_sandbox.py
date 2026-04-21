from __future__ import annotations
import pytest
from unittest.mock import MagicMock
from vv_ros_llm.vv.sandbox import DockerSandbox, DockerSandboxConfig, ImageMissing

@pytest.fixture
def mock_client(monkeypatch):
    client = MagicMock()
    monkeypatch.setattr("docker.from_env", lambda: client)
    return client

@pytest.mark.asyncio
async def test_ensure_image_ok(mock_client):
    mock_client.images.get.return_value = MagicMock()
    sb = DockerSandbox(DockerSandboxConfig(image="img:t"))
    await sb.ensure_image()

@pytest.mark.asyncio
async def test_ensure_image_missing(mock_client):
    from docker.errors import ImageNotFound
    mock_client.images.get.side_effect = ImageNotFound("no")
    sb = DockerSandbox(DockerSandboxConfig(image="img:t"))
    with pytest.raises(ImageMissing):
        await sb.ensure_image()

@pytest.mark.asyncio
async def test_run_command_happy_path(mock_client, tmp_path):
    container = MagicMock()
    container.wait.return_value = {"StatusCode": 0}
    container.logs.side_effect = [b"hello\n", b""]
    mock_client.containers.run.return_value = container
    sb = DockerSandbox(DockerSandboxConfig(image="img:t", timeout=1))
    res = await sb.run_command(["echo", "hi"], workspace=tmp_path)
    assert res.status == "OK" and "hello" in res.stdout


@pytest.mark.asyncio
async def test_sandbox_reap_leftover(mock_client):
    container1, container2 = MagicMock(), MagicMock()
    mock_client.containers.list.return_value = [container1, container2]
    sb = DockerSandbox(DockerSandboxConfig(image="img:t"))
    n = await sb.reap_leftover()
    assert n == 2
    container1.remove.assert_called_with(force=True)
    container2.remove.assert_called_with(force=True)


@pytest.mark.asyncio
async def test_sandbox_reap_leftover_handles_list_error(mock_client):
    mock_client.containers.list.side_effect = Exception("boom")
    sb = DockerSandbox(DockerSandboxConfig(image="img:t"))
    n = await sb.reap_leftover()
    assert n == 0


def test_sandbox_close_silent_on_client_error(mock_client):
    mock_client.close.side_effect = Exception("nope")
    sb = DockerSandbox(DockerSandboxConfig(image="img:t"))
    sb.close()


@pytest.mark.asyncio
async def test_run_command_truncates_large_logs(mock_client, tmp_path):
    big = b"x" * 3_000_000
    container = MagicMock()
    container.wait.return_value = {"StatusCode": 0}
    container.logs.side_effect = [big, b""]
    mock_client.containers.run.return_value = container
    sb = DockerSandbox(DockerSandboxConfig(image="img:t", timeout=1))
    res = await sb.run_command(["echo"], workspace=tmp_path)
    assert len(res.stdout.encode("utf-8", errors="ignore")) <= 2_000_000 + 64


@pytest.mark.asyncio
async def test_run_command_timeout_path(mock_client, tmp_path):
    container = MagicMock()
    container.wait.side_effect = Exception("timeout")
    container.logs.side_effect = [b"", b"boom"]
    mock_client.containers.run.return_value = container
    sb = DockerSandbox(DockerSandboxConfig(image="img:t", timeout=1))
    res = await sb.run_command(["sleep", "100"], workspace=tmp_path)
    assert res.status == "TIMEOUT" and res.timed_out
