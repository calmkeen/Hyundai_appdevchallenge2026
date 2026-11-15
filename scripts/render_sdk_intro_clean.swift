// Opaque-frame cleanup renderer for the existing SDK intro. The original
// renderer, plan, recordings and APK stay unchanged. Legacy artwork helpers and
// operations are retained so this file can be built independently.
import Foundation
import AVFoundation
import AppKit
import QuartzCore

private let W = 1920.0, H = 1080.0
private let blue = NSColor(srgbRed: 40/255, green: 89/255, blue: 232/255, alpha: 1)
private let ink = NSColor(srgbRed: 21/255, green: 33/255, blue: 50/255, alpha: 1)
private let muted = NSColor(srgbRed: 82/255, green: 97/255, blue: 118/255, alpha: 1)
private let pale = NSColor(srgbRed: 0.956, green: 0.969, blue: 0.988, alpha: 1)
private let appRect = NSRect(x: 432, y: 80, width: 1440, height: 900)

private struct Shot: Decodable {
    let kind: String, duration: Double, title: String, subtitle: String
    let start: Double?
    let chapter: String?
    let detail: String?
    let source: String?
    var key: String { [kind, title, subtitle, chapter ?? "", detail ?? "", source ?? ""].joined(separator: "|") }
}
private struct SourceClip: Decodable {
    let video: String, caption: String
    let crop_xywh: [Double]
}
private struct Plan: Decodable {
    let output: String, audio: String, music_credit: String, visual_credit: String
    let sources: [String: SourceClip]
    let intro_notice: String, outro_notice: String
    let audio_start: Double
    let audio_volume: Float
    let hero_asset: String
    let safety_asset: String
    let hero_title: String
    let hero_caption: String
    let segments: [Shot]
}
private struct Overlay { let shot: Shot, start: Double; var duration: Double }

