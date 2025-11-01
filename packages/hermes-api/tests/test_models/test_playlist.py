"""
Tests for playlist Pydantic models.
"""

from datetime import datetime

import pytest
from pydantic import ValidationError

from app.models.pydantic.playlist import (
    BatchCreateParams,
    BatchCreateResult,
    BatchProgressInfo,
    BatchStartResult,
    BatchStatus,
    BatchType,
    CreateBatchRequest,
    CreateBatchResponse,
    DetectUrlTypeRequest,
    DetectUrlTypeResponse,
    ParsePlaylistRequest,
    ParsePlaylistResponse,
    PlaylistInfo,
    PlaylistVideoInfo,
    SingleVideoInfo,
    UrlDetectionResult,
    YTDLResultType,
)


class TestPlaylistVideoInfo:
    """Tests for PlaylistVideoInfo model"""

    def test_create_with_required_fields(self):
        """Test creating PlaylistVideoInfo with only required fields"""
        video = PlaylistVideoInfo(
            url="https://youtube.com/watch?v=123",
            video_id="123",
            title="Test Video",
        )
        assert video.url == "https://youtube.com/watch?v=123"
        assert video.video_id == "123"
        assert video.title == "Test Video"
        assert video.duration is None
        assert video.thumbnail is None
        assert video.uploader is None
        assert video.view_count is None
        assert video.upload_date is None

    def test_create_with_all_fields(self):
        """Test creating PlaylistVideoInfo with all fields"""
        video = PlaylistVideoInfo(
            url="https://youtube.com/watch?v=123",
            video_id="123",
            title="Test Video",
            duration=300,
            thumbnail="https://i.ytimg.com/vi/123/default.jpg",
            uploader="Test Channel",
            view_count=1000,
            upload_date="20240101",
        )
        assert video.url == "https://youtube.com/watch?v=123"
        assert video.video_id == "123"
        assert video.title == "Test Video"
        assert video.duration == 300
        assert video.thumbnail == "https://i.ytimg.com/vi/123/default.jpg"
        assert video.uploader == "Test Channel"
        assert video.view_count == 1000
        assert video.upload_date == "20240101"

    def test_missing_required_field(self):
        """Test that missing required fields raise ValidationError"""
        with pytest.raises(ValidationError):
            PlaylistVideoInfo(url="https://youtube.com/watch?v=123", video_id="123")


class TestPlaylistInfo:
    """Tests for PlaylistInfo model"""

    def test_create_with_required_fields(self):
        """Test creating PlaylistInfo with required fields"""
        playlist = PlaylistInfo(
            is_playlist=True,
            playlist_type="playlist",
            playlist_title="Test Playlist",
            playlist_id="PL123",
            playlist_url="https://youtube.com/playlist?list=PL123",
            video_count=5,
            videos=[
                PlaylistVideoInfo(
                    url="https://youtube.com/watch?v=1",
                    video_id="1",
                    title="Video 1",
                )
            ],
        )
        assert playlist.is_playlist is True
        assert playlist.playlist_type == "playlist"
        assert playlist.playlist_title == "Test Playlist"
        assert playlist.playlist_id == "PL123"
        assert playlist.playlist_url == "https://youtube.com/playlist?list=PL123"
        assert playlist.video_count == 5
        assert len(playlist.videos) == 1
        assert playlist.uploader is None
        assert playlist.uploader_id is None
        assert playlist.description is None

    def test_create_with_all_fields(self):
        """Test creating PlaylistInfo with all fields"""
        videos = [
            PlaylistVideoInfo(
                url="https://youtube.com/watch?v=1", video_id="1", title="Video 1"
            ),
            PlaylistVideoInfo(
                url="https://youtube.com/watch?v=2", video_id="2", title="Video 2"
            ),
        ]
        playlist = PlaylistInfo(
            is_playlist=True,
            playlist_type="multi_video",
            playlist_title="Test Playlist",
            playlist_id="PL123",
            playlist_url="https://youtube.com/playlist?list=PL123",
            video_count=2,
            videos=videos,
            uploader="Test Channel",
            uploader_id="UC123",
            description="A test playlist",
        )
        assert playlist.uploader == "Test Channel"
        assert playlist.uploader_id == "UC123"
        assert playlist.description == "A test playlist"
        assert len(playlist.videos) == 2

    def test_valid_playlist_types(self):
        """Test that valid playlist types are accepted"""
        valid_types: list[YTDLResultType] = [
            "video",
            "playlist",
            "multi_video",
            "url",
            "url_transparent",
            "compat_list",
        ]
        for ptype in valid_types:
            playlist = PlaylistInfo(
                is_playlist=True,
                playlist_type=ptype,
                playlist_title="Test",
                playlist_id="123",
                playlist_url="https://example.com",
                video_count=0,
                videos=[],
            )
            assert playlist.playlist_type == ptype


