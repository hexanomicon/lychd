import { act, fireEvent, render, screen, waitFor } from '@testing-library/svelte';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { fixtureRun } from '$lib/pages/orb/state/__fixtures__/snapshot';
import { createWorkCommandRegistry, workCommandKey } from '$lib/shell/state/work-commands';
const camera = vi.hoisted(() => ({ setZoom: vi.fn(async () => true), fitView: vi.fn(async () => true) }));
vi.mock('@xyflow/svelte', async original => {
  const module = await original<typeof import('@xyflow/svelte')>();
  return { ...module, useSvelteFlow: () => ({ ...module.useSvelteFlow(), getZoom: () => 1, setZoom:camera.setZoom, fitView:camera.fitView }) };
});
vi.mock('$lib/api/client' , () => ({ getOrbRun: vi.fn() }));
vi.mock('$lib/pages/orb/state/live', async original => ({ ...await original<typeof import('$lib/pages/orb/state/live')>(), getOrbCatalogue: vi.fn(), listenToOrb: vi.fn() }));
import { getOrbRun } from '$lib/api/client';
import { getOrbCatalogue, listenToOrb } from '$lib/pages/orb/state/live';
import OrbField from './OrbField.svelte';

beforeEach(() => {
  vi.clearAllMocks();
  vi.stubGlobal('EventSource', vi.fn());
  vi.stubGlobal('matchMedia', vi.fn(() => ({ matches: false, addEventListener: vi.fn(), removeEventListener: vi.fn(), addListener: vi.fn(), removeListener: vi.fn() })));
  vi.stubGlobal('ResizeObserver', class { observe() {} unobserve() {} disconnect() {} });
  vi.mocked(getOrbCatalogue).mockResolvedValue({schema_version:1,snapshot_at:'2026-09-22T00:00:00Z',capture:'process_local',next_cursor:null,runs:[fixtureRun().run]});
  vi.mocked(getOrbRun).mockResolvedValue(fixtureRun());
  vi.mocked(listenToOrb).mockReturnValue(vi.fn());
});
afterEach(() => { vi.restoreAllMocks(); vi.unstubAllGlobals(); });
async function mount() {
  const registry = createWorkCommandRegistry();
  const view = render(OrbField, {context:new Map([[workCommandKey,registry]])});
  await waitFor(() => expect(listenToOrb).toHaveBeenCalledOnce());
  await waitFor(() => expect(screen.getByRole('button',{name:'Pause live field'}).hasAttribute('disabled')).toBe(false));
  await waitFor(() => expect(screen.getByRole('button', {name:'Zoom in'})).toBeTruthy());
  return {registry,view};
}

describe('Orb tab observation commands', () => {
  it('routes camera commands through the owned public helpers', async () => {
    const {registry,view}=await mount();
    camera.setZoom.mockClear(); camera.fitView.mockClear();
    let result;
    const pending = registry.execute('zoom in',registry.capture());
    await act();
    result = await pending;
    expect(result).toMatchObject({status:'applied'});
    expect(camera.setZoom).toHaveBeenLastCalledWith(1.2,{duration:0});
    const zoomOut = registry.execute('zoom out',registry.capture());
    await act();
    await zoomOut;
    expect(camera.setZoom).toHaveBeenLastCalledWith(1/1.2,{duration:0});
    const fit = registry.execute('fit graph',registry.capture());
    await act();
    await fit;
    expect(camera.fitView).toHaveBeenLastCalledWith({padding:0.18,minZoom:0.1,maxZoom:1,duration:0});
    view.unmount();
  });
  it('settles an unavailable renderer instead of leaving a command pending', async () => {
    const {registry,view}=await mount();
    camera.setZoom.mockImplementationOnce(() => new Promise<boolean>(() => {}));
    const pending=registry.execute('zoom in',registry.capture());
    await act();
    expect(await pending).toMatchObject({status:'unavailable'});
    view.unmount();
  });
  it('does not apply a queued camera request after navigation invalidates its capture', async () => {
    const {registry,view}=await mount();
    camera.setZoom.mockClear();
    const pending=registry.execute('zoom in',registry.capture());
    registry.invalidate();
    let result;
    await act();
    result = await pending;
    expect(result).toMatchObject({status:'stale'});
    expect(camera.setZoom).not.toHaveBeenCalled();
    view.unmount();
  });
  it('pauses and resumes using existing timeline state and refuses unknown commands without mutation', async () => {
    const {registry,view}=await mount();
    const calls=vi.mocked(getOrbRun).mock.calls.length;
    expect((await registry.execute('cancel run',registry.capture())).status).toBe('unsupported');
    expect(screen.getByRole('button',{name:'LIVE'}).getAttribute('aria-pressed')).toBe('true');
    let result;
    await act(async()=>{result=await registry.execute('pause',registry.capture());});
    expect(result).toMatchObject({status:'applied',summary:expect.stringContaining('tab observation')});
    expect(screen.getByRole('button',{name:'LIVE'}).getAttribute('aria-pressed')).toBe('false');
    await act(async()=>{await registry.execute('go live',registry.capture());});
    expect(screen.getByRole('button',{name:'LIVE'}).getAttribute('aria-pressed')).toBe('true');
    expect(getOrbRun).toHaveBeenCalledTimes(calls);
    view.unmount();
  });
  it('fences history and manual camera changes plus unmount, while live receipts keep the target', async () => {
    const {registry,view}=await mount();
    const captured=registry.capture();
    const initial=fixtureRun();
    await act(()=>vi.mocked(listenToOrb).mock.calls[0]![2].onFrame({schema_version:1,run_id:'run-a',kind:'evidence',after_seq:0,cursor:0,snapshot:{...initial,run:{...initial.run,status:'done'}}}));
    expect(registry.isCurrent(captured)).toBe(true);
    await fireEvent.click(screen.getByRole('button',{name:'Pause live field'}));
    expect((await registry.execute('go live',captured)).status).toBe('stale');
    const cameraCapture=registry.capture();
    await fireEvent.click(screen.getByRole('button',{name:'Zoom in'}));
    expect(registry.isCurrent(cameraCapture)).toBe(false);
    const last=registry.capture();
    view.unmount();
    expect(registry.isCurrent(last)).toBe(false);
  });
  it('seeks actual retained frames and refuses times beyond the observed window', async () => {
    const now=vi.spyOn(Date,'now').mockReturnValue(100000);
    const {registry,view}=await mount();
    now.mockReturnValue(110000);
    const initial=fixtureRun();
    await act(()=>vi.mocked(listenToOrb).mock.calls[0]![2].onFrame({schema_version:1,run_id:'run-a',kind:'evidence',after_seq:0,cursor:0,snapshot:{...initial,run:{...initial.run,status:'done'}}}));
    let result;
    await act(async()=>{result=await registry.execute('go back 10 seconds',registry.capture());});
    expect(result).toMatchObject({status:'applied',summary:expect.stringContaining('capture 1')});
    const cursor=screen.getByRole('slider',{name:'Seek tab observation time'}).getAttribute('aria-valuetext');
    expect((await registry.execute('go back 1 seconds',registry.capture())).status).toBe('unavailable');
    expect(screen.getByRole('slider',{name:'Seek tab observation time'}).getAttribute('aria-valuetext')).toBe(cursor);
    view.unmount();
  });
});
