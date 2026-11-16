/** Owned camera request. It grants presentation access only while its capture is current. */
export interface GraphCameraCommand {
  readonly id: number;
  readonly action: 'zoom-in' | 'zoom-out' | 'fit';
  readonly isCurrent: () => boolean;
  readonly complete: (status: 'applied' | 'stale' | 'unavailable') => void;
}
