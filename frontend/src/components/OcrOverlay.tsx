import { useEffect, useRef, useState } from 'react'
import type { OcrNumber } from '../api/types'

export interface OcrOverlayProps {
  imageUrl: string
  ocrNumbers: OcrNumber[]
  /** Map ocr_id → color string; OCR not in map renders default (slate). */
  colorByOcrId?: Record<number, string>
  onOcrClick?: (ocrId: number) => void
  /** Highlighted OCR id (e.g. currently being edited) */
  highlightedOcrId?: number | null
}

interface ImageDims {
  natural: { w: number; h: number }
  rendered: { w: number; h: number }
}

const DEFAULT_COLOR = 'rgba(148, 163, 184, 0.85)' // slate-400
const HIGHLIGHT_COLOR = 'rgba(250, 204, 21, 1)' // yellow-400

export default function OcrOverlay(props: OcrOverlayProps) {
  const { imageUrl, ocrNumbers, colorByOcrId, onOcrClick, highlightedOcrId } = props
  const imgRef = useRef<HTMLImageElement>(null)
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const [dims, setDims] = useState<ImageDims | null>(null)

  // Recompute dims on image load + window resize
  useEffect(() => {
    const updateDims = () => {
      const img = imgRef.current
      if (!img || !img.naturalWidth) return
      setDims({
        natural: { w: img.naturalWidth, h: img.naturalHeight },
        rendered: { w: img.clientWidth, h: img.clientHeight },
      })
    }
    updateDims()
    window.addEventListener('resize', updateDims)
    return () => window.removeEventListener('resize', updateDims)
  }, [imageUrl])

  // Draw bboxes
  useEffect(() => {
    if (!dims) return
    const canvas = canvasRef.current
    if (!canvas) return
    canvas.width = dims.rendered.w
    canvas.height = dims.rendered.h
    const ctx = canvas.getContext('2d')
    if (!ctx) return
    ctx.clearRect(0, 0, canvas.width, canvas.height)

    const sx = dims.rendered.w / dims.natural.w
    const sy = dims.rendered.h / dims.natural.h

    for (const n of ocrNumbers) {
      const x = n.bbox.x * sx
      const y = n.bbox.y * sy
      const w = n.bbox.w * sx
      const h = n.bbox.h * sy
      const isHighlighted = highlightedOcrId === n.id
      ctx.strokeStyle = isHighlighted ? HIGHLIGHT_COLOR : (colorByOcrId?.[n.id] ?? DEFAULT_COLOR)
      ctx.lineWidth = isHighlighted ? 3 : 2
      ctx.strokeRect(x, y, w, h)

      // Label with current value
      const value = n.corrected_value ?? n.raw_value
      const label = value === null ? '?' : String(value)
      ctx.fillStyle = isHighlighted ? HIGHLIGHT_COLOR : (colorByOcrId?.[n.id] ?? DEFAULT_COLOR)
      ctx.font = '14px system-ui, sans-serif'
      const textW = ctx.measureText(label).width
      ctx.fillRect(x, y - 18, textW + 8, 18)
      ctx.fillStyle = '#0f172a'
      ctx.fillText(label, x + 4, y - 4)
    }
  }, [dims, ocrNumbers, colorByOcrId, highlightedOcrId])

  const handleClick = (e: React.MouseEvent<HTMLCanvasElement>) => {
    if (!onOcrClick || !dims) return
    const rect = canvasRef.current!.getBoundingClientRect()
    const cx = e.clientX - rect.left
    const cy = e.clientY - rect.top
    const sx = dims.rendered.w / dims.natural.w
    const sy = dims.rendered.h / dims.natural.h

    // Find topmost bbox containing the click
    for (let i = ocrNumbers.length - 1; i >= 0; i--) {
      const n = ocrNumbers[i]
      const x = n.bbox.x * sx
      const y = n.bbox.y * sy
      const w = n.bbox.w * sx
      const h = n.bbox.h * sy
      if (cx >= x && cx <= x + w && cy >= y && cy <= y + h) {
        onOcrClick(n.id)
        return
      }
    }
  }

  return (
    <div className="relative inline-block">
      <img
        ref={imgRef}
        src={imageUrl}
        alt="capture"
        className="max-w-full rounded"
        onLoad={() => {
          // Trigger a re-measure after natural dimensions are available
          const img = imgRef.current
          if (img) {
            setDims({
              natural: { w: img.naturalWidth, h: img.naturalHeight },
              rendered: { w: img.clientWidth, h: img.clientHeight },
            })
          }
        }}
      />
      <canvas
        ref={canvasRef}
        onClick={handleClick}
        className="absolute top-0 left-0 cursor-crosshair"
      />
    </div>
  )
}
