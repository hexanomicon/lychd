import type { components } from "../api/openapi";

export type Point = components["schemas"]["CanvasPoint"];
export type Bounds = components["schemas"]["CanvasBounds"];
export type Stroke = components["schemas"]["CanvasStroke"];
export type Artwork = components["schemas"]["CanvasArtwork"];
export type CanvasNode = components["schemas"]["CanvasNode"];
export type CanvasEdge = components["schemas"]["CanvasEdge"];
export type Scene = components["schemas"]["CanvasScene"];
export type Document = components["schemas"]["CanvasDocument"];
export type Selection = components["schemas"]["CanvasSelection"];
export type CanvasCrop = components["schemas"]["CanvasCrop"];
export type Packet = components["schemas"]["CanvasPacket"];
export type Proposal = components["schemas"]["CanvasProposal"];
export type Tool = "select" | "lasso" | "draw" | "box" | "connect" | "pan";
