// Makes the Mac app icon from the square one, on Apple's macOS icon grid (an 824 px rounded square, corner
// radius about 185, centred on 1024), so macOS shows it like the iPhone's instead of shrinking it onto a grey tile:
//   swift godot/tools/mac_icon.swift godot/icon_placeholder.png godot/icon_mac_placeholder.png
import AppKit
let args = CommandLine.arguments
let src = NSImage(contentsOfFile: args[1])!
let size = 1024, inset: CGFloat = 100, radius: CGFloat = 185.4
let rep = NSBitmapImageRep(bitmapDataPlanes: nil, pixelsWide: size, pixelsHigh: size, bitsPerSample: 8,
	samplesPerPixel: 4, hasAlpha: true, isPlanar: false, colorSpaceName: .deviceRGB, bytesPerRow: 0, bitsPerPixel: 0)!
NSGraphicsContext.saveGraphicsState()
NSGraphicsContext.current = NSGraphicsContext(bitmapImageRep: rep)
let box = NSRect(x: inset, y: inset, width: CGFloat(size) - 2 * inset, height: CGFloat(size) - 2 * inset)
NSBezierPath(roundedRect: box, xRadius: radius, yRadius: radius).addClip()
src.draw(in: box)
NSGraphicsContext.restoreGraphicsState()
try! rep.representation(using: .png, properties: [:])!.write(to: URL(fileURLWithPath: args[2]))
