// Variables used by Scriptable.
// These must be at the very top of the file. Do not edit.
// icon-color: deep-brown; icon-glyph: magic;
/*
Codex Limits Lock Screen Widget for Scriptable.
Displays percentage REMAINING for the 5-hour and weekly Codex windows.
Recommended widget family: accessoryRectangular.
*/

const FILE_NAME = "codex-limits.json";
const REFRESH_MINUTES = 15;

const fm = FileManager.iCloud();
const filePath = fm.joinPath(fm.documentsDirectory(), FILE_NAME);

let data = null;
let errorMessage = null;

try {
  if (!fm.fileExists(filePath)) {
    throw new Error(`Missing ${FILE_NAME}`);
  }

  await fm.downloadFileFromiCloud(filePath);
  data = JSON.parse(fm.readString(filePath));

  if (
    typeof data.fiveHourPercent !== "number" ||
    typeof data.weeklyPercent !== "number"
  ) {
    throw new Error("Invalid data file");
  }
} catch (error) {
  errorMessage = String(error.message || error);
}

const widget = new ListWidget();
widget.setPadding(0, 2, 0, 2);
widget.refreshAfterDate = new Date(Date.now() + REFRESH_MINUTES * 60 * 1000);

if (errorMessage) {
  addHeader();
  addTerminalLine("DATA UNAVAILABLE", 7);
} else {
  addHeader();
  addUsageRow("05H", data.fiveHourPercent, formatResetTime(data.fiveHourResetsAt));
  addUsageRow("07D", data.weeklyPercent, formatResetDate(data.weeklyResetsAt));
}

function addHeader() {
  const title = widget.addText(">> CODEX");
  title.font = Font.semiboldMonospacedSystemFont(15);
  title.lineLimit = 1;
  title.minimumScaleFactor = 1;
}

function addUsageRow(label, percent, reset) {
  const resetSuffix = reset ? ` ${reset}` : "";
  addTerminalLine(`${label} ${formatPercent(percent)}${resetSuffix}`, 7);
}

function addTerminalLine(value, size) {
  const text = widget.addText(value);
  text.font = Font.semiboldMonospacedSystemFont(16);
  text.lineLimit = 1;
  text.minimumScaleFactor = 1;
}

function normalizedPercent(value) {
  return Math.round(Math.max(0, Math.min(100, value)));
}

function formatPercent(value) {
  return `${String(normalizedPercent(value)).padStart(3, "0")}%`;
}

function formatResetTime(timestamp) {
  if (typeof timestamp !== "number") return "";
  const date = new Date(timestamp * 1000);
  return `${pad2(date.getHours())}:${pad2(date.getMinutes())}`;
}

function formatResetDate(timestamp) {
  if (typeof timestamp !== "number") return "";
  const date = new Date(timestamp * 1000);
  return `${pad2(date.getDate())}.${pad2(date.getMonth() + 1)}`;
}

function pad2(value) {
  return String(value).padStart(2, "0");
}

Script.setWidget(widget);

if (config.runsInApp) {
  await widget.presentAccessoryRectangular();
}

Script.complete();
