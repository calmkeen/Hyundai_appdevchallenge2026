// Read-only, bounded-memory QA of the 34-second intro. This does not render or mux video.
// Usage: analyze-intro VIDEO NEW_OUTPUT_DIRECTORY [--full-frame-at SECONDS ...]
import Foundation
import AVFoundation
import AppKit

private let expectedWidth = 1920
private let expectedHeight = 1080
private let expectedFrames = 1020
private let expectedFPS = 30.0
private let sampleStride = 4
private let thumbnailWidth = 480
private let thumbnailHeight = 270
private let sheetColumns = 5
private let sheetRows = 6
private let labelHeight = 28

private struct RGBMetrics: Codable {
    let sample_count: Int
    let mean_rgb: [Double]
    let mean_g_minus_r: Double
    let mean_g_minus_b: Double
    let strong_green_sample_count: Int
    let strong_green_fraction: Double
}

private struct FrameStats: Codable {
    let frame_index: Int
    let pts_seconds: Double
    let pts_value: Int64
    let pts_timescale: Int32
    let width: Int
    let height: Int
    let whole_frame: RGBMetrics
    let outside_app: RGBMetrics
    let corner_deck: RGBMetrics
    let sampled_rgb_hash_fnv1a64: String
    let app_sampled_rgb_hash_fnv1a64: String
    let consecutive_sample_rgb_mad: Double?
    let consecutive_app_sample_rgb_mad: Double?
    let sampled_rgb_identical_to_previous: Bool?
    let app_sampled_rgb_identical_to_previous: Bool?
}

private struct Thumbnail: Codable {
    let frame_index: Int
    let pts_seconds: Double
    let path: String
    let reasons: [String]
}

private struct GreenRun: Codable {
    let first_frame: Int
    let last_frame: Int
    let start_seconds: Double
    let end_seconds_exclusive: Double
    let frame_count: Int
    let maximum_outside_app_green_fraction: Double
    let maximum_outside_app_mean_g_minus_r: Double
    let maximum_outside_app_mean_g_minus_b: Double
    let thumbnail_paths: [String]
}

private struct Analysis: Codable {
    let schema_version = 1
    let source_video: String
    let created_at: String
    let scope: String
    let sample_stride: Int
    let sample_origin = "top-left decoded pixel coordinates"
    let outside_app_region = "x < 432 OR x >= 1872 OR y < 100 OR y >= 1000; y < 1075 excludes the animated progress strip"
    let app_region = "432 <= x < 1872 AND 100 <= y < 1000"
    let corner_deck_region = "16 <= x < 400 AND 16 <= y < 56; plus 1888 <= x < 1904 AND 1016 <= y < 1064"
    let strong_green_predicate = "g > r + 10 AND g > b + 8 AND g > 35 (8-bit RGB)"
    let green_candidate_run_predicate = "outside_app strong_green_fraction >= 0.001; this is a heuristic requiring visual review"
    let expected_frame_count: Int
    let decoded_frame_count: Int
    let track_nominal_frame_rate: Double
    let asset_duration_seconds: Double
    let first_pts_seconds: Double?
    let last_pts_seconds: Double?
    let minimum_pts_step_seconds: Double?
    let maximum_pts_step_seconds: Double?
    let non_increasing_pts_count: Int
    let off_expected_pts_step_count: Int
    let reader_status: String
    let reader_error: String?
    let format_and_timing_passed: Bool
    let whole_frame_identical_pair_count: Int
    let app_identical_pair_count: Int
    let maximum_outside_app_green_fraction: Double
    let green_candidate_runs: [GreenRun]
    let thumbnail_manifest: String
    let full_frame_manifest: [Thumbnail]
    let contact_sheets: [String]
    let frames: [FrameStats]
}

private struct Accumulator {
    var count = 0
    var red: Int64 = 0
    var green: Int64 = 0
    var blue: Int64 = 0
    var strongGreen = 0