private func text(_ value: String, _ rect: NSRect, _ size: CGFloat, _ color: NSColor,
                  _ weight: NSFont.Weight = .regular, center: Bool = false, line: CGFloat? = nil) {
    let p = NSMutableParagraphStyle()
    p.alignment = center ? .center : .left
    if let line { p.minimumLineHeight = line; p.maximumLineHeight = line }
    NSAttributedString(string: value, attributes: [.font: NSFont.systemFont(ofSize: size, weight: weight),
        .foregroundColor: color, .paragraphStyle: p]).draw(in: rect)
}
private func rounded(_ r: NSRect, _ color: NSColor, radius: CGFloat = 18) {
    color.setFill(); NSBezierPath(roundedRect: r, xRadius: radius, yRadius: radius).fill()
}
private func bitmap(_ draw: () -> Void) -> CGImage {
    let b = NSBitmapImageRep(bitmapDataPlanes: nil, pixelsWide: Int(W), pixelsHigh: Int(H),
        bitsPerSample: 8, samplesPerPixel: 4, hasAlpha: true, isPlanar: false,
        colorSpaceName: .deviceRGB, bytesPerRow: 0, bitsPerPixel: 0)!
    NSGraphicsContext.saveGraphicsState()
    NSGraphicsContext.current = NSGraphicsContext(bitmapImageRep: b)
    draw()
    NSGraphicsContext.restoreGraphicsState()
    return b.cgImage!
}
private func overlayImage(_ shot: Shot, credit: String, hero: String, safety: String, visualCredit: String, heroTitle: String, heroCaption: String, sourceCaption: String, introNotice: String, outroNotice: String) -> CGImage {
    bitmap {
        if shot.kind == "video" {
            pale.setFill(); NSRect(x: 0, y: 0, width: W, height: H).fill()
            NSGraphicsContext.current!.cgContext.clear(appRect)
            NSColor(srgbRed: 0.84, green: 0.88, blue: 0.94, alpha: 1).setStroke()
            let border = NSBezierPath(rect: appRect.insetBy(dx: -1, dy: -1)); border.lineWidth = 1; border.stroke()
            text("CarCue", NSRect(x: 64, y: 958, width: 320, height: 60), 38, blue, .bold)
            text("APP PREVIEW", NSRect(x: 66, y: 916, width: 320, height: 30), 16, muted, .medium)
            rounded(NSRect(x: 64, y: 822, width: 320, height: 44), NSColor.white, radius: 12)
            text(shot.chapter ?? "", NSRect(x: 80, y: 829, width: 290, height: 30), 20, blue, .semibold)
            text(shot.title, NSRect(x: 64, y: 566, width: 330, height: 190), 48, ink, .bold, line: 65)
            text(shot.subtitle, NSRect(x: 66, y: 352, width: 322, height: 170), 25, muted, line: 40)
            if let detail = shot.detail {
                rounded(NSRect(x: 64, y: 286, width: 320, height: 44), NSColor(srgbRed: 1, green: 0.95, blue: 0.84, alpha: 1), radius: 10)
                text(detail, NSRect(x: 80, y: 294, width: 295, height: 30), 19, NSColor(srgbRed: 0.54, green: 0.30, blue: 0.05, alpha: 1), .medium)
            }
            text(sourceCaption, NSRect(x: 64, y: 24, width: 760, height: 30), 18, muted)
            text(visualCredit, NSRect(x: 832, y: 53, width: 1030, height: 20), 14, muted)
            text(credit, NSRect(x: 832, y: 28, width: 1030, height: 24), 15, muted)
        } else if shot.kind == "intro" {
            NSColor.white.setFill(); NSRect(x: 0, y: 0, width: W, height: H).fill()
            let panel = NSRect(x: 1140, y: 166, width: 620, height: 740)
            rounded(panel, .white, radius: 52)
            pale.setStroke(); let outline = NSBezierPath(roundedRect: panel, xRadius: 52, yRadius: 52)
            outline.lineWidth = 3; outline.stroke()
            let car = NSImage(contentsOfFile: hero)!
            let carHeight = 552 * car.size.height / car.size.width
            car.draw(in: NSRect(x: 1174, y: 342 + (430 - carHeight) / 2, width: 552, height: carHeight))
            let belt = NSImage(contentsOfFile: safety)!
            belt.draw(in: NSRect(x: 1330, y: 760, width: 240, height: 240 * belt.size.height / belt.size.width))
            text(heroTitle, NSRect(x: 1180, y: 278, width: 540, height: 44), 26, blue, .semibold, center: true)
            text(heroCaption, NSRect(x: 1180, y: 240, width: 540, height: 30), 17, muted, center: true)
            text("CarCue", NSRect(x: 112, y: 884, width: 800, height: 100), 70, blue, .bold)
            text(shot.title, NSRect(x: 112, y: 477, width: 960, height: 260), 83, ink, .bold, line: 112)
            text(shot.subtitle, NSRect(x: 118, y: 343, width: 920, height: 70), 34, muted)
            rounded(NSRect(x: 116, y: 211, width: 420, height: 56), pale, radius: 14)
            text("한국어  ·  English  ·  日本語", NSRect(x: 134, y: 223, width: 396, height: 34), 24, blue, .medium)
            text(introNotice, NSRect(x: 116, y: 80, width: 1000, height: 40), 22, muted)
            text(visualCredit, NSRect(x: 116, y: 58, width: 1680, height: 20), 14, muted)
            text(credit, NSRect(x: 116, y: 28, width: 1680, height: 30), 18, muted)
        } else {
            NSGradient(starting: blue, ending: NSColor(srgbRed: 0.06, green: 0.22, blue: 0.69, alpha: 1))!.draw(in: NSRect(x: 0, y: 0, width: W, height: H), angle: -25)
            text("CarCue", NSRect(x: 180, y: 802, width: 1560, height: 120), 78, .white, .bold, center: true)
            text(shot.title, NSRect(x: 220, y: 428, width: 1480, height: 270), 83, .white, .bold, center: true, line: 114)
            text(shot.subtitle, NSRect(x: 220, y: 284, width: 1480, height: 60), 32, .white, .medium, center: true)
            text(outroNotice, NSRect(x: 220, y: 103, width: 1480, height: 50), 22, NSColor.white.withAlphaComponent(0.8), center: true)
            text(visualCredit, NSRect(x: 150, y: 18, width: 1620, height: 22), 14, NSColor.white.withAlphaComponent(0.85), center: true)
            text(credit, NSRect(x: 150, y: 42, width: 1620, height: 35), 18, NSColor.white.withAlphaComponent(0.85), center: true)
        }
    }
}

private func blankMovie(_ url: URL, duration: Double) async throws {
    guard !FileManager.default.fileExists(atPath: url.path) else { throw fail("Refusing to overwrite blank source") }
    let writer = try AVAssetWriter(outputURL: url, fileType: .mp4)
    let input = AVAssetWriterInput(mediaType: .video, outputSettings: [AVVideoCodecKey: AVVideoCodecType.h264,
        AVVideoWidthKey: Int(W), AVVideoHeightKey: Int(H)])
    let adaptor = AVAssetWriterInputPixelBufferAdaptor(assetWriterInput: input, sourcePixelBufferAttributes: [
        kCVPixelBufferPixelFormatTypeKey as String: kCVPixelFormatType_32ARGB,
        kCVPixelBufferWidthKey as String: Int(W), kCVPixelBufferHeightKey as String: Int(H)])
    writer.add(input); guard writer.startWriting() else { throw writer.error! }; writer.startSession(atSourceTime: .zero)
    var b: CVPixelBuffer?; CVPixelBufferPoolCreatePixelBuffer(nil, adaptor.pixelBufferPool!, &b)
    let pixels = b!; CVPixelBufferLockBaseAddress(pixels, [])
    let context = CGContext(data: CVPixelBufferGetBaseAddress(pixels), width: Int(W), height: Int(H), bitsPerComponent: 8,
        bytesPerRow: CVPixelBufferGetBytesPerRow(pixels), space: CGColorSpaceCreateDeviceRGB(), bitmapInfo: CGImageAlphaInfo.noneSkipFirst.rawValue)!
    context.setFillColor(pale.cgColor); context.fill(CGRect(x: 0, y: 0, width: W, height: H))
    CVPixelBufferUnlockBaseAddress(pixels, [])
    for frame in 0..<Int(duration * 30) {
        while !input.isReadyForMoreMediaData { try await Task.sleep(nanoseconds: 2_000_000) }
        guard adaptor.append(pixels, withPresentationTime: CMTime(value: Int64(frame), timescale: 30)) else { throw writer.error! }
    }
    writer.endSession(atSourceTime: CMTime(seconds: duration, preferredTimescale: 600)); input.markAsFinished()
    await writer.finishWriting()
    guard writer.status == .completed else { throw writer.error! }
}

