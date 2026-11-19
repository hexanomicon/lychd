export const operationGroups = [
  {
    label: "Runtime",
    areas: [
      { id: "board", title: "Capability board", mark: "◎" },
      { id: "transitions", title: "Transitions", mark: "⇄" },
      { id: "installation", title: "Installation", mark: "⌂" },
      { id: "orchestration", title: "Orchestration", mark: "≋" }
    ]
  },
  {
    label: "Animators",
    areas: [
      { id: "inventory", title: "Animator inventory", mark: "◇" },
      { id: "fallback", title: "Animator fallback", mark: "↳" }
    ]
  },
  {
    label: "Signals and inquiry",
    areas: [
      { id: "affect", title: "Affect routing", mark: "∿" },
      { id: "exploration", title: "Exploration", mark: "⊙" }
    ]
  },
  {
    label: "Intercom",
    areas: [
      { id: "skills", title: "Advertised skills", mark: "✧" },
      { id: "peers", title: "Peer enrollment", mark: "⇆" },
      { id: "colleagues", title: "Colleagues", mark: "◌" }
    ]
  },
  {
    label: "People and access",
    areas: [
      { id: "principals", title: "Users and Principals", mark: "♙" },
      { id: "access", title: "Access policy", mark: "⚿" }
    ]
  }
] as const;

export type Operation = (typeof operationGroups)[number]["areas"][number];
export type OperationId = Operation["id"];

const areas: readonly Operation[] = operationGroups.flatMap((group) => [...group.areas] as Operation[]);

export function findOperation(id: string | null): Operation {
  return areas.find((area) => area.id === id) ?? operationGroups[0].areas[0];
}
