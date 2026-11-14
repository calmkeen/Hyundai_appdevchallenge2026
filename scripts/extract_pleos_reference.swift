// Extract only the user's supplied recording, not emulator APKs or SDK assets.
import Foundation
import AVFoundation
import AppKit

let source = URL(fileURLWithPath: CommandLine.arguments[1])
let output = URL(fileURLWithPath: CommandLine.arguments[2], isDirectory: true)
let asset = AVURLAsset(url: source)
let track = asset.tracks(withMediaType: .video).first!
precondition(track.naturalSize == CGSize(width: 2560, height: 1440))
let generator = AVAssetImageGenerator(asset: asset)
generator.appliesPreferredTrackTransform = true
generator.requestedTimeToleranceBefore = .zero
generator.requestedTimeToleranceAfter = .zero
try FileManager.default.createDirectory(at: output.appendingPathComponent("car"), withIntermediateDirectories: true)
func extract(_ seconds: Double, _ crop: CGRect, _ path: String) throws {
    let image = try generator.copyCGImage(at: CMTime(seconds: seconds, preferredTimescale: 6000), actualTime: nil)
    let part = image.cropping(to: crop)!
    let bitmap = NSBitmapImageRep(cgImage: part)
    try bitmap.representation(using: .png, properties: [:])!.write(to: output.appendingPathComponent(path))
}
try extract(4, CGRect(x: 250, y: 70, width: 370, height: 185), "seatbelt.png")
for i in 0...20 {
    try extract(19 + Double(i)/20, CGRect(x: 130, y: 520, width: 635, height: 405), String(format: "car/frame-%03d.png", i))
}
print("EXTRACTED original seatbelt + 21 car frames (19–20s), no SDK binary extraction or alternate model")