private func fileURL(_ path: String) -> URL {
    path.hasPrefix("/") ? URL(fileURLWithPath: path) : URL(fileURLWithPath: FileManager.default.currentDirectoryPath).appendingPathComponent(path)
}
private func fail(_ text: String) -> NSError { NSError(domain: "CarCueSDKIntro", code: 1, userInfo: [NSLocalizedDescriptionKey: text]) }
private func probe(_ path: String) async throws {
    let asset = AVURLAsset(url: fileURL(path))
    guard let track = try await asset.loadTracks(withMediaType: .video).first else { throw fail("No video track") }
    let size = try await track.load(.naturalSize)
    let fps = try await track.load(.nominalFrameRate)
    let duration = CMTimeGetSeconds(try await asset.load(.duration))
    let audio = try await asset.loadTracks(withMediaType: .audio)
    let data = try JSONSerialization.data(withJSONObject: ["width": size.width, "height": size.height, "fps": fps, "duration_seconds": duration, "audio_tracks": audio.count], options: [.sortedKeys])
    print(String(decoding: data, as: UTF8.self))
}
private func frame(_ path: String, _ seconds: Double, _ output: String) async throws {
    let target = fileURL(output)
    guard !FileManager.default.fileExists(atPath: target.path) else { throw fail("Refusing to overwrite frame") }
    let generator = AVAssetImageGenerator(asset: AVURLAsset(url: fileURL(path)))
    generator.appliesPreferredTrackTransform = true
    generator.requestedTimeToleranceBefore = .zero; generator.requestedTimeToleranceAfter = .zero
    let (cg, _) = try await generator.image(at: CMTime(seconds: seconds, preferredTimescale: 600))
    let bitmap = NSBitmapImageRep(cgImage: cg)
    guard let png = bitmap.representation(using: .png, properties: [:]) else { throw fail("Cannot encode frame") }
    try png.write(to: target, options: .withoutOverwriting)
}
private func pcm(_ path: String, _ output: String) async throws {
    let target = fileURL(output)
    guard !FileManager.default.fileExists(atPath: target.path) else { throw fail("Refusing to overwrite PCM") }
    let asset = AVURLAsset(url: fileURL(path))
    let tracks = try await asset.loadTracks(withMediaType: .audio)
    guard !tracks.isEmpty else { throw fail("No audio track") }
    let reader = try AVAssetReader(asset: asset)
    let audio = AVAssetReaderAudioMixOutput(audioTracks: tracks, audioSettings: [
        AVFormatIDKey: kAudioFormatLinearPCM, AVSampleRateKey: 44100,
        AVNumberOfChannelsKey: 2, AVLinearPCMBitDepthKey: 16,
        AVLinearPCMIsFloatKey: false, AVLinearPCMIsBigEndianKey: false,
        AVLinearPCMIsNonInterleaved: false])
    reader.add(audio)
    guard reader.startReading() else { throw reader.error ?? fail("Cannot start audio decode") }
    var bytes = Data()
    while let sample = audio.copyNextSampleBuffer() {
        guard let block = CMSampleBufferGetDataBuffer(sample) else { throw fail("Missing PCM buffer") }
        let size = CMBlockBufferGetDataLength(block)
        var chunk = [UInt8](repeating: 0, count: size)
        let status = chunk.withUnsafeMutableBytes { CMBlockBufferCopyDataBytes(block, atOffset: 0, dataLength: size, destination: $0.baseAddress!) }
        guard status == kCMBlockBufferNoErr else { throw fail("Cannot copy PCM") }
        bytes.append(contentsOf: chunk)
    }
    guard reader.status == .completed else { throw reader.error ?? fail("Incomplete PCM decode") }
    try bytes.write(to: target, options: .withoutOverwriting)
}