class TestSingleVideoInfo:
    """Tests for SingleVideoInfo model"""

    def test_create_with_required_fields(self):
        """Test creating SingleVideoInfo with required fields"""
        video = SingleVideoInfo(
            url="https://youtube.com/watch?v=123",
            video_id="123",
            title="Test Video",
        )
        assert video.is_playlist is False
        assert video.url == "https://youtube.com/watch?v=123"
        assert video.video_id == "123"
        assert video.title == "Test Video"
        assert video.duration is None
        assert video.thumbnail is None
        assert video.uploader is None
        assert video.description is None

    def test_create_with_all_fields(self):
        """Test creating SingleVideoInfo with all fields"""
        video = SingleVideoInfo(
            url="https://youtube.com/watch?v=123",
            video_id="123",
            title="Test Video",
            duration=300,
            thumbnail="https://i.ytimg.com/vi/123/default.jpg",
            uploader="Test Channel",
            description="Test description",
        )
        assert video.duration == 300
        assert video.thumbnail == "https://i.ytimg.com/vi/123/default.jpg"
        assert video.uploader == "Test Channel"
        assert video.description == "Test description"

    def test_is_playlist_always_false(self):
        """Test that is_playlist is always False"""
        video = SingleVideoInfo(
            url="https://youtube.com/watch?v=123",
            video_id="123",
            title="Test Video",
        )
        assert video.is_playlist is False


class TestUrlDetectionResult:
    """Tests for UrlDetectionResult model"""

    def test_create_without_metadata(self):
        """Test creating UrlDetectionResult without metadata"""
        result = UrlDetectionResult(
            url="https://youtube.com/watch?v=123",
            url_type="video",
        )
        assert result.url == "https://youtube.com/watch?v=123"
        assert result.url_type == "video"
        assert result.metadata is None

    def test_create_with_single_video_metadata(self):
        """Test creating UrlDetectionResult with SingleVideoInfo metadata"""
        video = SingleVideoInfo(
            url="https://youtube.com/watch?v=123",
            video_id="123",
            title="Test Video",
        )
        result = UrlDetectionResult(
            url="https://youtube.com/watch?v=123",
            url_type="video",
            metadata=video,
        )
        assert result.metadata == video

    def test_create_with_playlist_metadata(self):
        """Test creating UrlDetectionResult with PlaylistInfo metadata"""
        playlist = PlaylistInfo(
            is_playlist=True,
            playlist_type="playlist",
            playlist_title="Test Playlist",
            playlist_id="PL123",
            playlist_url="https://youtube.com/playlist?list=PL123",
            video_count=0,
            videos=[],
        )
        result = UrlDetectionResult(
            url="https://youtube.com/playlist?list=PL123",
            url_type="playlist",
            metadata=playlist,
        )
        assert result.metadata == playlist

    def test_valid_url_types(self):
        """Test that valid URL types are accepted"""
        for url_type in ["playlist", "video", "unknown"]:
            result = UrlDetectionResult(url="https://example.com", url_type=url_type)
            assert result.url_type == url_type


