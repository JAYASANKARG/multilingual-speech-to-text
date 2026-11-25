import type { SVGProps } from 'react'

type IconProps = SVGProps<SVGSVGElement>

function Svg({ children, className, ...props }: IconProps) {
  return (
    <svg
      {...props}
      className={className ?? 'icon'}
      viewBox="0 0 24 24"
      aria-hidden="true"
      focusable="false"
    >
      {children}
    </svg>
  )
}

export function MicIcon(props: IconProps) {
  return (
    <Svg {...props}>
      <path d="M12 3.25a3 3 0 0 0-3 3v5.5a3 3 0 0 0 6 0v-5.5a3 3 0 0 0-3-3Z" />
      <path d="M5.75 11.5a6.25 6.25 0 0 0 12.5 0" />
      <path d="M12 17.75v3" />
    </Svg>
  )
}

export function StopIcon(props: IconProps) {
  return (
    <Svg {...props}>
      <rect x="7" y="7" width="10" height="10" rx="2.2" />
    </Svg>
  )
}

export function SearchIcon(props: IconProps) {
  return (
    <Svg {...props}>
      <circle cx="10.75" cy="10.75" r="5.75" />
      <path d="m15.2 15.2 4.05 4.05" />
    </Svg>
  )
}

export function ChevronDownIcon(props: IconProps) {
  return (
    <Svg {...props}>
      <path d="m7 9.5 5 5 5-5" />
    </Svg>
  )
}

export function ChevronRightIcon(props: IconProps) {
  return (
    <Svg {...props}>
      <path d="m9.5 7 5 5-5 5" />
    </Svg>
  )
}

export function PlusIcon(props: IconProps) {
  return (
    <Svg {...props}>
      <path d="M12 5.5v13M5.5 12h13" />
    </Svg>
  )
}

export function CopyIcon(props: IconProps) {
  return (
    <Svg {...props}>
      <rect x="8.5" y="8.5" width="10" height="10" rx="2" />
      <path d="M15.5 8.5v-1a2 2 0 0 0-2-2h-6a2 2 0 0 0-2 2v6a2 2 0 0 0 2 2h1" />
    </Svg>
  )
}

export function DownloadIcon(props: IconProps) {
  return (
    <Svg {...props}>
      <path d="M12 4.5v10.25" />
      <path d="m7.75 10.75 4.25 4.25 4.25-4.25" />
      <path d="M5 18.5h14" />
    </Svg>
  )
}

export function XIcon(props: IconProps) {
  return (
    <Svg {...props}>
      <path d="m6.5 6.5 11 11M17.5 6.5l-11 11" />
    </Svg>
  )
}

export function AlertIcon(props: IconProps) {
  return (
    <Svg {...props}>
      <path d="M12 3.5 21 20H3L12 3.5Z" />
      <path d="M12 9.5v4.5" />
      <path d="M12 17.2v.1" />
    </Svg>
  )
}

export function ShieldIcon(props: IconProps) {
  return (
    <Svg {...props}>
      <path d="M12 3.5 19 6v5.5c0 4.2-2.9 7.4-7 9-4.1-1.6-7-4.8-7-9V6l7-2.5Z" />
      <path d="m9 11.75 2.1 2.1L15 9.9" />
    </Svg>
  )
}

/** The product mark: four level bars on an ink tile. */
export function BrandGlyph(props: IconProps) {
  return (
    <svg {...props} viewBox="0 0 24 24" aria-hidden="true" focusable="false">
      <rect x="3.5" y="9.5" width="2.6" height="5" rx="1.3" fill="currentColor" opacity="0.5" />
      <rect x="8.2" y="5.5" width="2.6" height="13" rx="1.3" fill="currentColor" />
      <rect x="12.9" y="7.5" width="2.6" height="9" rx="1.3" fill="currentColor" opacity="0.8" />
      <rect x="17.6" y="10.5" width="2.6" height="3" rx="1.3" fill="currentColor" opacity="0.45" />
    </svg>
  )
}
