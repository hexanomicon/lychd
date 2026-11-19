import { createContext } from "svelte";
import { appPinsKey, defaultAppPins, readAppPins, type ApplicationId } from "./applications";

export function createApplicationPins() {
  let ids = $state<ApplicationId[]>([...defaultAppPins]);
  function load() {
    try {
      ids = readAppPins(localStorage.getItem(appPinsKey));
    } catch {
      /* Optional layout storage. */
    }
  }
  function toggle(id: ApplicationId) {
    ids = ids.includes(id) ? ids.filter((current) => current !== id) : [...ids, id];
    try {
      localStorage.setItem(appPinsKey, JSON.stringify(ids));
    } catch {
      /* Retain the current tab's choice. */
    }
  }
  return {
    get ids() {
      return ids;
    },
    load,
    toggle,
  };
}
export const [getApplicationPins, setApplicationPins] =
  createContext<ReturnType<typeof createApplicationPins>>();
