import { recipes, type Recipe } from "$lib/compositions/video";
import { makeNode, type Blueprint } from "./blueprint";

export function compositionRecipe(value: string | null): Recipe | null {
  return value && Object.hasOwn(recipes, value) ? value as Recipe : null;
}

const stages: Record<Recipe, { prepare: string; material: string; produce: string; review: string; criteria: string }> = {
  "illustrated-story": {
    prepare: "Plan story beats", material: "Illustrated storyboard", produce: "Animate selected frames",
    review: "Review shot continuity", criteria: "Check character, palette and camera continuity against the approved storyboard."
  },
  "animated-lesson": {
    prepare: "Plan teaching scenes", material: "Diagram and pose sheet", produce: "Render lesson frames",
    review: "Review motion and labels", criteria: "Check claim sources, labels, camera position and legibility throughout the lesson."
  },
  "captioned-excerpt": {
    prepare: "Admit source excerpt", material: "Clip selection and timecodes", produce: "Trim approved excerpt",
    review: "Review captions and use", criteria: "Check source, permitted use, in/out points, caption spelling and safe area."
  }
};

/** Browser-editable studies of the Atelier visual and Broadcast editorial contracts. */
export function compositionBlueprint(recipe: Recipe): Blueprint {
  const stage = stages[recipe];
  const revision = { type:"string", description:"Exact source or candidate revision under review" };
  const pictureSchema = JSON.stringify({ type:"object", required:["revision","timebase","frames"],
    properties:{ revision, timebase:{type:"string"}, frames:{type:"integer",minimum:1} } });
  const reviewSchema = JSON.stringify({ type:"object", required:["revision","decision","findings"],
    properties:{ revision, decision:{type:"string",enum:["ready_for_review","changes_requested"]},
      findings:{type:"array",items:{type:"object",required:["frame","observation"],properties:{
        frame:{type:"integer",minimum:0},observation:{type:"string"}
      }}} } });
  const review = { inputs:"Visual candidate revision, approved storyboard, acceptance criteria", schema:reviewSchema,
    system:"Identify each visible finding and its affected frame. Keep the candidate revision attached to the review.",
    user:stage.criteria, fallback:"Return the candidate and missing evidence for visual review" };
  const nodes = [
    { ...makeNode("brief", "object", "Short video brief", "", "Script, recipe and requested duration from Atelier."),
      schema: JSON.stringify({ type: "object", properties: { recipe: { const: recipe }, script: { type: "string" },
        duration_seconds: { type: "integer", minimum: 1, maximum: 180 } }, required: ["recipe","script","duration_seconds"] }) },
    makeNode("direction", "subflow", "Direction & storyboard", "", "Freeze references and prepare the visual direction for operator review."),
    makeNode("picture", "subflow", "Picture production", "", stage.criteria),
    makeNode("edit", "subflow", "Editorial cut", "", "Broadcast places reviewed picture and admitted sound or captions onto the same timebase."),
    { ...makeNode("review", "ledger", "Review record", "", "Record the exact version, duration, open findings and the operator’s decision."),
      inputs:"Review cut and editorial findings", schema:reviewSchema },
    makeNode("plan", "agent", stage.prepare, "direction", stage.criteria),
    makeNode("storyboard", "object", stage.material, "direction", "Keep the proposed timing and exact source references."),
    makeNode("approval", "router", "Storyboard approved?", "direction", "Proceed with the accepted revision or send it back for a correction."),
    { ...makeNode("produce", "agent", stage.produce, "picture", "Work from approved material and the chosen target profile."),
      inputs:"Approved storyboard revision, target visual profile", schema:pictureSchema,
      system:"Work only from accepted material. Return the candidate revision, timebase and frame count.",
      user:stage.produce + " using the exact storyboard approved for this commission." },
    { ...makeNode("candidate", "object", "Visual candidate", "picture", "Retain the visual revision, provenance and timebase."), schema:pictureSchema },
    { ...makeNode("check", "agent", stage.review, "picture", stage.criteria), ...review },
    makeNode("timeline", "object", "Editorial timeline", "edit", "Pin source spans, duration and captions against approved material."),
    makeNode("render", "agent", "Render and verify cut", "edit", "Measure the output duration and check the exact timeline revision."),
    makeNode("cut", "object", "Review cut", "edit", "Return a reviewable cut with its references and findings.")
  ];
  const edges: Blueprint["edges"] = [];
  function connect(source: string, target: string, relation: Blueprint["edges"][number]["relation"], label: string) {
    edges.push({ id: source + "-" + target, source, target, relation, label });
  }
  connect("brief", "direction", "supplies", "Commission");
  connect("direction", "picture", "guards", "Approved storyboard");
  connect("picture", "edit", "supplies", "Accepted picture");
  connect("edit", "review", "records", "Cut and findings");
  connect("plan", "storyboard", "produces", "Storyboard revision");
  connect("storyboard", "approval", "supplies", "Proposed revision");
  connect("approval", "plan", "guards", "Correction requested");
  connect("produce", "candidate", "produces", "New candidate");
  connect("candidate", "check", "supplies", "Visual review");
  connect("timeline", "render", "supplies", "Pinned timebase");
  connect("render", "cut", "produces", "Rendered candidate");
  return { format: "loom-blueprint/1", nodes, edges };
}