class TestBatchCreateParams:
    """Tests for BatchCreateParams model"""

    def test_create_with_required_fields(self):
        """Test creating BatchCreateParams with required fields"""
        params = BatchCreateParams(
            user_id="user123",
            batch_type="playlist",
        )
        assert params.user_id == "user123"
        assert params.batch_type == "playlist"
        assert params.batch_title is None
        assert params.source_url is None
        assert params.format_spec == "best"
        assert params.output_directory is None
        assert params.videos == []

    def test_create_with_all_fields(self):
        """Test creating BatchCreateParams with all fields"""
        videos = [
            PlaylistVideoInfo(
                url="https://youtube.com/watch?v=1", video_id="1", title="Video 1"
            )
        ]
        params = BatchCreateParams(
            user_id="user123",
            batch_type="manual_batch",
            batch_title="My Batch",
            source_url="https://youtube.com/playlist?list=PL123",
            format_spec="1080p",
            output_directory="/downloads",
            videos=videos,
        )
        assert params.batch_title == "My Batch"
        assert params.source_url == "https://youtube.com/playlist?list=PL123"
        assert params.format_spec == "1080p"
        assert params.output_directory == "/downloads"
        assert len(params.videos) == 1

    def test_valid_batch_types(self):
        """Test that valid batch types are accepted"""
        valid_types: list[BatchType] = ["playlist", "manual_batch", "api_batch"]
        for btype in valid_types:
            params = BatchCreateParams(user_id="user123", batch_type=btype)
            assert params.batch_type == btype


class TestBatchProgressInfo:
    """Tests for BatchProgressInfo model"""

    def test_create_batch_progress_info(self):
        """Test creating BatchProgressInfo"""
        progress = BatchProgressInfo(
            batch_id="batch123",
            status="processing",
            total_videos=10,
            completed_videos=5,
            failed_videos=1,
            pending_videos=4,
            overall_progress=50.0,
        )
        assert progress.batch_id == "batch123"
        assert progress.status == "processing"
        assert progress.total_videos == 10
        assert progress.completed_videos == 5
        assert progress.failed_videos == 1
        assert progress.pending_videos == 4
        assert progress.overall_progress == 50.0

    def test_progress_validation(self):
        """Test that progress is validated between 0 and 100"""
        # Valid values
        BatchProgressInfo(
            batch_id="batch123",
            status="processing",
            total_videos=10,
            completed_videos=0,
            failed_videos=0,
            pending_videos=10,
            overall_progress=0.0,
        )
        BatchProgressInfo(
            batch_id="batch123",
            status="completed",
            total_videos=10,
            completed_videos=10,
            failed_videos=0,
            pending_videos=0,
            overall_progress=100.0,
        )

    def test_valid_batch_statuses(self):
        """Test that valid batch statuses are accepted"""
        valid_statuses: list[BatchStatus] = [
            "pending",
            "processing",
            "completed",
            "failed",
            "cancelled",
        ]
        for status in valid_statuses:
            progress = BatchProgressInfo(
                batch_id="batch123",
                status=status,
                total_videos=10,
                completed_videos=0,
                failed_videos=0,
                pending_videos=10,
                overall_progress=0.0,
            )
            assert progress.status == status


class TestBatchCreateResult:
    """Tests for BatchCreateResult model"""

    def test_create_batch_result(self):
        """Test creating BatchCreateResult"""
        now = datetime.now()
        result = BatchCreateResult(
            batch_id="batch123",
            batch_title="Test Batch",
            batch_type="playlist",
            status="pending",
            total_videos=10,
            created_at=now,
        )
        assert result.batch_id == "batch123"
        assert result.batch_title == "Test Batch"
        assert result.batch_type == "playlist"
        assert result.status == "pending"
        assert result.total_videos == 10
        assert result.created_at == now


class TestBatchStartResult:
    """Tests for BatchStartResult model"""

    def test_create_batch_start_result(self):
        """Test creating BatchStartResult"""
        result = BatchStartResult(
            batch_id="batch123",
            queued_count=10,
            failed_count=0,
            task_ids=["task1", "task2", "task3"],
        )
        assert result.batch_id == "batch123"
        assert result.queued_count == 10
        assert result.failed_count == 0
        assert len(result.task_ids) == 3


class TestDetectUrlTypeRequest:
    """Tests for DetectUrlTypeRequest model"""

    def test_create_detect_url_type_request(self):
        """Test creating DetectUrlTypeRequest"""
        request = DetectUrlTypeRequest(url="https://youtube.com/watch?v=123")
        assert request.url == "https://youtube.com/watch?v=123"


class TestDetectUrlTypeResponse:
    """Tests for DetectUrlTypeResponse model"""

    def test_create_detect_url_type_response(self):
        """Test creating DetectUrlTypeResponse"""
        response = DetectUrlTypeResponse(
            success=True,
            url_type="video",
            metadata={"title": "Test Video"},
        )
        assert response.success is True
        assert response.url_type == "video"
        assert response.metadata == {"title": "Test Video"}

    def test_create_without_metadata(self):
        """Test creating DetectUrlTypeResponse without metadata"""
        response = DetectUrlTypeResponse(success=False, url_type="unknown")
        assert response.success is False
        assert response.url_type == "unknown"
        assert response.metadata is None


