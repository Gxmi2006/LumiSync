# Performance and Engineering Improvements

## Lower CPU Usage

- Capture smaller regions whenever possible.
- Downscale before any color analysis.
- Use NumPy masks and histograms instead of Python loops.
- Keep visual-priority saliency maps at the configured downscaled resolution.
- Skip backend writes when color delta is below threshold.
- Add adaptive FPS: high FPS during scene changes, low FPS during static frames.

## Lower Latency

- Use Desktop Duplication through `dxcam` for fullscreen and monitor capture.
- Keep only the latest captured frame; never process a backlog.
- Separate capture and dispatch timing.
- Preallocate arrays where profiling shows allocation pressure.
- Keep smoothing cheap and stateful.

## Frame Pacing

Current pacing uses a fixed loop interval. Future pacing should track:

- capture time
- processing time
- backend dispatch time
- sleep jitter
- dropped frames

Expose this in diagnostics overlay.

## Async and Threading

Recommended model:

- UI/tray thread
- capture worker thread
- processing worker thread
- backend dispatch worker thread
- command/event queue

Use queues with size 1 for frame data so stale frames are dropped.

## GPU Acceleration

OpenCV CUDA is not a default dependency and is usually overkill for this pipeline. Better first steps:

- DXGI/DXcam capture
- smaller downscale
- vectorized NumPy
- optional Numba only if profiling proves value

## Dirty-Region Updates

Detect whether the frame changed enough to process. Use low-res frame difference or rolling luma delta. If below threshold, reuse previous color and reduce FPS.

## Memory Optimization

- Avoid repeated copies after MSS capture where possible.
- Keep RGB/BGRA conversion explicit.
- Reuse downscale target dimensions.
- Avoid creating Python lists for pixel operations.

## OpenCV Optimization

- Prefer `cv2.INTER_AREA` for downscaling.
- Use HSV masks for saturation/value filtering.
- Keep quantization bin counts reasonable.
- Use weighted histograms before considering k-means.
- Prefer the hybrid saliency heuristic over OpenCV-contrib saliency APIs for predictable dependencies.

## Backend Dispatch

- Backends should expose capabilities.
- Dispatch should rate-limit per backend.
- Failures should mark backend unavailable and schedule retry.
- Software fallback should never raise during normal color updates.
