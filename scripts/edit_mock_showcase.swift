// macOS AVFoundation editor. Sources and exact two-second cuts are listed in the JSON plan.
import Foundation
import AVFoundation
import AppKit
import QuartzCore

struct Segment: Decodable {
    let label: String
    let kind: String
    let source: String
    let start: Double?
    let caption: String?
    let crop: [Double]?
}
struct Plan: Decodable {
    let seconds_per_scene: Double
    let output: String
    let segments: [Segment]
}

func require(_ value: Bool, _ message: String) throws {
    if !value { throw NSError(domain: "CarCueVideo", code: 1, userInfo: [NSLocalizedDescriptionKey: message]) }
}

@main struct Editor {
    static func main() async throws {
        let planURL = URL(fileURLWithPath: CommandLine.arguments[1])
        let plan = try JSONDecoder().decode(Plan.self, from: Data(contentsOf: planURL))
        let root = URL(fileURLWithPath: FileManager.default.currentDirectoryPath, isDirectory: true)
        let work = root.appendingPathComponent("output/qa/short-video-work", isDirectory: true)
        try FileManager.default.createDirectory(at: work, withIntermediateDirectories: true)
        let composition = AVMutableComposition()
        let track = composition.addMutableTrack(withMediaType: .video, preferredTrackID: kCMPersistentTrackID_Invalid)!
        let duration = CMTime(seconds: plan.seconds_per_scene, preferredTimescale: 600)
        var position = CMTime.zero
        let canvas = CGSize(width: 1280, height: 800)
        var instructions = [AVMutableVideoCompositionInstruction]()
        var captions = [(Double, String)]()

        for (index, segment) in plan.segments.enumerated() {
            var source = root.appendingPathComponent(segment.source)
            if segment.kind == "image" {
                let movie = work.appendingPathComponent("image-\(index).mp4")
                try await stillMovie(image: source, caption: segment.caption, output: movie, duration: plan.seconds_per_scene)
                source = movie
            }
            let asset = AVURLAsset(url: source)
            let input = try await asset.loadTracks(withMediaType: .video).first!
            let start = CMTime(seconds: segment.start ?? 0, preferredTimescale: 600)
            let sourceDuration = try await asset.load(.duration)
            try require(CMTimeCompare(start + duration, sourceDuration) <= 0, "Cut beyond source: \(segment.label)")
            try track.insertTimeRange(CMTimeRange(start: start, duration: duration), of: input, at: position)
            let size = try await input.load(.naturalSize)
            var sourceRect = CGRect(origin: .zero, size: size)
            if let crop = segment.crop {
                try require(crop.count == 4, "Crop must have x, y, width, height")
                sourceRect = CGRect(x: crop[0], y: crop[1], width: crop[2], height: crop[3])
                try require(CGRect(origin: .zero, size: size).contains(sourceRect), "Crop outside source")
            }
            let scale = min(canvas.width / sourceRect.width, canvas.height / sourceRect.height)
            let transform = CGAffineTransform(translationX: -sourceRect.minX, y: -sourceRect.minY)
                .concatenating(CGAffineTransform(scaleX: scale, y: scale))
                .concatenating(CGAffineTransform(
                    translationX: (canvas.width - sourceRect.width * scale) / 2,
                    y: (canvas.height - sourceRect.height * scale) / 2))
            let layer = AVMutableVideoCompositionLayerInstruction(assetTrack: track)
            if segment.crop != nil { layer.setCropRectangle(sourceRect, at: position) }
            layer.setTransform(transform, at: position)
            if segment.kind == "video", let caption = segment.caption {
                captions.append((CMTimeGetSeconds(position), caption))
            }
            let instruction = AVMutableVideoCompositionInstruction()
            instruction.timeRange = CMTimeRange(start: position, duration: duration)
            instruction.backgroundColor = NSColor.white.cgColor
            instruction.layerInstructions = [layer]
            instructions.append(instruction)
            print("\(CMTimeGetSeconds(position))–\(CMTimeGetSeconds(position + duration)): \(segment.label)")
            position = position + duration
        }
        let video = AVMutableVideoComposition()
        video.renderSize = canvas
        video.frameDuration = CMTime(value: 1, timescale: 30)
        video.instructions = instructions
        if !captions.isEmpty {
            let parent = CALayer()
            parent.frame = CGRect(origin: .zero, size: canvas)
            let videoLayer = CALayer()
            videoLayer.frame = parent.bounds
            parent.addSublayer(videoLayer)
            let seconds = CMTimeGetSeconds(position)
            for (start, caption) in captions {
                let band = CALayer()
                band.frame = CGRect(x: 0, y: 0, width: 1280, height: 80)
                band.opacity = 0
                // Rasterize the video caption with AppKit so the export process
                // does not depend on CATextLayer's headless font resolution.
                let bitmap = NSBitmapImageRep(bitmapDataPlanes: nil, pixelsWide: 1280, pixelsHigh: 80,
                    bitsPerSample: 8, samplesPerPixel: 4, hasAlpha: true, isPlanar: false,
                    colorSpaceName: .deviceRGB, bytesPerRow: 0, bitsPerPixel: 0)!
                NSGraphicsContext.saveGraphicsState()
                NSGraphicsContext.current = NSGraphicsContext(bitmapImageRep: bitmap)
                NSColor.white.setFill()
                NSBezierPath(rect: NSRect(x: 0, y: 0, width: 1280, height: 80)).fill()
                let style = NSMutableParagraphStyle()
                style.alignment = .center
                NSAttributedString(string: caption, attributes: [
                    .font: NSFont.systemFont(ofSize: 26, weight: .semibold),
                    .foregroundColor: NSColor(srgbRed: 0.08, green: 0.13, blue: 0.20, alpha: 1),
                    .paragraphStyle: style
                ]).draw(in: NSRect(x: 24, y: 14, width: 1232, height: 48))
                NSGraphicsContext.restoreGraphicsState()
                band.contents = bitmap.cgImage
                let visibility = CAKeyframeAnimation(keyPath: "opacity")
                if start == 0 {
                    visibility.keyTimes = [0, NSNumber(value: plan.seconds_per_scene / seconds), 1]
                    visibility.values = [1, 0, 0]
                } else {
                    visibility.keyTimes = [0, NSNumber(value: start / seconds), NSNumber(value: (start + plan.seconds_per_scene) / seconds), 1]
                    visibility.values = [0, 1, 0, 0]
                }
                visibility.calculationMode = .discrete
                visibility.beginTime = AVCoreAnimationBeginTimeAtZero
                visibility.duration = seconds
                visibility.isRemovedOnCompletion = false
                visibility.fillMode = .both
                band.add(visibility, forKey: "sourceCaption")
                parent.addSublayer(band)
            }
            video.animationTool = AVVideoCompositionCoreAnimationTool(postProcessingAsVideoLayer: videoLayer, in: parent)
        }
        let output = root.appendingPathComponent(plan.output)
        if FileManager.default.fileExists(atPath: output.path) { try FileManager.default.removeItem(at: output) }
        let session = AVAssetExportSession(asset: composition, presetName: AVAssetExportPresetHighestQuality)!
        session.videoComposition = video
        session.shouldOptimizeForNetworkUse = true
        try await session.export(to: output, as: .mp4)
        print("EXPORTED \(output.path) · \(CMTimeGetSeconds(position)) seconds")
    }

