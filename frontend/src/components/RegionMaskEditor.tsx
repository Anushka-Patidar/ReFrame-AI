import { useEffect, useMemo, useRef, useState } from 'react'
import type { PointerEvent as ReactPointerEvent } from 'react'
import { RotateCcw, Save, Trash2, Undo2, Redo2 } from 'lucide-react'
import type { RegionAction, RegionConstraint } from '../types/api'
import { api } from '../lib/api'

type RegionDraft = {
  id: string
  action: RegionAction
  label: string
  maskCanvas: HTMLCanvasElement // display-sized (not original)
}

const ACTION_META: Record<
  RegionAction,
  { label: string; color: string; overlayAlpha: number; swatch: string }
> = {
  KEEP: { label: 'KEEP', color: '#22c55e', overlayAlpha: 0.33, swatch: 'bg-emerald-500/20' },
  CHANGE: {
    label: 'CHANGE',
    color: '#f59e0b',
    overlayAlpha: 0.33,
    swatch: 'bg-amber-500/20',
  },
  REMOVE: { label: 'REMOVE', color: '#ef4444', overlayAlpha: 0.33, swatch: 'bg-red-500/20' },
}

function makeBlankCanvas(width: number, height: number) {
  const c = document.createElement('canvas')
  c.width = Math.max(1, Math.floor(width))
  c.height = Math.max(1, Math.floor(height))
  return c
}

async function canvasToBlob(canvas: HTMLCanvasElement, type: string) {
  return await new Promise<Blob>((resolve, reject) => {
    canvas.toBlob((b) => {
      if (!b) reject(new Error('Failed to export mask PNG.'))
      else resolve(b)
    }, type)
  })
}

function canvasHasAnyAlphaPixels(canvas: HTMLCanvasElement) {
  const ctx = canvas.getContext('2d')
  if (!ctx) return false
  const img = ctx.getImageData(0, 0, canvas.width, canvas.height)
  const data = img.data
  for (let i = 3; i < data.length; i += 4) {
    if (data[i] !== 0) return true
  }
  return false
}