class TestParsePlaylistRequest:
    """Tests for ParsePlaylistRequest model"""

    def test_create_with_default_extract_flat(self):
        """Test creating ParsePlaylistRequest with default extract_flat"""
        request = ParsePlaylistRequest(url="https://youtube.com/playlist?list=PL123")
        assert request.url == "https://youtube.com/playlist?list=PL123"
        assert request.extract_flat is True

    def test_create_with_extract_flat_false(self):
        """Test creating ParsePlaylistRequest with extract_flat=False"""
        request = ParsePlaylistRequest(
            url="https://youtube.com/playlist?list=PL123", extract_flat=False
        )
        assert request.extract_flat is False


class TestParsePlaylistResponse:
    """Tests for ParsePlaylistResponse model"""

    def test_create_success_response(self):
        """Test creating successful ParsePlaylistResponse"""
        playlist = PlaylistInfo(
            is_playlist=True,
            playlist_type="playlist",
            playlist_title="Test Playlist",
            playlist_id="PL123",
            playlist_url="https://youtube.com/playlist?list=PL123",
            video_count=0,
            videos=[],
        )
        response = ParsePlaylistResponse(
            success=True,
            playlist=playlist,
            message="Successfully parsed playlist",
        )
        assert response.success is True
        assert response.playlist == playlist
        assert response.message == "Successfully parsed playlist"

    def test_create_error_response(self):
        """Test creating error ParsePlaylistResponse"""
        response = ParsePlaylistResponse(
            success=False,
            playlist=None,
            message="Failed to parse playlist",
        )
        assert response.success is False
        assert response.playlist is None
        assert response.message == "Failed to parse playlist"


class TestCreateBatchRequest:
    """Tests for CreateBatchRequest model"""

    def test_create_playlist_batch_request(self):
        """Test creating CreateBatchRequest for playlist"""
        request = CreateBatchRequest(
            source_type="playlist",
            playlist_url="https://youtube.com/playlist?list=PL123",
        )
        assert request.source_type == "playlist"
        assert request.playlist_url == "https://youtube.com/playlist?list=PL123"
        assert request.urls is None
        assert request.batch_title is None
        assert request.format_spec == "best"
        assert request.output_directory is None
        assert request.start_immediately is True

    def test_create_manual_batch_request(self):
        """Test creating CreateBatchRequest for manual batch"""
        urls = ["https://youtube.com/watch?v=1", "https://youtube.com/watch?v=2"]
        request = CreateBatchRequest(
            source_type="manual",
            urls=urls,
            batch_title="My Manual Batch",
            format_spec="720p",
            start_immediately=False,
        )
        assert request.source_type == "manual"
        assert request.urls == urls
        assert request.batch_title == "My Manual Batch"
        assert request.format_spec == "720p"
        assert request.start_immediately is False

    def test_create_with_all_fields(self):
        """Test creating CreateBatchRequest with all fields"""
        request = CreateBatchRequest(
            source_type="playlist",
            playlist_url="https://youtube.com/playlist?list=PL123",
            urls=["https://youtube.com/watch?v=1"],
            batch_title="Test Batch",
            format_spec="1080p",
            output_directory="/downloads/batch",
            start_immediately=True,
        )
        assert request.playlist_url == "https://youtube.com/playlist?list=PL123"
        assert request.urls == ["https://youtube.com/watch?v=1"]
        assert request.batch_title == "Test Batch"
        assert request.output_directory == "/downloads/batch"


class TestCreateBatchResponse:
    """Tests for CreateBatchResponse model"""

    def test_create_batch_response(self):
        """Test creating CreateBatchResponse"""
        now = datetime.now()
        response = CreateBatchResponse(
            success=True,
            batch_id="batch123",
            batch_title="Test Batch",
            batch_type="playlist",
            total_videos=10,
            status="pending",
            created_at=now,
        )
        assert response.success is True
        assert response.batch_id == "batch123"
        assert response.batch_title == "Test Batch"
        assert response.batch_type == "playlist"
        assert response.total_videos == 10
        assert response.status == "pending"
        assert response.created_at == now
