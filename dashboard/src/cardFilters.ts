import { SavedView } from "./types";
import { DEFAULT_VIEWS } from "./savedViews";

export type SummaryCardId =
  | "all"
  | "archived"
  | "forks"
  | "open-prs"
  | "inactive"
  | "unprotected"
  | "partial";

export interface SummaryCardDef {
  id: SummaryCardId;
  label: string;
  filterable: boolean;
  hint?: string;
}

export const SUMMARY_CARDS: SummaryCardDef[] = [
  { id: "all", label: "Visible repos", filterable: true },
  { id: "archived", label: "Archived", filterable: true },
  { id: "forks", label: "Forks", filterable: true },
  { id: "open-prs", label: "Open PRs", filterable: true },
  { id: "inactive", label: "Inactive", filterable: true },
  { id: "unprotected", label: "No branch protection", filterable: true },
  { id: "partial", label: "Partial sync", filterable: true },
];

function baseView(): SavedView {
  return { ...DEFAULT_VIEWS[0] };
}

export function viewForCard(cardId: SummaryCardId): SavedView {
  switch (cardId) {
    case "all":
      return baseView();
    case "inactive":
      return { ...DEFAULT_VIEWS.find((view) => view.id === "inactive")! };
    case "unprotected":
      return { ...DEFAULT_VIEWS.find((view) => view.id === "unprotected")! };
    case "archived":
      return { ...baseView(), archived: "yes", groupBy: "none" };
    case "forks":
      return { ...baseView(), fork: "yes", groupBy: "none" };
    case "open-prs":
      return { ...baseView(), hasOpenPr: "yes", groupBy: "none" };
    case "partial":
      return { ...baseView(), partialOnly: true, groupBy: "none" };
    default:
      return baseView();
  }
}

export function activeCardForView(view: SavedView): SummaryCardId | null {
  for (const card of SUMMARY_CARDS) {
    if (card.id === "all") continue;
    if (viewsMatch(view, viewForCard(card.id))) {
      return card.id;
    }
  }
  if (viewsMatch(view, baseView())) {
    return "all";
  }
  return null;
}

function viewsMatch(a: SavedView, b: SavedView): boolean {
  return (
    a.search === b.search &&
    a.source === b.source &&
    a.visibility === b.visibility &&
    a.archived === b.archived &&
    a.fork === b.fork &&
    a.hasOpenPr === b.hasOpenPr &&
    a.dependabotOnly === b.dependabotOnly &&
    a.inactiveOnly === b.inactiveOnly &&
    a.unprotectedOnly === b.unprotectedOnly &&
    a.partialOnly === b.partialOnly
  );
}
