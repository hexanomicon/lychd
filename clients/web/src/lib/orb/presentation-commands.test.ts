import { describe, expect, it } from 'vitest';
import { parseOrbPresentationCommand, seekObservationFrame } from './presentation-commands';
describe('Orb presentation grammar', () => {
  it.each(['zoom in', 'zoom out', 'fit graph', 'pause', 'go live', 'go back 1 seconds', 'go forward 3600 seconds'])('accepts %s', command => {
    expect(parseOrbPresentationCommand(command)).not.toBeNull();
  });
  it.each(['resume run', 'delete run-a', 'clear history', 'change provider', 'go back 0 seconds', 'go back 3601 seconds', 'go back 1.5 seconds', 'go back -1 seconds', 'zoom in and pause', 'focus run run-a'])('rejects %s', command => {
    expect(parseOrbPresentationCommand(command)).toBeNull();
  });
  it.each(['Zoom in.', 'ZOOM OUT!', 'fit graph?', 'pause.', 'go live!', 'go back 10 seconds.'])('accepts terminal ASR punctuation in %s', command => {
    expect(parseOrbPresentationCommand(command)).toEqual(parseOrbPresentationCommand(command.slice(0, -1)));
  });
  it.each(['zoom in. pause', 'zoom in..', 'pause; go live'])('does not broaden punctuation into multiple commands: %s', command => {
    expect(parseOrbPresentationCommand(command)).toBeNull();
  });
  const frames = [{id:1,observedAt:1000}, {id:2,observedAt:9000}, {id:3,observedAt:11000}];
  it('chooses the nearest actual receipt, resolving ties to the earlier frame', () => {
    expect(seekObservationFrame(frames,null,-3)).toBe(frames[1]);
    expect(seekObservationFrame(frames,1,9)).toBe(frames[1]);
  });
  it('refuses outside bounds, absent history, and a trimmed pinned cursor', () => {
    expect(seekObservationFrame(frames,null,1)).toBeUndefined();
    expect(seekObservationFrame(frames,null,-11)).toBeUndefined();
    expect(seekObservationFrame([],null,-1)).toBeUndefined();
    expect(seekObservationFrame(frames,99,-1)).toBeUndefined();
  });
});