// The cleanup renderer is deliberately separate from the original composition
// path. It flattens initialized, opaque frames on the CPU; Core Animation and
// video-composition crop/opacity instructions never enter this export.
private final class NativeDecodedFrame {
    let pixels: CVPixelBuffer
    let time: CMTime
    let index: Int
    private var cachedImage: CGImage?

    init(pixels: CVPixelBuffer, time: CMTime, index: Int) {
        self.pixels = pixels; self.time = time; self.index = index
    }

    func image() throws -> CGImage {
        if let cachedImage { return cachedImage }
        CVPixelBufferLockBaseAddress(pixels, .readOnly)
        defer { CVPixelBufferUnlockBaseAddress(pixels, .readOnly) }
        guard let base = CVPixelBufferGetBaseAddress(pixels),
              let context = CGContext(data: base, width: CVPixelBufferGetWidth(pixels),
                height: CVPixelBufferGetHeight(pixels), bitsPerComponent: 8,
                bytesPerRow: CVPixelBufferGetBytesPerRow(pixels),
                space: CGColorSpace(name: CGColorSpace.sRGB)!,
                bitmapInfo: CGImageAlphaInfo.noneSkipFirst.rawValue | CGBitmapInfo.byteOrder32Little.rawValue),
              let image = context.makeImage() else { throw fail("Cannot create decoded source image") }
        cachedImage = image
        return image
    }
}

private final class NativeFrameStream {
    private let reader: AVAssetReader
    private let output: AVAssetReaderTrackOutput
    private var current: NativeDecodedFrame?
    private var next: NativeDecodedFrame?
    private var decodedCount = 0
    private var lastRequested = CMTime.negativeInfinity

    init(asset: AVURLAsset, track: AVAssetTrack) throws {
        reader = try AVAssetReader(asset: asset)
        output = AVAssetReaderTrackOutput(track: track, outputSettings: [
            kCVPixelBufferPixelFormatTypeKey as String: kCVPixelFormatType_32BGRA])
        output.alwaysCopiesSampleData = false
        guard reader.canAdd(output) else { throw fail("Cannot add source decoder") }
        reader.add(output)
        guard reader.startReading() else { throw reader.error ?? fail("Cannot start source decoder") }
        next = try readNext()
    }

    private func readNext() throws -> NativeDecodedFrame? {
        guard let sample = output.copyNextSampleBuffer() else {
            if reader.status == .failed { throw reader.error ?? fail("Source decode failed") }
            guard reader.status == .completed else { throw fail("Source decode ended unexpectedly") }
            return nil
        }
        guard let pixels = CMSampleBufferGetImageBuffer(sample) else { throw fail("Missing decoded source pixels") }
        let result = NativeDecodedFrame(pixels: pixels,
            time: CMSampleBufferGetPresentationTimeStamp(sample), index: decodedCount)
        decodedCount += 1
        return result
    }

    func frame(at target: CMTime) throws -> NativeDecodedFrame {
        guard CMTimeCompare(target, lastRequested) >= 0 else { throw fail("Cleanup source windows must remain chronological") }
        lastRequested = target
        // Decode sequentially even across omitted windows. This retains only the
        // current and next source frame, and handles arbitrarily long VFR holds
        // without inventing frames or guessing a decoder preroll duration.
        while let candidate = next, CMTimeCompare(candidate.time, target) <= 0 {
            current = candidate
            next = try readNext()
        }
        guard let current else { throw fail("No recorded source frame at or before requested time") }
        return current
    }

    func close() { reader.cancelReading() }
}

