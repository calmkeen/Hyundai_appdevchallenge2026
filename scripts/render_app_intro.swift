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
    var key: String { [kind, title, subtitle, chapter ?? "", detail ?? ""].joined(separator: "|") }
}
private struct Plan: Decodable {
    let output: String, source: String, audio: String, music_credit: String
    let audio_start: Double
    let audio_volume: Float
    let model_hero: String
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
private func overlayImage(_ shot: Shot, credit: String, hero: String) -> CGImage {
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
            text("실제 APK 실행 화면 · MOCK 데이터 · 개발 중", NSRect(x: 64, y: 24, width: 1600, height: 30), 18, muted)
            text(credit, NSRect(x: 832, y: 28, width: 1030, height: 24), 15, muted)
        } else if shot.kind == "intro" {
            NSColor.white.setFill(); NSRect(x: 0, y: 0, width: W, height: H).fill()
            rounded(NSRect(x: 1140, y: 166, width: 620, height: 740), pale, radius: 52)
            let carPhoto = NSImage(contentsOfFile: hero)!
            let photoHeight = 552 * carPhoto.size.height / carPhoto.size.width
            let photoRect = NSRect(x: 1174, y: 342 + (430 - photoHeight) / 2, width: 552, height: photoHeight)
            NSGraphicsContext.saveGraphicsState()
            NSBezierPath(roundedRect: photoRect, xRadius: 24, yRadius: 24).addClip()
            carPhoto.draw(in: photoRect)
            NSGraphicsContext.restoreGraphicsState()
            text("IONIQ 5 STYLE · 3D", NSRect(x: 1180, y: 278, width: 540, height: 44), 26, blue, .semibold, center: true)
            text("실제 앱의 3D 렌더링 화면", NSRect(x: 1180, y: 240, width: 540, height: 30), 17, muted, center: true)
            text("CarCue", NSRect(x: 112, y: 884, width: 800, height: 100), 70, blue, .bold)
            text(shot.title, NSRect(x: 112, y: 477, width: 960, height: 260), 83, ink, .bold, line: 112)
            text(shot.subtitle, NSRect(x: 118, y: 343, width: 920, height: 70), 34, muted)
            rounded(NSRect(x: 116, y: 211, width: 420, height: 56), pale, radius: 14)
            text("한국어  ·  English  ·  日本語", NSRect(x: 134, y: 223, width: 396, height: 34), 24, blue, .medium)
            text("개발 중인 Mock 앱 소개", NSRect(x: 116, y: 80, width: 800, height: 40), 22, muted)
            text(credit, NSRect(x: 116, y: 28, width: 1680, height: 30), 18, muted)
        } else {
            NSGradient(starting: blue, ending: NSColor(srgbRed: 0.06, green: 0.22, blue: 0.69, alpha: 1))!.draw(in: NSRect(x: 0, y: 0, width: W, height: H), angle: -25)
            text("CarCue", NSRect(x: 180, y: 802, width: 1560, height: 120), 78, .white, .bold, center: true)
            text(shot.title, NSRect(x: 220, y: 428, width: 1480, height: 270), 83, .white, .bold, center: true, line: 114)
            text(shot.subtitle, NSRect(x: 220, y: 284, width: 1480, height: 60), 32, .white, .medium, center: true)
            text("실제 APK 기반 Mock 시연", NSRect(x: 220, y: 103, width: 1480, height: 50), 22, NSColor.white.withAlphaComponent(0.8), center: true)
            text(credit, NSRect(x: 150, y: 42, width: 1620, height: 35), 18, NSColor.white.withAlphaComponent(0.85), center: true)
        }
    }
}

private func blankMovie(_ url: URL, duration: Double) async throws {
    try? FileManager.default.removeItem(at: url)
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

@main struct AppIntro {
    static func main() async throws {
        let root = URL(fileURLWithPath: FileManager.default.currentDirectoryPath, isDirectory: true)
        let plan = try JSONDecoder().decode(Plan.self, from: Data(contentsOf: URL(fileURLWithPath: CommandLine.arguments[1])))
        let work = root.appendingPathComponent("output/qa/app-intro-work", isDirectory: true)
        let source = AVURLAsset(url: root.appendingPathComponent(plan.source))
        let sourceTrack = try await source.loadTracks(withMediaType: .video).first!
        let sourceDuration = CMTimeGetSeconds(try await source.load(.duration))
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
            if native { precondition((shot.start ?? 0) + shot.duration <= sourceDuration) }
            try videoTrack.insertTimeRange(CMTimeRange(start: CMTime(seconds: native ? shot.start! : 0, preferredTimescale: 600), duration: duration), of: native ? sourceTrack : blankTrack, at: at)
            let layer = AVMutableVideoCompositionLayerInstruction(assetTrack: videoTrack)
            if native {
                layer.setTransform(CGAffineTransform(scaleX: 1.125, y: 1.125).concatenating(CGAffineTransform(translationX: appRect.minX, y: H - appRect.maxY)), at: at)
                layer.setOpacityRamp(fromStartOpacity: 0, toEndOpacity: 1, timeRange: CMTimeRange(start: at, duration: CMTime(seconds: 0.13, preferredTimescale: 600)))
                layer.setOpacityRamp(fromStartOpacity: 1, toEndOpacity: 0, timeRange: CMTimeRange(start: at + duration - CMTime(seconds: 0.10, preferredTimescale: 600), duration: CMTime(seconds: 0.10, preferredTimescale: 600)))
            } else { layer.setTransform(.identity, at: at) }
            let instruction = AVMutableVideoCompositionInstruction()
            instruction.timeRange = CMTimeRange(start: at, duration: duration); instruction.layerInstructions = [layer]
            instruction.backgroundColor = pale.cgColor; instructions.append(instruction)
            if let last = overlays.last, last.shot.key == shot.key {
                overlays[overlays.count - 1].duration += shot.duration
            } else { overlays.append(Overlay(shot: shot, start: cursor, duration: shot.duration)) }
            print("\(cursor)–\(cursor + shot.duration) \(shot.kind): \(shot.chapter ?? "CarCue")")
            cursor += shot.duration
        }
        let soundAsset = AVURLAsset(url: root.appendingPathComponent(plan.audio))
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
            let layer = CALayer(); layer.frame = parent.bounds; layer.contents = overlayImage(overlay.shot, credit: plan.music_credit, hero: plan.model_hero); layer.opacity = 0
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
        let output = root.appendingPathComponent(plan.output); try? FileManager.default.removeItem(at: output)
        let export = AVAssetExportSession(asset: composition, presetName: AVAssetExportPresetHighestQuality)!
        export.videoComposition = video; export.audioMix = audioMix; export.shouldOptimizeForNetworkUse = true
        try await export.export(to: output, as: .mp4)
        print("EXPORTED \(cursor)s, 1920×1080, 30fps, licensed external music")
    }
}