    mutating func add(_ r: Int, _ g: Int, _ b: Int) {
        count += 1
        red += Int64(r); green += Int64(g); blue += Int64(b)
        if g > r + 10 && g > b + 8 && g > 35 { strongGreen += 1 }
    }

    var metrics: RGBMetrics {
        let denominator = Double(max(count, 1))
        return RGBMetrics(sample_count: count,
                          mean_rgb: [Double(red) / denominator, Double(green) / denominator, Double(blue) / denominator],
                          mean_g_minus_r: Double(green - red) / denominator,
                          mean_g_minus_b: Double(green - blue) / denominator,
                          strong_green_sample_count: strongGreen,
                          strong_green_fraction: Double(strongGreen) / denominator)
    }
}

private func fail(_ message: String) -> NSError {
    NSError(domain: "IntroVideoAnalysis", code: 1, userInfo: [NSLocalizedDescriptionKey: message])
}

private func writeJSON<T: Encodable>(_ value: T, to url: URL) throws {
    let encoder = JSONEncoder()
    encoder.outputFormatting = [.prettyPrinted, .sortedKeys, .withoutEscapingSlashes]
    try encoder.encode(value).write(to: url, options: .atomic)
}

private func hashDescription(_ bytes: [UInt8]) -> String {
    var hash: UInt64 = 14_695_981_039_346_656_037
    for byte in bytes { hash = (hash ^ UInt64(byte)) &* 1_099_511_628_211 }
    return String(format: "%016llx", hash)
}

private func meanAbsoluteDifference(_ current: [UInt8], _ previous: [UInt8]?) -> Double? {
    guard let previous, previous.count == current.count else { return nil }
    var difference: Int64 = 0
    for index in current.indices { difference += Int64(abs(Int(current[index]) - Int(previous[index]))) }
    return Double(difference) / Double(current.count)
}

private func downsample(_ image: CGImage) throws -> CGImage {
    guard let context = CGContext(data: nil, width: thumbnailWidth, height: thumbnailHeight,
                                  bitsPerComponent: 8, bytesPerRow: thumbnailWidth * 4,
                                  space: CGColorSpace(name: CGColorSpace.sRGB)!,
                                  bitmapInfo: CGImageAlphaInfo.noneSkipLast.rawValue) else {
        throw fail("Unable to create thumbnail bitmap")
    }
    context.interpolationQuality = .high
    context.draw(image, in: CGRect(x: 0, y: 0, width: thumbnailWidth, height: thumbnailHeight))
    guard let result = context.makeImage() else { throw fail("Unable to downsample decoded image") }
    return result
}

private func writeImage(_ image: CGImage, to url: URL, type: NSBitmapImageRep.FileType) throws {
    let bitmap = NSBitmapImageRep(cgImage: image)
    let properties: [NSBitmapImageRep.PropertyKey: Any] = type == .jpeg ? [.compressionFactor: 0.86] : [:]
    guard let data = bitmap.representation(using: type, properties: properties) else {
        throw fail("Unable to encode QA image: \(url.lastPathComponent)")
    }
    try data.write(to: url, options: .atomic)
}

