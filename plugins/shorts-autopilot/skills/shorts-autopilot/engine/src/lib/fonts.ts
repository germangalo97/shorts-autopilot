/** Fonts (Google Fonts, OFL license), Latin subset: accented letters and Spanish punctuation included. */
import { loadFont as anton } from "@remotion/google-fonts/Anton";
import { loadFont as instrumentSerif } from "@remotion/google-fonts/InstrumentSerif";
import { loadFont as interTight } from "@remotion/google-fonts/InterTight";
import { loadFont as jetbrains } from "@remotion/google-fonts/JetBrainsMono";
import { loadFont as spaceGrotesk } from "@remotion/google-fonts/SpaceGrotesk";
import type { FontName } from "../props";

const latin = { subsets: ["latin" as const] };

export const FONTS: Record<FontName, string> = {
  anton: anton("normal", { weights: ["400"], ...latin }).fontFamily,
  serif: instrumentSerif("normal", { weights: ["400"], ...latin }).fontFamily,
  inter: interTight("normal", { weights: ["500", "700", "800", "900"], ...latin }).fontFamily,
  grotesk: spaceGrotesk("normal", { weights: ["500", "700"], ...latin }).fontFamily,
  mono: jetbrains("normal", { weights: ["400", "700", "800"], ...latin }).fontFamily,
};
