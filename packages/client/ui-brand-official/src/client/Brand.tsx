import type { SidebarBrandMarkOwnerProps } from '@deepseek-ai/dsh-client-ui-sidebar/client'

/**
 * Render the official mark with the presentation requested by its host surface.
 * @param props - Host-supplied mark presentation.
 * @returns the official whale mark.
 */
export function OfficialBrandMark({ size }: SidebarBrandMarkOwnerProps) {
  return <img
    src="/favicon.svg"
    width={size}
    height={size}
    alt=""
    style={{ display: 'block', borderRadius: '50%' }}
  />
}

/**
 * Render the official name artwork without its independently slotted mark.
 * @returns the official name wordmark.
 */
export function OfficialBrandName() {
  return <span style={{ fontSize:18,fontWeight:600,lineHeight:24 }}>Vertax Work</span>
}
