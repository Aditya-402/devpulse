process.env.TZ = "Asia/Kolkata"; // before any Date is created

const test = require("node:test");
const assert = require("node:assert");
const { ymd, computeStreak, bestStreak } = require("./streak.js");

const tasksOn = (...dates) => dates.map(date => ({ date }));
// 00:30 IST on 2026-10-29 is still 2026-10-28 in UTC.
const justAfterMidnightIST = new Date("2026-10-29T00:30:00+05:30");

test("runs in India time", () => {
  assert.strictEqual(ymd(justAfterMidnightIST), "2026-10-29");
});

test("no tasks -> no streak", () => {
  assert.deepStrictEqual(computeStreak([], justAfterMidnightIST), { streak: 0, todayEmpty: true });
});

test("task logged at 00:30 IST counts for the local day", () => {
  const r = computeStreak(tasksOn("2026-10-29"), justAfterMidnightIST);
  assert.deepStrictEqual(r, { streak: 1, todayEmpty: false });
});

test("00:30 IST with yesterday logged: today empty, streak counts from yesterday", () => {
  const r = computeStreak(tasksOn("2026-10-28", "2026-10-27"), justAfterMidnightIST);
  assert.deepStrictEqual(r, { streak: 2, todayEmpty: true });
});

test("consecutive days including today", () => {
  const r = computeStreak(tasksOn("2026-10-29", "2026-10-28", "2026-10-27"), justAfterMidnightIST);
  assert.deepStrictEqual(r, { streak: 3, todayEmpty: false });
});

test("a gap ends the streak", () => {
  const r = computeStreak(tasksOn("2026-10-29", "2026-10-28", "2026-10-26"), justAfterMidnightIST);
  assert.strictEqual(r.streak, 2);
});

test("older tasks without yesterday or today give no streak", () => {
  const r = computeStreak(tasksOn("2026-10-26"), justAfterMidnightIST);
  assert.deepStrictEqual(r, { streak: 0, todayEmpty: true });
});

test("duplicate tasks on one day count once", () => {
  const r = computeStreak(tasksOn("2026-10-29", "2026-10-29", "2026-10-28"), justAfterMidnightIST);
  assert.strictEqual(r.streak, 2);
});

test("streak spans a month boundary", () => {
  const now = new Date("2026-11-01T00:30:00+05:30");
  const r = computeStreak(tasksOn("2026-11-01", "2026-10-31", "2026-10-30"), now);
  assert.strictEqual(r.streak, 3);
});

test("bestStreak: no tasks -> 0", () => {
  assert.strictEqual(bestStreak([]), 0);
});

test("bestStreak: a single task -> 1", () => {
  assert.strictEqual(bestStreak(tasksOn("2026-10-29")), 1);
});

test("bestStreak: finds the longest run, not the latest", () => {
  const t = tasksOn("2026-10-01", "2026-10-02", "2026-10-03", "2026-10-04", "2026-10-20", "2026-10-21");
  assert.strictEqual(bestStreak(t), 4);
});

test("bestStreak: unsorted input", () => {
  assert.strictEqual(bestStreak(tasksOn("2026-10-03", "2026-10-01", "2026-10-02", "2026-10-09")), 3);
});

test("bestStreak: duplicate days count once", () => {
  assert.strictEqual(bestStreak(tasksOn("2026-10-01", "2026-10-01", "2026-10-01", "2026-10-02")), 2);
});

test("bestStreak: a one-day gap splits runs", () => {
  assert.strictEqual(bestStreak(tasksOn("2026-10-01", "2026-10-02", "2026-10-04", "2026-10-05")), 2);
});

test("bestStreak: spans month and year boundaries", () => {
  assert.strictEqual(bestStreak(tasksOn("2026-10-30", "2026-10-31", "2026-11-01")), 3);
  assert.strictEqual(bestStreak(tasksOn("2025-12-31", "2026-01-01")), 2);
});

test("bestStreak: leap day is consecutive with Feb 28 and Mar 1", () => {
  assert.strictEqual(bestStreak(tasksOn("2028-02-28", "2028-02-29", "2028-03-01")), 3);
});

test("bestStreak: never less than the current streak", () => {
  const t = tasksOn("2026-10-29", "2026-10-28", "2026-10-27", "2026-10-10");
  assert.ok(bestStreak(t) >= computeStreak(t, justAfterMidnightIST).streak);
});