private func makeContactSheets(_ thumbnails: [Thumbnail], prefix: String, output: URL) throws -> [String] {
    var paths: [String] = []
    let pageCapacity = sheetColumns * sheetRows
    for start in stride(from: 0, to: thumbnails.count, by: pageCapacity) {
        let path: String = try autoreleasepool {
            let slice = Array(thumbnails[start..<min(start + pageCapacity, thumbnails.count)])
            let rowCount = (slice.count + sheetColumns - 1) / sheetColumns
            let width = thumbnailWidth * sheetColumns
            let height = (thumbnailHeight + labelHeight) * rowCount
            guard let bitmap = NSBitmapImageRep(bitmapDataPlanes: nil, pixelsWide: width, pixelsHigh: height,
                                                bitsPerSample: 8, samplesPerPixel: 4, hasAlpha: true,
                                                isPlanar: false, colorSpaceName: .deviceRGB,
                                                bytesPerRow: 0, bitsPerPixel: 0),
                  let graphics = NSGraphicsContext(bitmapImageRep: bitmap) else {
                throw fail("Unable to create contact sheet bitmap")
            }
            NSGraphicsContext.saveGraphicsState()
            defer { NSGraphicsContext.restoreGraphicsState() }
            NSGraphicsContext.current = graphics
            NSColor.white.setFill()
            NSRect(x: 0, y: 0, width: width, height: height).fill()
            for (index, thumbnail) in slice.enumerated() {
                let x = (index % sheetColumns) * thumbnailWidth
                let top = (index / sheetColumns) * (thumbnailHeight + labelHeight)
                guard let image = NSImage(contentsOf: output.appendingPathComponent(thumbnail.path)) else {
                    throw fail("Unable to read thumbnail for contact sheet: \(thumbnail.path)")
                }
                image.draw(in: NSRect(x: x, y: height - top - thumbnailHeight,
                                      width: thumbnailWidth, height: thumbnailHeight))
                let label = String(format: "frame %04d  %.3fs", thumbnail.frame_index, thumbnail.pts_seconds)
                (label as NSString).draw(in: NSRect(x: x + 8, y: height - top - thumbnailHeight - labelHeight + 5,
                                                   width: thumbnailWidth - 16, height: labelHeight - 5),
                                         withAttributes: [.font: NSFont.monospacedSystemFont(ofSize: 15, weight: .regular),
                                                          .foregroundColor: NSColor.black])
            }
            guard let image = bitmap.cgImage else { throw fail("Unable to finalize contact sheet") }
            let name = String(format: "contact-sheets/%@-%02d.jpg", prefix, start / pageCapacity + 1)
            try writeImage(image, to: output.appendingPathComponent(name), type: .jpeg)
            return name
        }
        paths.append(path)
    }
    return paths
}