export function RegionMaskEditor({
  token,
  roomId,
  imageUrl,
  initialConstraints,
  onRefresh,
}: {
  token: string
  roomId: string
  imageUrl: string
  initialConstraints: RegionConstraint[]
  onRefresh: () => Promise<void>
}) {
  const [error, setError] = useState('')
  const [isSaving, setIsSaving] = useState(false)

  const [activeAction, setActiveAction] = useState<RegionAction>('KEEP')
  const [activeLabel, setActiveLabel] = useState('')
  const [brushRadius, setBrushRadius] = useState(18)
  const [eraseMode, setEraseMode] = useState(false)

  const [originalSize, setOriginalSize] = useState<{ w: number; h: number } | null>(null)
  const [displaySize, setDisplaySize] = useState<{ w: number; h: number } | null>(null)

  const overlayCanvasRef = useRef<HTMLCanvasElement | null>(null)
  const activeMaskCanvasRef = useRef<HTMLCanvasElement | null>(null)
  const pointerDownRef = useRef(false)
  const lastPointRef = useRef<{ x: number; y: number } | null>(null)

  const undoStackRef = useRef<ImageData[]>([])
  const redoStackRef = useRef<ImageData[]>([])

  const [persistedRegions, setPersistedRegions] = useState(initialConstraints)
  const [pendingRegions, setPendingRegions] = useState<RegionDraft[]>([])

  const maskCanvasByRegionIdRef = useRef<Record<string, HTMLCanvasElement>>({})

  const canSave = useMemo(() => {
    if (!originalSize || !displaySize) return false
    if (!pendingRegions.length) return false
    return true
  }, [pendingRegions.length, displaySize, originalSize])

  // Load original dimensions (for correct mask export coordinate space).
  useEffect(() => {
    setOriginalSize(null)
    setDisplaySize(null)
    if (!imageUrl) return

    const img = new Image()
    img.onload = () => {
      const w = img.naturalWidth
      const h = img.naturalHeight
      if (!w || !h) return
      const maxSide = 900
      const scale = Math.min(1, maxSide / Math.max(w, h))
      const dw = Math.max(1, Math.round(w * scale))
      const dh = Math.max(1, Math.round(h * scale))
      setOriginalSize({ w, h })
      setDisplaySize({ w: dw, h: dh })
    }
    img.src = imageUrl
  }, [imageUrl])

  // Initialize mask canvases when display size is ready.
  useEffect(() => {
    if (!displaySize) return
    activeMaskCanvasRef.current = makeBlankCanvas(displaySize.w, displaySize.h)

    undoStackRef.current = []
    redoStackRef.current = []

    const canvas = overlayCanvasRef.current
    if (canvas) {
      canvas.width = displaySize.w
      canvas.height = displaySize.h
    }

    // Load persisted mask images into display-sized canvases.
    const regionMasks: Record<string, HTMLCanvasElement> = {}
    const entries = persistedRegions.map((r) => r.id)
    if (!entries.length) {
      maskCanvasByRegionIdRef.current = regionMasks
      renderOverlay()
      return
    }

    let cancelled = false
    ;(async () => {
      await Promise.all(
        persistedRegions.map(async (region) => {
          if (!displaySize) return
          const maskImg = new Image()
          maskImg.crossOrigin = 'anonymous'
          await new Promise<void>((resolve, reject) => {
            maskImg.onload = () => resolve()
            maskImg.onerror = () => reject(new Error('Failed to load mask PNG.'))
            maskImg.src = region.mask_url
          })

          if (cancelled) return

          const c = makeBlankCanvas(displaySize.w, displaySize.h)
          const ctx = c.getContext('2d')
          if (!ctx) return
          ctx.imageSmoothingEnabled = false
          ctx.drawImage(maskImg, 0, 0, displaySize.w, displaySize.h)
          regionMasks[region.id] = c
        }),
      )

      if (cancelled) return
      maskCanvasByRegionIdRef.current = regionMasks
      renderOverlay()
    })().catch((e) => {
      if (!cancelled) setError(e instanceof Error ? e.message : 'Failed loading masks.')
    })

    return () => {
      cancelled = true
    }
  }, [displaySize, persistedRegions])

  useEffect(() => {
    setPersistedRegions(initialConstraints)
  }, [initialConstraints])

  function renderOverlay() {
    const canvas = overlayCanvasRef.current
    const maskCanvas = activeMaskCanvasRef.current
    if (!canvas || !maskCanvas || !displaySize) return

    const ctx = canvas.getContext('2d')
    if (!ctx) return

    ctx.clearRect(0, 0, canvas.width, canvas.height)

    const drawMask = (mask: HTMLCanvasElement | null | undefined, action: RegionAction, alpha: number) => {
      if (!mask) return
      const meta = ACTION_META[action]
      // 1) Draw mask alpha into the overlay canvas.
      ctx.globalAlpha = 1
      ctx.globalCompositeOperation = 'source-over'
      ctx.drawImage(mask, 0, 0, canvas.width, canvas.height)
      // 2) Colorize using source-atop.
      ctx.globalCompositeOperation = 'source-atop'
      ctx.fillStyle = meta.color
      ctx.globalAlpha = alpha
      ctx.fillRect(0, 0, canvas.width, canvas.height)
      ctx.globalCompositeOperation = 'source-over'
      ctx.globalAlpha = 1
    }

    for (const region of persistedRegions) {
      const mask = maskCanvasByRegionIdRef.current[region.id]
      drawMask(mask, region.action, ACTION_META[region.action].overlayAlpha)
    }
    for (const draft of pendingRegions) {
      drawMask(draft.maskCanvas, draft.action, ACTION_META[draft.action].overlayAlpha)
    }
    drawMask(maskCanvas, activeAction, ACTION_META[activeAction].overlayAlpha)
  }

  // Throttle overlay renders while painting.
  const renderQueuedRef = useRef(false)
  const requestRender = () => {
    if (renderQueuedRef.current) return
    renderQueuedRef.current = true
    requestAnimationFrame(() => {
      renderQueuedRef.current = false
      renderOverlay()
    })
  }

  function getRelativePoint(e: ReactPointerEvent<HTMLCanvasElement>) {
    const canvas = overlayCanvasRef.current
    if (!canvas) return { x: 0, y: 0 }
    const rect = canvas.getBoundingClientRect()
    return {
      x: Math.max(0, Math.min(canvas.width, e.clientX - rect.left)),
      y: Math.max(0, Math.min(canvas.height, e.clientY - rect.top)),
    }
  }

  function beginStroke(p: { x: number; y: number }) {
    const maskCanvas = activeMaskCanvasRef.current
    const canvas = overlayCanvasRef.current
    if (!maskCanvas || !canvas || !displaySize) return

    const ctx = maskCanvas.getContext('2d')
    if (!ctx) return

    // Undo: snapshot before mutating.
    const snapshot = ctx.getImageData(0, 0, maskCanvas.width, maskCanvas.height)
    undoStackRef.current.push(snapshot)
    if (undoStackRef.current.length > 25) undoStackRef.current.shift()
    redoStackRef.current = []

    pointerDownRef.current = true
    lastPointRef.current = p

    ctx.imageSmoothingEnabled = true
    ctx.lineCap = 'round'
    ctx.lineJoin = 'round'
    ctx.lineWidth = Math.max(1, brushRadius * 2)
    ctx.globalCompositeOperation = eraseMode ? 'destination-out' : 'source-over'
    ctx.strokeStyle = eraseMode ? 'rgba(0,0,0,1)' : 'rgba(255,255,255,1)'

    ctx.beginPath()
    ctx.moveTo(p.x, p.y)
    ctx.lineTo(p.x + 0.01, p.y + 0.01)
    ctx.stroke()
    requestRender()
  }

  function continueStroke(p: { x: number; y: number }) {
    if (!pointerDownRef.current) return
    const last = lastPointRef.current
    if (!last) return

    const maskCanvas = activeMaskCanvasRef.current
    if (!maskCanvas) return
    const ctx = maskCanvas.getContext('2d')
    if (!ctx) return

    ctx.imageSmoothingEnabled = true
    ctx.lineCap = 'round'
    ctx.lineJoin = 'round'
    ctx.lineWidth = Math.max(1, brushRadius * 2)
    ctx.globalCompositeOperation = eraseMode ? 'destination-out' : 'source-over'
    ctx.strokeStyle = eraseMode ? 'rgba(0,0,0,1)' : 'rgba(255,255,255,1)'

    ctx.beginPath()
    ctx.moveTo(last.x, last.y)
    ctx.lineTo(p.x, p.y)
    ctx.stroke()

    lastPointRef.current = p
    requestRender()
  }

  function endStroke() {
    pointerDownRef.current = false
    lastPointRef.current = null
    requestRender()
  }

  function undo() {
    const maskCanvas = activeMaskCanvasRef.current
    if (!maskCanvas) return
    const ctx = maskCanvas.getContext('2d')
    if (!ctx) return
    const prev = undoStackRef.current.pop()
    if (!prev) return

    const current = ctx.getImageData(0, 0, maskCanvas.width, maskCanvas.height)
    redoStackRef.current.push(current)
    ctx.putImageData(prev, 0, 0)
    requestRender()
  }

  function redo() {
    const maskCanvas = activeMaskCanvasRef.current
    if (!maskCanvas) return
    const ctx = maskCanvas.getContext('2d')
    if (!ctx) return
    const next = redoStackRef.current.pop()
    if (!next) return

    const current = ctx.getImageData(0, 0, maskCanvas.width, maskCanvas.height)
    undoStackRef.current.push(current)
    ctx.putImageData(next, 0, 0)
    requestRender()
  }

  function clearActiveMask() {
    const maskCanvas = activeMaskCanvasRef.current
    if (!maskCanvas) return
    const ctx = maskCanvas.getContext('2d')
    if (!ctx) return
    const snapshot = ctx.getImageData(0, 0, maskCanvas.width, maskCanvas.height)
    undoStackRef.current.push(snapshot)
    redoStackRef.current = []
    ctx.clearRect(0, 0, maskCanvas.width, maskCanvas.height)
    requestRender()
  }

  function addActiveRegionToDrafts() {
    const maskCanvas = activeMaskCanvasRef.current
    if (!maskCanvas) return
    if (!activeLabel.trim()) {
      setError('Add a label for this region (e.g. sofa, curtains, TV unit).')
      return
    }
    if (!canvasHasAnyAlphaPixels(maskCanvas)) {
      setError('Paint at least one pixel region before adding it.')
      return
    }
    setError('')

    const clone = makeBlankCanvas(maskCanvas.width, maskCanvas.height)
    const cloneCtx = clone.getContext('2d')
    const srcCtx = maskCanvas.getContext('2d')
    if (!cloneCtx || !srcCtx) return
    cloneCtx.drawImage(maskCanvas, 0, 0)

    const id = crypto.randomUUID()
    setPendingRegions((current) => [
      ...current,
      {
        id,
        action: activeAction,
        label: activeLabel.trim()[:80],
        maskCanvas: clone,
      },
    ])

    // Reset active mask.
    undoStackRef.current = []
    redoStackRef.current = []
    const ctx = maskCanvas.getContext('2d')
    ctx?.clearRect(0, 0, maskCanvas.width, maskCanvas.height)
    requestRender()
  }

  async function exportDraftMaskToBlob(draft: RegionDraft) {
    if (!originalSize) throw new Error('Original image size not loaded.')
    const origCanvas = makeBlankCanvas(originalSize.w, originalSize.h)
    const ctx = origCanvas.getContext('2d')
    if (!ctx) throw new Error('Failed creating export canvas.')
    ctx.imageSmoothingEnabled = false
    ctx.drawImage(draft.maskCanvas, 0, 0, origCanvas.width, origCanvas.height)
    return canvasToBlob(origCanvas, 'image/png')
  }

  async function savePendingRegions() {
    setError('')
    if (!token) return
    if (!originalSize) return
    if (!pendingRegions.length) return

    setIsSaving(true)
    try {
      for (const draft of pendingRegions) {
        const blob = await exportDraftMaskToBlob(draft)
        const file = new File([blob], `${draft.id}.png`, { type: 'image/png' })
        await api.createRegionConstraint(token, roomId, {
          action: draft.action,
          label: draft.label,
          image_width: originalSize.w,
          image_height: originalSize.h,
          mask: file,
        })
      }
      setPendingRegions([])
      await onRefresh()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Unable to save region constraints.')
    } finally {
      setIsSaving(false)
    }
  }

  async function deletePersistedConstraint(constraintId: string) {
    setError('')
    try {
      await api.deleteRegionConstraint(token, roomId, constraintId)
      await onRefresh()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Unable to delete region constraint.')
    }
  }

  return (
    <div className="space-y-6">
      {error ? <p className="text-sm text-red-600">{error}</p> : null}

      <div className="grid gap-6 lg:grid-cols-[1fr_420px]">
        <div className="rounded-[1.6rem] border border-sand-200 bg-white p-4">
          {displaySize ? (
            <div className="relative">
              {/* Background room photo (never modified) */}
              <img
                src={imageUrl}
                alt="Room to mask"
                width={displaySize.w}
                height={displaySize.h}
                style={{ display: 'block', width: displaySize.w, height: displaySize.h }}
              />
              {/* Overlay canvas (transparent strokes + colored overlays) */}
              <canvas
                ref={overlayCanvasRef}
                width={displaySize.w}
                height={displaySize.h}
                className="absolute left-0 top-0 cursor-crosshair"
                onPointerDown={(e) => {
                  e.currentTarget.setPointerCapture(e.pointerId)
                  const p = getRelativePoint(e)
                  beginStroke(p)
                }}
                onPointerMove={(e) => {
                  if (!pointerDownRef.current) return
                  const p = getRelativePoint(e)
                  continueStroke(p)
                }}
                onPointerUp={() => endStroke()}
                onPointerCancel={() => endStroke()}
                onPointerLeave={() => endStroke()}
              />
            </div>
          ) : (
            <div className="flex min-h-[280px] items-center justify-center text-ink-500">
              Loading room image...
            </div>
          )}
        </div>

        <div className="space-y-4">
          <div className="rounded-[1.6rem] border border-sand-200 bg-white/75 p-5">
            <p className="text-sm font-semibold uppercase tracking-[0.18em] text-ink-700">
              Mode
            </p>
            <div className="mt-3 flex gap-3">
              {(['KEEP', 'CHANGE', 'REMOVE'] as RegionAction[]).map((m) => {
                const meta = ACTION_META[m]
                const active = m === activeAction
                return (
                  <button
                    key={m}
                    type="button"
                    className={`rounded-full border px-4 py-2 text-sm font-medium transition ${
                      active ? `border-transparent ${meta.swatch} text-ink-950` : 'border-sand-200 bg-white'
                    }`}
                    onClick={() => setActiveAction(m)}
                  >
                    {meta.label}
                  </button>
                )
              })}
            </div>
          </div>

          <div className="rounded-[1.6rem] border border-sand-200 bg-white/75 p-5">
            <p className="text-sm font-semibold uppercase tracking-[0.18em] text-ink-700">
              Brush
            </p>
            <div className="mt-4 space-y-4">
              <label className="block">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-medium text-ink-500">Radius</span>
                  <span className="text-xs text-ink-700">{brushRadius}px</span>
                </div>
                <input
                  type="range"
                  min={4}
                  max={60}
                  value={brushRadius}
                  onChange={(e) => setBrushRadius(Number(e.target.value))}
                  className="mt-2 w-full"
                />
              </label>

              <label className="flex items-center gap-3">
                <input
                  type="checkbox"
                  checked={eraseMode}
                  onChange={(e) => setEraseMode(e.target.checked)}
                />
                <span className="text-sm text-ink-700">Erase</span>
              </label>

              <div className="flex flex-wrap gap-2">
                <button
                  type="button"
                  onClick={undo}
                  className="inline-flex items-center gap-2 rounded-full border border-sand-200 bg-white px-4 py-2 text-sm text-ink-700 transition hover:bg-sand-25"
                  disabled={!undoStackRef.current.length}
                >
                  <Undo2 className="h-4 w-4" />
                  Undo
                </button>
                <button
                  type="button"
                  onClick={redo}
                  className="inline-flex items-center gap-2 rounded-full border border-sand-200 bg-white px-4 py-2 text-sm text-ink-700 transition hover:bg-sand-25"
                  disabled={!redoStackRef.current.length}
                >
                  <Redo2 className="h-4 w-4" />
                  Redo
                </button>
                <button
                  type="button"
                  onClick={clearActiveMask}
                  className="inline-flex items-center gap-2 rounded-full border border-sand-200 bg-white px-4 py-2 text-sm text-ink-700 transition hover:bg-sand-25"
                >
                  <RotateCcw className="h-4 w-4" />
                  Clear
                </button>
              </div>
            </div>
          </div>

          <div className="rounded-[1.6rem] border border-sand-200 bg-white/75 p-5">
            <p className="text-sm font-semibold uppercase tracking-[0.18em] text-ink-700">
              Region label
            </p>
            <input
              value={activeLabel}
              onChange={(e) => setActiveLabel(e.target.value)}
              placeholder="e.g. sofa, curtains, door, TV unit"
              className="mt-3 w-full rounded-[1.2rem] border border-sand-200 bg-white px-4 py-3 text-sm outline-none focus:border-accent-500"
            />
            <div className="mt-3 flex items-center gap-3">
              <button
                type="button"
                onClick={addActiveRegionToDrafts}
                className="inline-flex w-full items-center justify-center gap-2 rounded-full bg-ink-950 px-4 py-3 text-sm font-medium text-white transition hover:-translate-y-0.5"
              >
                Add Region
              </button>
            </div>
          </div>

          <div className="rounded-[1.6rem] border border-sand-200 bg-white/75 p-5">
            <div className="flex items-center justify-between">
              <p className="text-sm font-semibold uppercase tracking-[0.18em] text-ink-700">Pending</p>
              <p className="text-xs text-ink-500">{pendingRegions.length} region(s)</p>
            </div>
            <div className="mt-3 max-h-56 space-y-2 overflow-auto pr-2">
              {pendingRegions.length ? (
                pendingRegions.map((r) => (
                  <div key={r.id} className="flex items-center justify-between gap-2 rounded-xl border border-sand-200 bg-white p-2">
                    <div className="min-w-0">
                      <p className="truncate text-xs font-semibold text-ink-700">{r.label}</p>
                      <p className="text-[11px] text-ink-500">{r.action}</p>
                    </div>
                    <Trash2
                      className="h-4 w-4 cursor-pointer text-ink-400 hover:text-red-600"
                      onClick={() => setPendingRegions((cur) => cur.filter((x) => x.id !== r.id))}
                    />
                  </div>
                ))
              ) : (
                <p className="text-sm text-ink-500">Paint a region and add it above.</p>
              )}
            </div>
            <button
              type="button"
              onClick={savePendingRegions}
              disabled={!canSave || isSaving}
              className="mt-4 inline-flex w-full items-center justify-center gap-2 rounded-full bg-sand-25 px-4 py-3 text-sm font-medium text-ink-700 transition hover:bg-sand-25 disabled:cursor-not-allowed disabled:opacity-50"
            >
              <Save className="h-4 w-4" />
              {isSaving ? 'Saving...' : 'Save Regions'}
            </button>
          </div>

          <div className="rounded-[1.6rem] border border-sand-200 bg-white/75 p-5">
            <p className="text-sm font-semibold uppercase tracking-[0.18em] text-ink-700">
              Saved on server
            </p>
            <div className="mt-3 max-h-56 space-y-2 overflow-auto pr-2">
              {persistedRegions.length ? (
                persistedRegions.map((r) => (
                  <div key={r.id} className="flex items-center justify-between gap-2 rounded-xl border border-sand-200 bg-white p-2">
                    <div className="min-w-0">
                      <p className="truncate text-xs font-semibold text-ink-700">{r.label}</p>
                      <p className="text-[11px] text-ink-500">{r.action}</p>
                    </div>
                    <button
                      type="button"
                      className="text-xs font-medium text-red-600 hover:underline"
                      onClick={() => void deletePersistedConstraint(r.id)}
                    >
                      Delete
                    </button>
                  </div>
                ))
              ) : (
                <p className="text-sm text-ink-500">No saved region constraints yet.</p>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

