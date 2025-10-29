"""
Tests for cleanup tasks.
"""

import os
import tempfile
from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock, patch

import pytest

from app.tasks.cleanup_tasks import (
    _cleanup_download_files,
    _cleanup_temp_files,
    cleanup_temp_files,
)


class TestCleanupTempFiles:
    """Test suite for temporary file cleanup."""

    @pytest.mark.asyncio
    async def test_cleanup_temp_files_basic(self):
        """Test basic temp file cleanup."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create old and new files
            old_file = os.path.join(tmpdir, "old_file.tmp")
            new_file = os.path.join(tmpdir, "new_file.tmp")

            # Create old file (modify time to 25 hours ago)
            with open(old_file, "w") as f:
                f.write("old content" * 100)

            old_time = datetime.now(timezone.utc).timestamp() - (
                25 * 3600
            )  # 25 hours ago
            os.utime(old_file, (old_time, old_time))

            # Create new file (modify time to 1 hour ago)
            with open(new_file, "w") as f:
                f.write("new content" * 100)

            new_time = datetime.now(timezone.utc).timestamp() - 3600  # 1 hour ago
            os.utime(new_file, (new_time, new_time))

            old_file_size = os.path.getsize(old_file)

            # Mock the environment variable to point to our temp dir
            with patch.dict(os.environ, {"HERMES_TEMP_DIR": tmpdir}):
                result = await _cleanup_temp_files(max_age_hours=24)

            # Old file should be deleted, new file should remain
            assert result["deleted_files"] == 1
            assert result["total_freed_bytes"] == old_file_size
            assert not os.path.exists(old_file)
            assert os.path.exists(new_file)

    @pytest.mark.asyncio
    async def test_cleanup_temp_files_no_directory(self):
        """Test cleanup when temp directory doesn't exist."""
        with patch.dict(os.environ, {"HERMES_TEMP_DIR": "/nonexistent/directory"}):
            result = await _cleanup_temp_files(max_age_hours=24)

        assert result["deleted_files"] == 0
        assert result["total_freed_bytes"] == 0

    @pytest.mark.asyncio
    async def test_cleanup_temp_files_empty_directory(self):
        """Test cleanup with empty temp directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.dict(os.environ, {"HERMES_TEMP_DIR": tmpdir}):
                result = await _cleanup_temp_files(max_age_hours=24)

            assert result["deleted_files"] == 0
            assert result["total_freed_bytes"] == 0

    @pytest.mark.asyncio
    async def test_cleanup_temp_files_all_new_files(self):
        """Test cleanup when all files are newer than cutoff."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create only new files
            for i in range(3):
                file_path = os.path.join(tmpdir, f"new_file{i}.tmp")
                with open(file_path, "w") as f:
                    f.write(f"content {i}" * 100)

                # Set modification time to 1 hour ago
                new_time = datetime.now(timezone.utc).timestamp() - 3600
                os.utime(file_path, (new_time, new_time))

            with patch.dict(os.environ, {"HERMES_TEMP_DIR": tmpdir}):
                result = await _cleanup_temp_files(max_age_hours=24)

            # No files should be deleted
            assert result["deleted_files"] == 0
            assert result["total_freed_bytes"] == 0
            assert len(os.listdir(tmpdir)) == 3

    @pytest.mark.asyncio
    async def test_cleanup_temp_files_different_cutoff(self):
        """Test cleanup with different age cutoff."""
        with tempfile.TemporaryDirectory() as tmpdir:
            old_file = os.path.join(tmpdir, "old_file.tmp")

            with open(old_file, "w") as f:
                f.write("content" * 100)

            # Set modification time to 2 hours ago
            old_time = datetime.now(timezone.utc).timestamp() - (2 * 3600)
            os.utime(old_file, (old_time, old_time))

            file_size = os.path.getsize(old_file)

            # Cleanup files older than 1 hour
            with patch.dict(os.environ, {"HERMES_TEMP_DIR": tmpdir}):
                result = await _cleanup_temp_files(max_age_hours=1)

            assert result["deleted_files"] == 1
            assert result["total_freed_bytes"] == file_size
            assert not os.path.exists(old_file)

    def test_cleanup_temp_files_sync_wrapper(self):
        """Test the synchronous wrapper function."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = os.path.join(tmpdir, "test.tmp")
            with open(test_file, "w") as f:
                f.write("test" * 100)

            # Set old modification time
            old_time = datetime.now(timezone.utc).timestamp() - (25 * 3600)
            os.utime(test_file, (old_time, old_time))

            with patch.dict(os.environ, {"HERMES_TEMP_DIR": tmpdir}):
                result = cleanup_temp_files(max_age_hours=24)

            assert result["deleted_files"] == 1
            assert result["total_freed_bytes"] > 0
            assert not os.path.exists(test_file)


class TestCleanupDownloadFiles:
    """Test suite for download file cleanup."""

    @pytest.mark.asyncio
    async def test_cleanup_download_files_success(self):
        """Test successful cleanup of download files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test files
            test_file1 = os.path.join(tmpdir, "video1.mp4")
            test_file2 = os.path.join(tmpdir, "video2.mp4")

            with open(test_file1, "w") as f:
                f.write("video content 1" * 1000)
            with open(test_file2, "w") as f:
                f.write("video content 2" * 1000)

            file_size1 = os.path.getsize(test_file1)
            file_size2 = os.path.getsize(test_file2)

            # Mock file info objects
            mock_file1 = Mock()
            mock_file1.filepath = test_file1
            mock_file2 = Mock()
            mock_file2.filepath = test_file2

            # Mock the async session and repositories
            with patch(
                "app.tasks.cleanup_tasks.async_session_maker"
            ) as mock_session_maker:
                mock_session = AsyncMock()
                mock_session.__aenter__ = AsyncMock(return_value=mock_session)
                mock_session.__aexit__ = AsyncMock()
                mock_session_maker.return_value = mock_session

                # Mock repository
                mock_repo = AsyncMock()
                mock_repo.get_by_download_id = AsyncMock(
                    return_value=[mock_file1, mock_file2]
                )

                with patch(
                    "app.tasks.cleanup_tasks.DownloadFileRepository",
                    return_value=mock_repo,
                ):
                    result = await _cleanup_download_files(["test-download-123"])

            assert result["deleted_files"] == 2
            assert result["failed_files"] == 0
            assert result["total_freed_bytes"] == file_size1 + file_size2
            assert not os.path.exists(test_file1)
            assert not os.path.exists(test_file2)

    @pytest.mark.asyncio
    async def test_cleanup_download_files_missing_file(self):
        """Test cleanup handles missing files gracefully."""
        # Mock file info for non-existent file
        mock_file = Mock()
        mock_file.filepath = "/nonexistent/path/video.mp4"

        with patch("app.tasks.cleanup_tasks.async_session_maker") as mock_session_maker:
            mock_session = AsyncMock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock()
            mock_session_maker.return_value = mock_session

            mock_repo = AsyncMock()
            mock_repo.get_by_download_id = AsyncMock(return_value=[mock_file])

            with patch(
                "app.tasks.cleanup_tasks.DownloadFileRepository", return_value=mock_repo
            ):
                result = await _cleanup_download_files(["test-download-123"])

        # Should not crash, just skip the missing file
        assert result["deleted_files"] == 0
        assert result["total_freed_bytes"] == 0
        assert result["failed_files"] == 0

    @pytest.mark.asyncio
    async def test_cleanup_download_files_empty_list(self):
        """Test cleanup with empty download ID list."""
        with patch("app.tasks.cleanup_tasks.async_session_maker") as mock_session_maker:
            mock_session = AsyncMock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock()
            mock_session_maker.return_value = mock_session

            result = await _cleanup_download_files([])

        assert result["deleted_files"] == 0
        assert result["failed_files"] == 0
        assert result["total_freed_bytes"] == 0

    @pytest.mark.asyncio
    async def test_cleanup_download_files_repository_error(self):
        """Test cleanup handles repository errors."""
        with patch("app.tasks.cleanup_tasks.async_session_maker") as mock_session_maker:
            mock_session = AsyncMock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock()
            mock_session_maker.return_value = mock_session

            mock_repo = AsyncMock()
            mock_repo.get_by_download_id = AsyncMock(
                side_effect=Exception("Database connection error")
            )

            with patch(
                "app.tasks.cleanup_tasks.DownloadFileRepository", return_value=mock_repo
            ):
                result = await _cleanup_download_files(["test-download-123"])

        # Should handle error and report it
        assert result["failed_files"] == 1
        assert "test-download-123" in result["failed_downloads"]

    @pytest.mark.asyncio
    async def test_cleanup_download_files_multiple_downloads(self):
        """Test cleanup of files from multiple downloads."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create files for two downloads
            file1 = os.path.join(tmpdir, "download1_video.mp4")
            file2 = os.path.join(tmpdir, "download2_video.mp4")

            with open(file1, "w") as f:
                f.write("content1" * 500)
            with open(file2, "w") as f:
                f.write("content2" * 500)

            total_size = os.path.getsize(file1) + os.path.getsize(file2)

            mock_file1 = Mock()
            mock_file1.filepath = file1
            mock_file2 = Mock()
            mock_file2.filepath = file2

            with patch(
                "app.tasks.cleanup_tasks.async_session_maker"
            ) as mock_session_maker:
                mock_session = AsyncMock()
                mock_session.__aenter__ = AsyncMock(return_value=mock_session)
                mock_session.__aexit__ = AsyncMock()
                mock_session_maker.return_value = mock_session

                mock_repo = AsyncMock()

                # Different files for different downloads
                async def get_files_side_effect(download_id):
                    if download_id == "download-1":
                        return [mock_file1]
                    elif download_id == "download-2":
                        return [mock_file2]
                    return []

                mock_repo.get_by_download_id = AsyncMock(
                    side_effect=get_files_side_effect
                )

                with patch(
                    "app.tasks.cleanup_tasks.DownloadFileRepository",
                    return_value=mock_repo,
                ):
                    result = await _cleanup_download_files(["download-1", "download-2"])

            assert result["deleted_files"] == 2
            assert result["failed_files"] == 0
            assert result["total_freed_bytes"] == total_size
            assert not os.path.exists(file1)
            assert not os.path.exists(file2)
