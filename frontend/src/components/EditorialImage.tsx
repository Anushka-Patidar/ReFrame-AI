import { useEffect, useState, type ReactNode } from 'react'

type EditorialImageProps = {
  src?: string | null
  alt: string
  className?: string
  overlay?: boolean
  fit?: 'cover' | 'contain'
  children?: ReactNode
}

export function EditorialImage({
  src,
  alt,
  className = '',
  overlay = false,
  fit = 'cover',
  children,
}: EditorialImageProps) {
  const [hasError, setHasError] = useState(false)

  useEffect(() => {
    setHasError(false)
  }, [src])

  const showFallback = !src || hasError

  return (
    <div className={`group relative overflow-hidden bg-sand-100 ${className}`}>
      {showFallback ? (
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_top,rgba(134,100,74,0.18),transparent_48%),linear-gradient(145deg,#e8ddd0,#f6f1ea)]" />
      ) : (
        <img
          src={src}
          alt={alt}
          onError={() => setHasError(true)}
          className={`h-full w-full transition duration-700 ease-out group-hover:scale-[1.02] ${
            fit === 'contain' ? 'object-contain bg-[#1a1714]' : 'object-cover'
          }`}
        />
      )}
      {overlay ? (
        <div className="absolute inset-0 bg-gradient-to-t from-black/55 via-black/10 to-transparent" />
      ) : null}
      {children ? <div className="absolute inset-0">{children}</div> : null}
    </div>
  )
}
