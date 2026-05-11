from pathlib import Path
import re

path = Path(r"flutter/android/app/src/main/kotlin/com/carriez/flutter_hbb/MainService.kt")
content = path.read_text(encoding="utf-8")

# 1) Add rotation fields
if "bbRotationMode" not in content:
    anchor = """    private var imageReader: ImageReader? = null
    private var virtualDisplay: VirtualDisplay? = null"""
    replacement = """    private var imageReader: ImageReader? = null
    private var virtualDisplay: VirtualDisplay? = null

    // BB CUSTOM ROTATION FIX
    // 90 clockwise, 270 counter-clockwise
    private val bbRotationMode = 270

    // Capture size and reported output size are kept separately.
    private var captureWidth = 0
    private var captureHeight = 0
    private var captureDpi = 0

    // Direct buffer pool for rotated frames.
    private val rotateBufferPool = arrayOfNulls<ByteBuffer>(4)
    private var rotateBufferSize = 0
    private var rotateBufferIndex = 0"""
    if anchor not in content:
        raise SystemExit("video field anchor not found")
    content = content.replace(anchor, replacement, 1)

# 2) Replace updateScreenInfo block
update_replacement = r'''    private fun isRotating90or270(): Boolean {
        return bbRotationMode == 90 || bbRotationMode == 270
    }

    private fun getCaptureWidth(): Int {
        return if (captureWidth > 0) captureWidth else SCREEN_INFO.width
    }

    private fun getCaptureHeight(): Int {
        return if (captureHeight > 0) captureHeight else SCREEN_INFO.height
    }

    private fun getCaptureDpi(): Int {
        return if (captureDpi > 0) captureDpi else SCREEN_INFO.dpi
    }

    private fun updateScreenInfo(orientation: Int) {
        var rawW: Int
        var rawH: Int
        var dpi: Int
        val windowManager = getSystemService(Context.WINDOW_SERVICE) as WindowManager

        @Suppress("DEPRECATION")
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
            val m = windowManager.maximumWindowMetrics
            rawW = m.bounds.width()
            rawH = m.bounds.height()
            dpi = resources.configuration.densityDpi
        } else {
            val dm = DisplayMetrics()
            windowManager.defaultDisplay.getRealMetrics(dm)
            rawW = dm.widthPixels
            rawH = dm.heightPixels
            dpi = dm.densityDpi
        }

        val maxSide = max(rawW, rawH)
        val minSide = min(rawW, rawH)

        var outW: Int
        var outH: Int

        if (orientation == ORIENTATION_LANDSCAPE) {
            outW = maxSide
            outH = minSide
        } else {
            outW = minSide
            outH = maxSide
        }

        var capW = outW
        var capH = outH

        if (isRotating90or270()) {
            capW = outH
            capH = outW
        }

        var scale = 1

        if (outW != 0 && outH != 0) {
            if (isHalfScale == true && (outW > MAX_SCREEN_SIZE || outH > MAX_SCREEN_SIZE)) {
                scale = 2
                outW /= scale
                outH /= scale
                capW /= scale
                capH /= scale
                dpi /= scale
            }

            val changed =
                SCREEN_INFO.width != outW ||
                    SCREEN_INFO.height != outH ||
                    SCREEN_INFO.scale != scale ||
                    SCREEN_INFO.dpi != dpi ||
                    captureWidth != capW ||
                    captureHeight != capH ||
                    captureDpi != dpi

            if (changed) {
                SCREEN_INFO.width = outW
                SCREEN_INFO.height = outH
                SCREEN_INFO.scale = scale
                SCREEN_INFO.dpi = dpi

                captureWidth = capW
                captureHeight = capH
                captureDpi = dpi

                Log.d(
                    logTag,
                    "updateScreenInfo output:${SCREEN_INFO.width}x${SCREEN_INFO.height}, capture:${captureWidth}x${captureHeight}, dpi:$dpi, rotation:$bbRotationMode"
                )

                if (isStart) {
                    stopCapture()
                    FFI.refreshScreen()
                    startCapture()
                } else {
                    FFI.refreshScreen()
                }
            }
        }
    }

    override fun onBind'''

content, n = re.subn(
    r'(?s)    private fun updateScreenInfo\(orientation: Int\) \{.*?\n    override fun onBind',
    update_replacement,
    content,
    count=1,
)
if n != 1:
    raise SystemExit("updateScreenInfo block not found")

# 3) Replace createSurface block
surface_replacement = r'''    @SuppressLint("WrongConstant")
    private fun createSurface(): Surface? {
        return if (useVP9) {
            null
        } else {
            val cw = getCaptureWidth()
            val ch = getCaptureHeight()

            Log.d(
                logTag,
                "ImageReader.newInstance capture:${cw}x${ch}, output:${SCREEN_INFO.width}x${SCREEN_INFO.height}, rotation:$bbRotationMode"
            )

            imageReader =
                ImageReader.newInstance(
                    cw,
                    ch,
                    PixelFormat.RGBA_8888,
                    2
                ).apply {
                    setOnImageAvailableListener({ imageReader: ImageReader ->
                        try {
                            imageReader.acquireLatestImage().use { image ->
                                if (image == null || !isStart) return@setOnImageAvailableListener

                                val plane = image.planes[0]
                                val buffer = plane.buffer
                                buffer.rewind()

                                val fixedBuffer = rotateFrameIfNeeded(
                                    buffer,
                                    image.width,
                                    image.height,
                                    plane.rowStride,
                                    plane.pixelStride
                                )

                                FFI.onVideoFrameUpdate(fixedBuffer)
                            }
                        } catch (e: java.lang.Exception) {
                            Log.e(logTag, "onImageAvailable frame rotate error:$e")
                        }
                    }, serviceHandler)
                }

            Log.d(logTag, "ImageReader.setOnImageAvailableListener done")
            imageReader?.surface
        }
    }

    fun onVoiceCallStarted'''