    static func stillMovie(image url: URL, caption: String?, output: URL, duration: Double) async throws {
        let image = NSImage(contentsOf: url)!
        let bitmap = NSBitmapImageRep(bitmapDataPlanes: nil, pixelsWide: 1280, pixelsHigh: 800,
            bitsPerSample: 8, samplesPerPixel: 4, hasAlpha: true, isPlanar: false,
            colorSpaceName: .deviceRGB, bytesPerRow: 0, bitsPerPixel: 0)!
        NSGraphicsContext.saveGraphicsState()
        NSGraphicsContext.current = NSGraphicsContext(bitmapImageRep: bitmap)
        NSColor.white.setFill()
        NSBezierPath(rect: NSRect(x: 0, y: 0, width: 1280, height: 800)).fill()
        let area = caption == nil ? NSRect(x: 0, y: 0, width: 1280, height: 800) : NSRect(x: 64, y: 110, width: 1152, height: 640)
        let scale = min(area.width / image.size.width, area.height / image.size.height)
        let size = NSSize(width: image.size.width * scale, height: image.size.height * scale)
        image.draw(in: NSRect(x: area.midX - size.width / 2, y: area.midY - size.height / 2, width: size.width, height: size.height))
        if let caption {
            let style = NSMutableParagraphStyle()
            style.alignment = .center
            let text = NSAttributedString(string: caption, attributes: [
                .font: NSFont.systemFont(ofSize: 26, weight: .semibold),
                .foregroundColor: NSColor(srgbRed: 0.08, green: 0.13, blue: 0.20, alpha: 1),
                .paragraphStyle: style])
            text.draw(in: NSRect(x: 40, y: 28, width: 1200, height: 65))
        }
        NSGraphicsContext.restoreGraphicsState()
        if FileManager.default.fileExists(atPath: output.path) { try FileManager.default.removeItem(at: output) }
        let writer = try AVAssetWriter(outputURL: output, fileType: .mp4)
        let input = AVAssetWriterInput(mediaType: .video, outputSettings: [
            AVVideoCodecKey: AVVideoCodecType.h264, AVVideoWidthKey: 1280, AVVideoHeightKey: 800])
        let adaptor = AVAssetWriterInputPixelBufferAdaptor(assetWriterInput: input, sourcePixelBufferAttributes: [
            kCVPixelBufferPixelFormatTypeKey as String: kCVPixelFormatType_32ARGB,
            kCVPixelBufferWidthKey as String: 1280, kCVPixelBufferHeightKey as String: 800])
        writer.add(input)
        try require(writer.startWriting(), "Cannot start image movie writer")
        writer.startSession(atSourceTime: .zero)
        var buffer: CVPixelBuffer?
        try require(CVPixelBufferPoolCreatePixelBuffer(nil, adaptor.pixelBufferPool!, &buffer) == kCVReturnSuccess, "No frame buffer")
        let pixels = buffer!
        CVPixelBufferLockBaseAddress(pixels, [])
        let context = CGContext(data: CVPixelBufferGetBaseAddress(pixels), width: 1280, height: 800,
            bitsPerComponent: 8, bytesPerRow: CVPixelBufferGetBytesPerRow(pixels), space: CGColorSpaceCreateDeviceRGB(),
            bitmapInfo: CGImageAlphaInfo.noneSkipFirst.rawValue)!
        context.draw(bitmap.cgImage!, in: CGRect(x: 0, y: 0, width: 1280, height: 800))
        CVPixelBufferUnlockBaseAddress(pixels, [])
        for frame in 0..<Int((duration * 30).rounded()) {
            while !input.isReadyForMoreMediaData { try await Task.sleep(nanoseconds: 2_000_000) }
            try require(adaptor.append(pixels, withPresentationTime: CMTime(value: Int64(frame), timescale: 30)), "Cannot write frame")
        }
        writer.endSession(atSourceTime: CMTime(seconds: duration, preferredTimescale: 600))
        input.markAsFinished()
        await writer.finishWriting()
        try require(writer.status == .completed, "Image movie failed: \(String(describing: writer.error))")
    }
}
