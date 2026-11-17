import React from "react";

/**
 * Control mode: when true, ONLY text is drawn (no photos, flashes or decorations), so kit/zones.py can check frame by
 * frame that no letter sits where the apps cover the screen.
 */
export const TextOnly = React.createContext(false);
