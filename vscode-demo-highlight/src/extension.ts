import * as vscode from "vscode";
import * as path from "path";
import * as fs from "fs";

const HIGHLIGHTS_FILENAME = ".demo-highlights.json";

interface HighlightEntry {
  lines: [number, number]; // [startLine, endLine] 1-based inclusive
  style: "box" | "arrow" | "underline" | "highlight";
  color?: string;
  label?: string;
}

let activeDecorations: vscode.TextEditorDecorationType[] = [];
let fileWatcher: vscode.FileSystemWatcher | undefined;

export function activate(context: vscode.ExtensionContext) {
  const pattern = new vscode.RelativePattern(
    vscode.workspace.workspaceFolders?.[0] ?? "",
    HIGHLIGHTS_FILENAME
  );

  fileWatcher = vscode.workspace.createFileSystemWatcher(pattern);
  fileWatcher.onDidChange(() => applyHighlights(context));
  fileWatcher.onDidCreate(() => applyHighlights(context));
  fileWatcher.onDidDelete(() => clearAllDecorations());

  context.subscriptions.push(fileWatcher);
  context.subscriptions.push(
    vscode.commands.registerCommand("demoHighlight.clear", clearAllDecorations)
  );

  // Apply on activation in case file already exists
  applyHighlights(context);
}

export function deactivate() {
  clearAllDecorations();
}

function clearAllDecorations() {
  for (const dec of activeDecorations) {
    dec.dispose();
  }
  activeDecorations = [];
}

function applyHighlights(context: vscode.ExtensionContext) {
  clearAllDecorations();

  const workspaceFolder = vscode.workspace.workspaceFolders?.[0];
  if (!workspaceFolder) {
    return;
  }

  const highlightsPath = path.join(
    workspaceFolder.uri.fsPath,
    HIGHLIGHTS_FILENAME
  );

  if (!fs.existsSync(highlightsPath)) {
    return;
  }

  let entries: HighlightEntry[];
  try {
    const raw = fs.readFileSync(highlightsPath, "utf-8");
    entries = JSON.parse(raw);
  } catch {
    return; // Invalid JSON or read error — silently skip
  }

  if (!Array.isArray(entries) || entries.length === 0) {
    return;
  }

  const editor = vscode.window.activeTextEditor;
  if (!editor) {
    return;
  }

  for (const entry of entries) {
    const decorationType = createDecorationType(entry, context);
    if (!decorationType) {
      continue;
    }

    const startLine = Math.max(0, entry.lines[0] - 1); // Convert 1-based to 0-based
    const endLine = Math.max(startLine, entry.lines[1] - 1);

    const range = new vscode.Range(
      new vscode.Position(startLine, 0),
      new vscode.Position(endLine, Number.MAX_SAFE_INTEGER)
    );

    editor.setDecorations(decorationType, [{ range }]);
    activeDecorations.push(decorationType);
  }
}

function createDecorationType(
  entry: HighlightEntry,
  context: vscode.ExtensionContext
): vscode.TextEditorDecorationType | undefined {
  switch (entry.style) {
    case "box":
      return vscode.window.createTextEditorDecorationType({
        isWholeLine: true,
        backgroundColor: entry.color || "#FFD70044",
        border: `2px solid ${stripAlpha(entry.color || "#FFD700")}`,
        borderRadius: "3px",
      });

    case "arrow":
      return vscode.window.createTextEditorDecorationType({
        isWholeLine: true,
        gutterIconPath: vscode.Uri.file(
          path.join(context.extensionPath, "assets", "arrow.svg")
        ),
        gutterIconSize: "contain",
        backgroundColor: entry.color || "#FF634722",
      });

    case "underline":
      return vscode.window.createTextEditorDecorationType({
        isWholeLine: true,
        borderWidth: "0 0 2px 0",
        borderStyle: "solid",
        borderColor: entry.color || "#FF6347",
      });

    case "highlight":
      return vscode.window.createTextEditorDecorationType({
        isWholeLine: true,
        backgroundColor: entry.color || "#87CEEB33",
      });

    default:
      return undefined;
  }
}

/**
 * Strip alpha channel from hex color for use in border (borders don't support alpha).
 * e.g. "#FFD70044" → "#FFD700"
 */
function stripAlpha(color: string): string {
  if (color.startsWith("#") && color.length === 9) {
    return color.slice(0, 7);
  }
  return color;
}