private func analyze() throws {
    let args = CommandLine.arguments
    guard args.count >= 3 else {
        throw fail("Usage: analyze-intro VIDEO NEW_OUTPUT_DIRECTORY [--full-frame-at SECONDS ...]")
    }
    let source = URL(fileURLWithPath: args[1]).standardizedFileURL
    let output = URL(fileURLWithPath: args[2], isDirectory: true).standardizedFileURL
    guard FileManager.default.fileExists(atPath: source.path) else { throw fail("Video does not exist: \(source.path)") }
    guard !FileManager.default.fileExists(atPath: output.path) else {
        throw fail("Refusing to overwrite an existing output path: \(output.path)")
    }
    var fullFrameIndices = Set<Int>()
    var argumentIndex = 3
    while argumentIndex < args.count {
        guard args[argumentIndex] == "--full-frame-at", argumentIndex + 1 < args.count,
              let seconds = Double(args[argumentIndex + 1]), seconds.isFinite, seconds >= 0, seconds < 34 else {
            throw fail("Expected --full-frame-at SECONDS, with 0 <= SECONDS < 34")
        }
        fullFrameIndices.insert(Int((seconds * expectedFPS).rounded()))
        argumentIndex += 2
    }

    let asset = AVURLAsset(url: source)
    guard let track = asset.tracks(withMediaType: .video).first else { throw fail("No video track") }
    let size = track.naturalSize
    guard Int(size.width) == expectedWidth && Int(size.height) == expectedHeight else {
        throw fail("Expected 1920x1080 input; found \(size)")
    }
    guard track.preferredTransform == .identity else { throw fail("Rotated/transformed input requires explicit handling") }
    let reader = try AVAssetReader(asset: asset)
    let readerOutput = AVAssetReaderTrackOutput(track: track, outputSettings: [
        kCVPixelBufferPixelFormatTypeKey as String: kCVPixelFormatType_32BGRA
    ])
    readerOutput.alwaysCopiesSampleData = false
    guard reader.canAdd(readerOutput) else { throw fail("Cannot add video decoder output") }
    reader.add(readerOutput)

    // The new-directory guard above ensures earlier QA artifacts cannot be silently replaced.
    try FileManager.default.createDirectory(at: output.appendingPathComponent("thumbnails"), withIntermediateDirectories: true)
    try FileManager.default.createDirectory(at: output.appendingPathComponent("full-frames"), withIntermediateDirectories: false)
    try FileManager.default.createDirectory(at: output.appendingPathComponent("contact-sheets"), withIntermediateDirectories: false)
    guard reader.startReading() else { throw fail("AVAssetReader failed to start: \(String(describing: reader.error))") }

    var frames: [FrameStats] = []
    frames.reserveCapacity(expectedFrames)
    var thumbnails: [Thumbnail] = []
    var fullFrames: [Thumbnail] = []
    var previousPixels: [UInt8]?
    var previousAppPixels: [UInt8]?
    var minimumStep = Double.infinity
    var maximumStep = -Double.infinity
    var nonIncreasingCount = 0
    var offStepCount = 0
    let boundaries = stride(from: 3.0, through: 31.0, by: 2.0).map { $0 }

    while let sample = readerOutput.copyNextSampleBuffer() {
        try autoreleasepool {
            let index = frames.count
            let pts = CMSampleBufferGetPresentationTimeStamp(sample)
            let seconds = CMTimeGetSeconds(pts)
            guard seconds.isFinite else { throw fail("Non-finite PTS at frame \(index)") }
            if let previous = frames.last {
                let step = seconds - previous.pts_seconds
                minimumStep = min(minimumStep, step); maximumStep = max(maximumStep, step)
                if step <= 0 { nonIncreasingCount += 1 }
                if abs(step - 1.0 / expectedFPS) > 0.000001 { offStepCount += 1 }
            }
            guard let pixels = CMSampleBufferGetImageBuffer(sample) else { throw fail("Missing pixel buffer at frame \(index)") }
            let width = CVPixelBufferGetWidth(pixels), height = CVPixelBufferGetHeight(pixels)
            guard width == expectedWidth && height == expectedHeight else { throw fail("Unexpected decoded dimensions at frame \(index)") }
            CVPixelBufferLockBaseAddress(pixels, .readOnly)
            defer { CVPixelBufferUnlockBaseAddress(pixels, .readOnly) }
            guard let address = CVPixelBufferGetBaseAddress(pixels) else { throw fail("Missing decoded pixels") }
            let base = address.assumingMemoryBound(to: UInt8.self)
            let bytesPerRow = CVPixelBufferGetBytesPerRow(pixels)
            var whole = Accumulator(), outside = Accumulator(), corner = Accumulator()
            var sampled: [UInt8] = []
            var appSampled: [UInt8] = []
            sampled.reserveCapacity(width / sampleStride * height / sampleStride * 3)
            appSampled.reserveCapacity(1440 / sampleStride * 900 / sampleStride * 3)
            for y in stride(from: 0, to: height, by: sampleStride) {
                let row = base.advanced(by: y * bytesPerRow)
                for x in stride(from: 0, to: width, by: sampleStride) {
                    let pixel = row.advanced(by: x * 4)
                    let b = Int(pixel[0]), g = Int(pixel[1]), r = Int(pixel[2])
                    whole.add(r, g, b)
                    sampled.append(UInt8(r)); sampled.append(UInt8(g)); sampled.append(UInt8(b))
                    let inApp = x >= 432 && x < 1872 && y >= 100 && y < 1000
                    if inApp {
                        appSampled.append(UInt8(r)); appSampled.append(UInt8(g)); appSampled.append(UInt8(b))
                    } else if y < 1075 {
                        outside.add(r, g, b)
                    }
                    if (x >= 16 && x < 400 && y >= 16 && y < 56) ||
                       (x >= 1888 && x < 1904 && y >= 1016 && y < 1064) {
                        corner.add(r, g, b)
                    }
                }
            }
            let mad = meanAbsoluteDifference(sampled, previousPixels)
            let appMAD = meanAbsoluteDifference(appSampled, previousAppPixels)
            frames.append(FrameStats(frame_index: index, pts_seconds: seconds, pts_value: pts.value, pts_timescale: pts.timescale,
                                     width: width, height: height, whole_frame: whole.metrics,
                                     outside_app: outside.metrics, corner_deck: corner.metrics,
                                     sampled_rgb_hash_fnv1a64: hashDescription(sampled),
                                     app_sampled_rgb_hash_fnv1a64: hashDescription(appSampled),
                                     consecutive_sample_rgb_mad: mad, consecutive_app_sample_rgb_mad: appMAD,
                                     sampled_rgb_identical_to_previous: mad.map { $0 == 0 },
                                     app_sampled_rgb_identical_to_previous: appMAD.map { $0 == 0 }))
            previousPixels = sampled; previousAppPixels = appSampled

            var reasons: [String] = []
            if index % 6 == 0 { reasons.append("regular_5fps") }
            if boundaries.contains(where: { seconds >= $0 - 0.100001 && seconds <= $0 + 0.200001 }) {
                reasons.append("scene_boundary_30fps")
            }
            if index == 0 || index == expectedFrames - 1 { reasons.append("endpoint") }
            if fullFrameIndices.contains(index) { reasons.append("requested_full_frame") }
            if !reasons.isEmpty {
                let bitmapInfo = CGBitmapInfo.byteOrder32Little.rawValue | CGImageAlphaInfo.noneSkipFirst.rawValue
                guard let context = CGContext(data: address, width: width, height: height,
                                              bitsPerComponent: 8, bytesPerRow: bytesPerRow,
                                              space: CGColorSpace(name: CGColorSpace.sRGB)!, bitmapInfo: bitmapInfo),
                      let image = context.makeImage() else { throw fail("Unable to export frame \(index)") }
                let thumbnailPath = String(format: "thumbnails/frame-%04d.jpg", index)
                try writeImage(downsample(image), to: output.appendingPathComponent(thumbnailPath), type: .jpeg)
                thumbnails.append(Thumbnail(frame_index: index, pts_seconds: seconds, path: thumbnailPath, reasons: reasons))
                if fullFrameIndices.contains(index) {
                    let fullPath = String(format: "full-frames/frame-%04d.png", index)
                    try writeImage(image, to: output.appendingPathComponent(fullPath), type: .png)
                    fullFrames.append(Thumbnail(frame_index: index, pts_seconds: seconds, path: fullPath, reasons: ["requested_full_frame"]))
                }
            }
        }
        if frames.count % 150 == 0 { print("Decoded \(frames.count) frames") }
        if frames.count > expectedFrames + 60 { reader.cancelReading(); throw fail("Unexpected input exceeds expected 1020 frames") }
    }

    let status: String
    switch reader.status {
    case .completed: status = "completed"
    case .failed: status = "failed"
    case .cancelled: status = "cancelled"
    case .reading: status = "reading"
    case .unknown: status = "unknown"
    @unknown default: status = "unrecognized"
    }
    let readerError = reader.error.map { String(describing: $0) }
    var runs: [GreenRun] = []
    var firstCandidate: Int?
    func appendRun(through last: Int) {
        guard let first = firstCandidate else { return }
        let slice = frames[first...last]
        runs.append(GreenRun(first_frame: first, last_frame: last,
                             start_seconds: frames[first].pts_seconds,
                             end_seconds_exclusive: frames[last].pts_seconds + 1.0 / expectedFPS,
                             frame_count: last - first + 1,
                             maximum_outside_app_green_fraction: slice.map { $0.outside_app.strong_green_fraction }.max() ?? 0,
                             maximum_outside_app_mean_g_minus_r: slice.map { $0.outside_app.mean_g_minus_r }.max() ?? 0,
                             maximum_outside_app_mean_g_minus_b: slice.map { $0.outside_app.mean_g_minus_b }.max() ?? 0,
                             thumbnail_paths: thumbnails.filter { $0.frame_index >= first && $0.frame_index <= last }.map { $0.path }))
        firstCandidate = nil
    }
    for frame in frames {
        if frame.outside_app.strong_green_fraction >= 0.001 {
            if firstCandidate == nil { firstCandidate = frame.frame_index }
        } else if firstCandidate != nil { appendRun(through: frame.frame_index - 1) }
    }
    if firstCandidate != nil { appendRun(through: frames.count - 1) }

    try writeJSON(thumbnails, to: output.appendingPathComponent("thumbnail-manifest.json"))
    var sheets = try makeContactSheets(thumbnails.filter { $0.reasons.contains("regular_5fps") || $0.reasons.contains("endpoint") },
                                       prefix: "regular", output: output)
    sheets += try makeContactSheets(thumbnails.filter { $0.reasons.contains("scene_boundary_30fps") },
                                    prefix: "boundaries", output: output)
    let timingPassed = frames.count == expectedFrames && nonIncreasingCount == 0 && offStepCount == 0 &&
                       abs(frames.first?.pts_seconds ?? -1) < 0.000001 &&
                       reader.status == .completed && readerError == nil
    let analysis = Analysis(source_video: source.path,
                            created_at: ISO8601DateFormatter().string(from: Date()),
                            scope: "All decoded video frames, stride-4 RGB measurements, 5fps and cut-boundary thumbnails. Green detection is a QA heuristic, not visual proof. App hashes measure decoded image repeats; they do not estimate or invent source FPS. No video or audio is modified.",
                            sample_stride: sampleStride,
                            expected_frame_count: expectedFrames, decoded_frame_count: frames.count,
                            track_nominal_frame_rate: Double(track.nominalFrameRate),
                            asset_duration_seconds: CMTimeGetSeconds(asset.duration),
                            first_pts_seconds: frames.first?.pts_seconds, last_pts_seconds: frames.last?.pts_seconds,
                            minimum_pts_step_seconds: minimumStep.isFinite ? minimumStep : nil,
                            maximum_pts_step_seconds: maximumStep.isFinite ? maximumStep : nil,
                            non_increasing_pts_count: nonIncreasingCount, off_expected_pts_step_count: offStepCount,
                            reader_status: status, reader_error: readerError, format_and_timing_passed: timingPassed,
                            whole_frame_identical_pair_count: frames.filter { $0.sampled_rgb_identical_to_previous == true }.count,
                            app_identical_pair_count: frames.filter { $0.app_sampled_rgb_identical_to_previous == true }.count,
                            maximum_outside_app_green_fraction: frames.map { $0.outside_app.strong_green_fraction }.max() ?? 0,
                            green_candidate_runs: runs, thumbnail_manifest: "thumbnail-manifest.json",
                            full_frame_manifest: fullFrames, contact_sheets: sheets, frames: frames)
    try writeJSON(analysis, to: output.appendingPathComponent("analysis.json"))
    print("Analysis: \(output.appendingPathComponent("analysis.json").path)")
    print("Decoded \(frames.count) frames; reader=\(status); readerError=\(readerError ?? "none"); format/timing=\(timingPassed ? "PASS" : "FAIL")")
    print("PTS step min=\(minimumStep), max=\(maximumStep); green candidate runs=\(runs.count); QA thumbnails=\(thumbnails.count)")
    guard timingPassed else { throw fail("Decode/format/timing validation failed; inspect analysis.json") }
}

do {
    try analyze()
} catch {
    fputs("ERROR: \(error.localizedDescription)\n", stderr)
    exit(1)
}