content, n = re.subn(
    r'(?s)    @SuppressLint\("WrongConstant"\)\s+private fun createSurface\(\): Surface\? \{.*?\n    fun onVoiceCallStarted',
    surface_replacement,
    content,
    count=1,
)
if n != 1:
    raise SystemExit("createSurface block not found")

# 4) Insert rotation helper functions
if "private fun rotateFrameIfNeeded(" not in content:
    helpers = r'''    private fun getRotateBuffer(size: Int): ByteBuffer {
        if (size <= 0) {
            throw IllegalArgumentException("Invalid rotate buffer size:$size")
        }

        if (rotateBufferSize != size) {
            for (i in rotateBufferPool.indices) {
                rotateBufferPool[i] = null
            }
            rotateBufferSize = size
            rotateBufferIndex = 0
            Log.d(logTag, "Reset rotate buffer pool size:$size")
        }

        val idx = rotateBufferIndex % rotateBufferPool.size
        var out = rotateBufferPool[idx]

        if (out == null || out.capacity() < size) {
            out = ByteBuffer.allocateDirect(size)
            rotateBufferPool[idx] = out
            Log.d(logTag, "Allocated rotate buffer index:$idx size:$size")
        }

        rotateBufferIndex = (idx + 1) % rotateBufferPool.size

        out.clear()
        out.limit(size)
        return out
    }

    private fun clearRotateBuffers() {
        for (i in rotateBufferPool.indices) {
            rotateBufferPool[i] = null
        }
        rotateBufferSize = 0
        rotateBufferIndex = 0
        Log.d(logTag, "Cleared rotate buffer pool")
    }

    private fun rotateRgba90Cw(
        src: ByteBuffer,
        width: Int,
        height: Int,
        rowStride: Int,
        pixelStride: Int
    ): ByteBuffer {
        val size = width * height * 4
        val out = getRotateBuffer(size)

        for (y in 0 until height) {
            for (x in 0 until width) {
                val srcPos = y * rowStride + x * pixelStride

                val dstX = height - 1 - y
                val dstY = x
                val dstPos = (dstY * height + dstX) * 4

                out.put(dstPos, src.get(srcPos))
                out.put(dstPos + 1, src.get(srcPos + 1))
                out.put(dstPos + 2, src.get(srcPos + 2))
                out.put(dstPos + 3, src.get(srcPos + 3))
            }
        }

        out.position(0)
        out.limit(size)
        return out
    }

    private fun rotateRgba270Cw(
        src: ByteBuffer,
        width: Int,
        height: Int,
        rowStride: Int,
        pixelStride: Int
    ): ByteBuffer {
        val size = width * height * 4
        val out = getRotateBuffer(size)

        for (y in 0 until height) {
            for (x in 0 until width) {
                val srcPos = y * rowStride + x * pixelStride

                val dstX = y
                val dstY = width - 1 - x
                val dstPos = (dstY * height + dstX) * 4

                out.put(dstPos, src.get(srcPos))
                out.put(dstPos + 1, src.get(srcPos + 1))
                out.put(dstPos + 2, src.get(srcPos + 2))
                out.put(dstPos + 3, src.get(srcPos + 3))
            }
        }

        out.position(0)
        out.limit(size)
        return out
    }

    private fun rotateFrameIfNeeded(
        src: ByteBuffer,
        width: Int,
        height: Int,
        rowStride: Int,
        pixelStride: Int
    ): ByteBuffer {
        return when (bbRotationMode) {
            90 -> rotateRgba90Cw(src, width, height, rowStride, pixelStride)
            270 -> rotateRgba270Cw(src, width, height, rowStride, pixelStride)
            else -> {
                src.rewind()
                src
            }
        }
    }

'''
    marker = '    @SuppressLint("WrongConstant")\n    private fun createSurface(): Surface? {'
    if marker not in content:
        raise SystemExit("createSurface marker not found for helpers")
    content = content.replace(marker, helpers + marker, 1)

# 5) Clear rotate buffers in stopCapture
if "imageReader = null\n\n        clearRotateBuffers()" not in content:
    content = content.replace(
        "        imageReader?.close()\n        imageReader = null",
        "        imageReader?.close()\n        imageReader = null\n\n        clearRotateBuffers()",
        1,
    )

# 6) Use capture size for VirtualDisplay and VP9 codec
content = content.replace(
    "it.resize(SCREEN_INFO.width, SCREEN_INFO.height, SCREEN_INFO.dpi)",
    "it.resize(getCaptureWidth(), getCaptureHeight(), getCaptureDpi())",
)

content = content.replace(
    "SCREEN_INFO.width, SCREEN_INFO.height, SCREEN_INFO.dpi, VIRTUAL_DISPLAY_FLAG_AUTO_MIRROR",
    "getCaptureWidth(), getCaptureHeight(), getCaptureDpi(), VIRTUAL_DISPLAY_FLAG_AUTO_MIRROR",
)

content = content.replace(
    "MediaFormat.createVideoFormat(MIME_TYPE, SCREEN_INFO.width, SCREEN_INFO.height)",
    "MediaFormat.createVideoFormat(MIME_TYPE, getCaptureWidth(), getCaptureHeight())",
)

path.write_text(content, encoding="utf-8")
print("BB rotation patch OK")