private func renderClean(_ planPath: String, _ workPath: String, _ audioReferencePath: String) async throws {
    let plan = try JSONDecoder().decode(Plan.self, from: Data(contentsOf: fileURL(planPath)))
    let work = fileURL(workPath), outputURL = fileURL(plan.output)
    guard FileManager.default.fileExists(atPath: work.path),
          try FileManager.default.contentsOfDirectory(atPath: work.path).isEmpty else { throw fail("Cleanup work directory must be empty") }
    guard !FileManager.default.fileExists(atPath: outputURL.path) else { throw fail("Refusing to overwrite video") }
    let shotFrameCounts = try plan.segments.map { shot -> Int in
        let frames = shot.duration * 30
        guard frames.isFinite, frames > 0, abs(frames.rounded() - frames) < 0.000001 else {
            throw fail("Cleanup shot duration must contain whole 30fps frames")
        }
        return Int(frames.rounded())
    }
    let frameCount = shotFrameCounts.reduce(0, +)
    guard frameCount == 1020 else { throw fail("Cleanup requires the existing 34-second plan") }
    let duration = CMTime(value: Int64(frameCount), timescale: 30)
    var streams = [String: NativeFrameStream]()
    defer { for stream in streams.values { stream.close() } }
    for (name, clip) in plan.sources {
        let asset = AVURLAsset(url: fileURL(clip.video))
        guard let track = try await asset.loadTracks(withMediaType: .video).first else { throw fail("Missing cleanup source track") }
        let size = try await track.load(.naturalSize), crop = clip.crop_xywh
        let transform = try await track.load(.preferredTransform)
        guard transform.isIdentity, crop.count == 4, crop.allSatisfy({ $0.isFinite }),
              crop[0] >= 0, crop[1] >= 0, crop[2] > 0, crop[3] > 0,
              crop[0] + crop[2] <= size.width, crop[1] + crop[3] <= size.height else {
            throw fail("Invalid cleanup source crop or orientation")
        }
        let sourceDuration = CMTimeGetSeconds(try await asset.load(.duration))
        for shot in plan.segments where shot.kind == "video" && shot.source == name {
            guard let start = shot.start, start.isFinite, start >= 0,
                  start + shot.duration <= sourceDuration else { throw fail("Cleanup cut outside recording") }
        }
        streams[name] = try NativeFrameStream(asset: asset, track: track)
    }

    let videoOnly = work.appendingPathComponent("opaque-video-only.mp4")
    let writer = try AVAssetWriter(outputURL: videoOnly, fileType: .mp4)
    let input = AVAssetWriterInput(mediaType: .video, outputSettings: [
        AVVideoCodecKey: AVVideoCodecType.h264, AVVideoWidthKey: Int(W), AVVideoHeightKey: Int(H),
        AVVideoCompressionPropertiesKey: [AVVideoAverageBitRateKey: 12_000_000,
            AVVideoProfileLevelKey: AVVideoProfileLevelH264HighAutoLevel,
            AVVideoExpectedSourceFrameRateKey: 30, AVVideoMaxKeyFrameIntervalKey: 30,
            AVVideoAllowFrameReorderingKey: false],
        AVVideoColorPropertiesKey: [AVVideoColorPrimariesKey: AVVideoColorPrimaries_ITU_R_709_2,
            AVVideoTransferFunctionKey: AVVideoTransferFunction_ITU_R_709_2,
            AVVideoYCbCrMatrixKey: AVVideoYCbCrMatrix_ITU_R_709_2]])
    input.expectsMediaDataInRealTime = false
    input.mediaTimeScale = 30
    let adaptor = AVAssetWriterInputPixelBufferAdaptor(assetWriterInput: input, sourcePixelBufferAttributes: [
        kCVPixelBufferPixelFormatTypeKey as String: kCVPixelFormatType_32BGRA,
        kCVPixelBufferWidthKey as String: Int(W), kCVPixelBufferHeightKey as String: Int(H),
        kCVPixelBufferCGImageCompatibilityKey as String: true,
        kCVPixelBufferCGBitmapContextCompatibilityKey as String: true])
    guard writer.canAdd(input) else { throw fail("Cannot add cleanup encoder") }
    writer.add(input)
    guard writer.startWriting() else { throw writer.error ?? fail("Cannot start cleanup encoder") }
    writer.startSession(atSourceTime: .zero)
    var mappings = [[String: Any]](), outputFrame = 0
    let colorSpace = CGColorSpace(name: CGColorSpace.sRGB)!
    for (shotIndex, shot) in plan.segments.enumerated() {
        let overlay = overlayImage(shot, credit: plan.music_credit, hero: plan.hero_asset,
            safety: plan.safety_asset, visualCredit: plan.visual_credit, heroTitle: plan.hero_title,
            heroCaption: plan.hero_caption, sourceCaption: plan.sources[shot.source ?? ""]?.caption ?? "",
            introNotice: plan.intro_notice, outroNotice: plan.outro_notice)
        var previousSourceIndex: Int?, croppedImage: CGImage?
        for localFrame in 0..<shotFrameCounts[shotIndex] {
            while !input.isReadyForMoreMediaData {
                guard writer.status == .writing else { throw writer.error ?? fail("Cleanup encoder stopped") }
                try await Task.sleep(nanoseconds: 2_000_000)
            }
            try autoreleasepool {
                var buffer: CVPixelBuffer?
                guard let pool = adaptor.pixelBufferPool,
                      CVPixelBufferPoolCreatePixelBuffer(nil, pool, &buffer) == kCVReturnSuccess,
                      let buffer else { throw fail("Cannot allocate cleanup frame") }
                CVPixelBufferLockBaseAddress(buffer, [])
                var bufferLocked = true
                defer { if bufferLocked { CVPixelBufferUnlockBaseAddress(buffer, []) } }
                guard let base = CVPixelBufferGetBaseAddress(buffer),
                      let context = CGContext(data: base, width: Int(W), height: Int(H), bitsPerComponent: 8,
                        bytesPerRow: CVPixelBufferGetBytesPerRow(buffer), space: colorSpace,
                        bitmapInfo: CGImageAlphaInfo.premultipliedFirst.rawValue | CGBitmapInfo.byteOrder32Little.rawValue) else {
                    throw fail("Cannot initialize cleanup frame context")
                }
                // Fill every byte used by the image, including alpha, before drawing.
                memset(base, 0, CVPixelBufferGetDataSize(buffer))
                context.setFillColor(pale.cgColor)
                context.fill(CGRect(x: 0, y: 0, width: W, height: H))
                context.interpolationQuality = .high
                if shot.kind == "video" {
                    guard let name = shot.source, let clip = plan.sources[name],
                          let stream = streams[name], let start = shot.start else { throw fail("Missing cleanup shot source") }
                    let requested = start + Double(localFrame) / 30
                    let native = try stream.frame(at: CMTime(seconds: requested, preferredTimescale: 600_000))
                    let c = clip.crop_xywh
                    if previousSourceIndex != native.index {
                        croppedImage = try native.image().cropping(to: CGRect(x: c[0], y: c[1], width: c[2], height: c[3]))
                        previousSourceIndex = native.index
                    }
                    guard let croppedImage else { throw fail("Cannot crop recorded source frame") }
                    let scale = min(appRect.width / c[2], appRect.height / c[3])
                    let destination = CGRect(x: appRect.minX + (appRect.width - c[2] * scale) / 2,
                        y: appRect.minY + (appRect.height - c[3] * scale) / 2,
                        width: c[2] * scale, height: c[3] * scale)
                    context.setFillColor(NSColor.black.cgColor); context.fill(appRect)
                    context.draw(croppedImage, in: destination)
                    mappings.append(["output_frame": outputFrame, "output_seconds": Double(outputFrame) / 30,
                        "shot_index": shotIndex, "source": name, "requested_source_seconds": requested,
                        "recorded_frame_index": native.index,
                        "recorded_frame_seconds": CMTimeGetSeconds(native.time)])
                }
                context.draw(overlay, in: CGRect(x: 0, y: 0, width: W, height: H))
                CVPixelBufferUnlockBaseAddress(buffer, [])
                bufferLocked = false
                guard adaptor.append(buffer, withPresentationTime: CMTime(value: Int64(outputFrame), timescale: 30)) else {
                    throw writer.error ?? fail("Cannot append cleanup frame")
                }
            }
            outputFrame += 1
        }
    }
    writer.endSession(atSourceTime: duration); input.markAsFinished()
    await writer.finishWriting()
    guard writer.status == .completed, outputFrame == frameCount else { throw writer.error ?? fail("Incomplete cleanup video") }

    // Copy the already approved soundtrack through the muxer. No audio reader,
    // encoder, gain adjustment or fade operation is used in this path.
    let reference = AVURLAsset(url: fileURL(audioReferencePath))
    let referenceAudio = try await reference.loadTracks(withMediaType: .audio)
    guard referenceAudio.count == 1 else { throw fail("Cleanup requires one existing soundtrack track") }
    let cleanVideo = AVURLAsset(url: videoOnly)
    guard let cleanTrack = try await cleanVideo.loadTracks(withMediaType: .video).first else { throw fail("Missing encoded cleanup video") }
    let composition = AVMutableComposition()
    guard let videoTrack = composition.addMutableTrack(withMediaType: .video, preferredTrackID: kCMPersistentTrackID_Invalid),
          let audioTrack = composition.addMutableTrack(withMediaType: .audio, preferredTrackID: kCMPersistentTrackID_Invalid) else {
        throw fail("Cannot create cleanup mux tracks")
    }
    let range = CMTimeRange(start: .zero, duration: duration)
    try videoTrack.insertTimeRange(range, of: cleanTrack, at: .zero)
    try audioTrack.insertTimeRange(range, of: referenceAudio[0], at: .zero)
    guard let mux = AVAssetExportSession(asset: composition, presetName: AVAssetExportPresetPassthrough) else { throw fail("Cannot create cleanup passthrough muxer") }
    mux.timeRange = range; mux.shouldOptimizeForNetworkUse = true
    try await mux.export(to: outputURL, as: .mp4)
    let map: [String: Any] = ["frame_count": frameCount, "fps": 30, "duration_seconds": 34,
        "frame_selection": "Latest original recorded presentation timestamp at or before requested source time; held frames only, no interpolation.",
        "source_decoder_memory": "One current and one lookahead decoded frame per source; unused frames discarded sequentially.",
        "opaque_cpu_compositing": true, "core_animation_used": false,
        "progress_bar_used": false, "per_cut_opacity_fades_used": false,
        "audio_passthrough_reference": fileURL(audioReferencePath).path, "frames": mappings]
    try JSONSerialization.data(withJSONObject: map, options: [.prettyPrinted, .sortedKeys])
        .write(to: work.appendingPathComponent("source-frame-map.json"), options: .withoutOverwriting)
    print("EXPORTED CLEAN \(frameCount) frames, 34s, 1920×1080, CFR30; original recorded frames and passthrough soundtrack")
}

