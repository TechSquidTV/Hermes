# Managed download deliverables

The worker registers the main media file and each remaining subtitle and thumbnail output in the same transaction as completion. File listing, serving, manual deletion and retention use these records. Deleting one output preserves the download record while other outputs remain, so those files stay listed and retention can remove them. Cancellation removes every final output if it wins the completion transition.

The downloader uses yt-dlp's completed file-move manifest to identify deliverables after postprocessing. It excludes removed intermediates and does not scan neighboring files. Request options, including authentication headers and cookies, apply to both metadata extraction and downloading.

Managed paths are canonical absolute paths confined to the configured downloads directory. The `e7f31a92c604` migration normalizes historical paths in bounded batches and adds the filepath index. File access uses an indexed equality lookup; general listing limits remain unchanged. Related downloads are found through the managed record's `download_id`.

**Breaking change:** `YTDLPService.download_video()` now returns `DownloadOutputs` with `media_path`, `sidecar_paths`, and the combined `paths` property instead of a string. Completion also requires this structured result rather than a separate output path. Internal callers must use this result directly; there is no string compatibility adapter. Run database migrations before starting the updated API and worker.

Existing unregistered sidecars cannot be safely attributed from filenames alone. This change tracks deliverables from new downloads; it does not discover old orphaned files by scanning the download directory.
