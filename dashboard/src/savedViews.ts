import { SavedView } from "./types";

const STORAGE_KEY = "github-repo-inventory-views";

export function loadViews(): SavedView[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return DEFAULT_VIEWS;
    const parsed = JSON.parse(raw) as SavedView[];
    return parsed.length ? parsed : DEFAULT_VIEWS;
  } catch {
    return DEFAULT_VIEWS;
  }
}

export function saveViews(views: SavedView[]) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(views));
}

export const DEFAULT_VIEWS: SavedView[] = [
  {
    id: "all",
    name: "All repositories",
    search: "",
    source: "all",
    visibility: "all",
    archived: "all",
    fork: "all",
    hasOpenPr: "all",
    dependabotOnly: false,
    inactiveOnly: false,
    unprotectedOnly: false,
    groupBy: "none",
  },
  {
    id: "dependabot",
    name: "Dependabot PRs",
    search: "",
    source: "all",
    visibility: "all",
    archived: "no",
    fork: "all",
    hasOpenPr: "yes",
    dependabotOnly: true,
    inactiveOnly: false,
    unprotectedOnly: false,
    groupBy: "source",
  },
  {
    id: "inactive",
    name: "Inactive repositories",
    search: "",
    source: "all",
    visibility: "all",
    archived: "no",
    fork: "all",
    hasOpenPr: "all",
    dependabotOnly: false,
    inactiveOnly: true,
    unprotectedOnly: false,
    groupBy: "source",
  },
  {
    id: "unprotected",
    name: "No branch protection",
    search: "",
    source: "all",
    visibility: "all",
    archived: "no",
    fork: "no",
    hasOpenPr: "all",
    dependabotOnly: false,
    inactiveOnly: false,
    unprotectedOnly: true,
    groupBy: "visibility",
  },
];