@main struct SDKIntro {
    static func main() async throws {
        let args = CommandLine.arguments
        guard args.count >= 3 else { throw fail("Usage: render PLAN WORK | probe VIDEO | frame VIDEO SECONDS PNG | pcm VIDEO PCM") }
        switch args[1] {
        case "probe": try await probe(args[2]); return
        case "frame":
            guard args.count == 5, let seconds = Double(args[3]), seconds >= 0 else { throw fail("Invalid frame arguments") }
            try await frame(args[2], seconds, args[4]); return
        case "pcm":
            guard args.count == 4 else { throw fail("Invalid PCM arguments") }
            try await pcm(args[2], args[3]); return
        case "render-clean":
            guard args.count == 5 else { throw fail("Usage: render-clean PLAN WORK AUDIO_REFERENCE") }
            try await renderClean(args[2], args[3], args[4]); return
        case "render": break
        default: throw fail("Unknown operation")
        }
        guard args.count == 4 else { throw fail("Render requires plan and a new work directory") }
        let plan = try JSONDecoder().decode(Plan.self, from: Data(contentsOf: fileURL(args[2])))
        let work = fileURL(args[3])
        guard FileManager.default.fileExists(atPath: work.path), try FileManager.default.contentsOfDirectory(atPath: work.path).isEmpty else { throw fail("Render work directory must be empty") }
        var tracks = [String: AVAssetTrack](), durations = [String: Double]()
        var assets = [String: AVURLAsset]()
        for (name, clip) in plan.sources {
            let asset = AVURLAsset(url: fileURL(clip.video))
            let track = try await asset.loadTracks(withMediaType: .video).first!
            let size = try await track.load(.naturalSize), crop = clip.crop_xywh
            precondition(crop.count == 4 && crop[0] >= 0 && crop[1] >= 0 && crop[2] > 0 && crop[3] > 0)
            precondition(crop[0]+crop[2] <= size.width && crop[1]+crop[3] <= size.height)
            assets[name] = asset; tracks[name] = track
            durations[name] = CMTimeGetSeconds(try await asset.load(.duration))
        }
        let blank = work.appendingPathComponent("blank.mp4")
        try await blankMovie(blank, duration: 3)
        let blankAsset = AVURLAsset(url: blank)
        let blankTrack = try await blankAsset.loadTracks(withMediaType: .video).first!
        let composition = AVMutableComposition()
        let videoTrack = composition.addMutableTrack(withMediaType: .video, preferredTrackID: kCMPersistentTrackID_Invalid)!
        var instructions = [AVMutableVideoCompositionInstruction]()
        var overlays = [Overlay](); var cursor = 0.0
        for shot in plan.segments {
            let at = CMTime(seconds: cursor, preferredTimescale: 600), duration = CMTime(seconds: shot.duration, preferredTimescale: 600)
            let native = shot.kind == "video"
            if native { precondition(shot.start! >= 0 && shot.start! + shot.duration <= durations[shot.source!]!) }
            try videoTrack.insertTimeRange(CMTimeRange(start: CMTime(seconds: native ? shot.start! : 0, preferredTimescale: 600), duration: duration), of: native ? tracks[shot.source!]! : blankTrack, at: at)
            let layer = AVMutableVideoCompositionLayerInstruction(assetTrack: videoTrack)
            if native {
                let c = plan.sources[shot.source!]!.crop_xywh
                let crop = CGRect(x: c[0], y: c[1], width: c[2], height: c[3])
                let scale = min(appRect.width/crop.width, appRect.height/crop.height)
                let x = appRect.minX + (appRect.width-crop.width*scale)/2 - crop.minX*scale
                let y = H-appRect.maxY + (appRect.height-crop.height*scale)/2 - crop.minY*scale
                // The installed AVFoundation header specifies clean-aperture,
                // top-left source coordinates for the crop, before transformation.
                layer.setCropRectangle(crop, at: at)
                layer.setTransform(CGAffineTransform(scaleX: scale, y: scale).concatenating(CGAffineTransform(translationX: x, y: y)), at: at)
                layer.setOpacityRamp(fromStartOpacity: 0, toEndOpacity: 1, timeRange: CMTimeRange(start: at, duration: CMTime(seconds: 0.13, preferredTimescale: 600)))
                layer.setOpacityRamp(fromStartOpacity: 1, toEndOpacity: 0, timeRange: CMTimeRange(start: at + duration - CMTime(seconds: 0.10, preferredTimescale: 600), duration: CMTime(seconds: 0.10, preferredTimescale: 600)))
            } else { layer.setTransform(.identity, at: at) }
            let instruction = AVMutableVideoCompositionInstruction()
            instruction.timeRange = CMTimeRange(start: at, duration: duration); instruction.layerInstructions = [layer]
            instruction.backgroundColor = NSColor.white.cgColor; instructions.append(instruction)
            if let last = overlays.last, last.shot.key == shot.key {
                overlays[overlays.count - 1].duration += shot.duration
            } else { overlays.append(Overlay(shot: shot, start: cursor, duration: shot.duration)) }
            print("\(cursor)–\(cursor + shot.duration) \(shot.kind): \(shot.chapter ?? "CarCue")")
            cursor += shot.duration
        }
        let soundAsset = AVURLAsset(url: fileURL(plan.audio))
        let soundSource = try await soundAsset.loadTracks(withMediaType: .audio).first!
        let soundTrack = composition.addMutableTrack(withMediaType: .audio, preferredTrackID: kCMPersistentTrackID_Invalid)!
        try soundTrack.insertTimeRange(CMTimeRange(start: CMTime(seconds: plan.audio_start, preferredTimescale: 600), duration: CMTime(seconds: cursor, preferredTimescale: 600)), of: soundSource, at: .zero)
        let volume = AVMutableAudioMixInputParameters(track: soundTrack)
        volume.setVolume(plan.audio_volume, at: .zero)
        volume.setVolumeRamp(fromStartVolume: 0, toEndVolume: plan.audio_volume, timeRange: CMTimeRange(start: .zero, duration: CMTime(seconds: 0.8, preferredTimescale: 600)))
        volume.setVolumeRamp(fromStartVolume: plan.audio_volume, toEndVolume: 0, timeRange: CMTimeRange(start: CMTime(seconds: cursor - 1.4, preferredTimescale: 600), duration: CMTime(seconds: 1.4, preferredTimescale: 600)))
        let audioMix = AVMutableAudioMix(); audioMix.inputParameters = [volume]
        let parent = CALayer(); parent.frame = CGRect(x: 0, y: 0, width: W, height: H); parent.backgroundColor = pale.cgColor
        let renderedVideo = CALayer(); renderedVideo.frame = parent.bounds; parent.addSublayer(renderedVideo)
        for overlay in overlays {
            let layer = CALayer(); layer.frame = parent.bounds; layer.contents = overlayImage(overlay.shot, credit: plan.music_credit, hero: plan.hero_asset, safety: plan.safety_asset, visualCredit: plan.visual_credit, heroTitle: plan.hero_title, heroCaption: plan.hero_caption, sourceCaption: plan.sources[overlay.shot.source ?? ""]?.caption ?? "", introNotice: plan.intro_notice, outroNotice: plan.outro_notice); layer.opacity = 0
            let s = overlay.start / cursor, end = (overlay.start + overlay.duration) / cursor, fade = 0.14 / cursor
            let animation = CAKeyframeAnimation(keyPath: "opacity")
            if overlay.shot.kind == "outro" {
                animation.keyTimes = [0, NSNumber(value: s), NSNumber(value: s+fade), 1]
                animation.values = [0, 0, 1, 1]
            } else if overlay.start == 0 {
                animation.keyTimes = [0, NSNumber(value: fade), NSNumber(value: end-fade), NSNumber(value: end), 1]
                animation.values = [1, 1, 1, 0, 0]
            } else {
                animation.keyTimes = [0, NSNumber(value: s), NSNumber(value: s+fade), NSNumber(value: end-fade), NSNumber(value: end), 1]
                animation.values = [0, 0, 1, 1, 0, 0]
            }
            animation.beginTime = AVCoreAnimationBeginTimeAtZero; animation.duration = cursor
            animation.isRemovedOnCompletion = false; animation.fillMode = .both
            layer.add(animation, forKey: "chapterFade"); parent.addSublayer(layer)
        }
        let progress = CALayer(); progress.frame = CGRect(x: 0, y: 0, width: W, height: 5); progress.backgroundColor = blue.cgColor
        progress.anchorPoint = CGPoint(x: 0, y: 0.5); progress.position = CGPoint(x: 0, y: 2.5)
        let growth = CABasicAnimation(keyPath: "transform.scale.x"); growth.fromValue = 0; growth.toValue = 1
        growth.beginTime = AVCoreAnimationBeginTimeAtZero; growth.duration = cursor; growth.isRemovedOnCompletion = false; growth.fillMode = .both
        progress.add(growth, forKey: "progress"); parent.addSublayer(progress)
        let video = AVMutableVideoComposition(); video.renderSize = CGSize(width: W, height: H); video.frameDuration = CMTime(value: 1, timescale: 30)
        video.instructions = instructions; video.animationTool = AVVideoCompositionCoreAnimationTool(postProcessingAsVideoLayer: renderedVideo, in: parent)
        let output = fileURL(plan.output)
        guard !FileManager.default.fileExists(atPath: output.path) else { throw fail("Refusing to overwrite video") }
        let export = AVAssetExportSession(asset: composition, presetName: AVAssetExportPresetHighestQuality)!
        export.videoComposition = video; export.audioMix = audioMix; export.shouldOptimizeForNetworkUse = true
        try await export.export(to: output, as: .mp4)
        print("EXPORTED \(cursor)s, 1920×1080, 30fps, licensed external music")
    }
}
