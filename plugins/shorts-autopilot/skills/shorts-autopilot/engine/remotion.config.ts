import { Config } from "@remotion/cli/config";

// PNG frames and BT.709 color: JPEG frames come out as full-range yuvj420p, which social apps mislabel.
Config.setVideoImageFormat("png");
Config.setColorSpace("bt709");
Config.setPixelFormat("yuv420p");
Config.setOverwriteOutput(true);
Config.setEntryPoint("./src/index.ts");
Config.setChromiumOpenGlRenderer("angle");
