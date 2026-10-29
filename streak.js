// Streak calculation, shared by index.html (browser) and streak.test.js (node).
(function (root) {
  const ymd = d => d.toLocaleDateString("en-CA"); // YYYY-MM-DD, local time

  // Streak: consecutive days with >= 1 task, counted back from today
  // (or from yesterday if nothing is logged yet today).
  function computeStreak(tasks, now) {
    const withTasks = new Set(tasks.map(t => t.date));
    const cursor = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    const todayEmpty = !withTasks.has(ymd(cursor));
    if (todayEmpty) cursor.setDate(cursor.getDate() - 1);
    let streak = 0;
    while (withTasks.has(ymd(cursor))) {
      streak++;
      cursor.setDate(cursor.getDate() - 1);
    }
    return { streak, todayEmpty };
  }

  // Longest run of consecutive days with >= 1 task, over all tasks ever.
  // Task dates are "YYYY-MM-DD" strings (local calendar days).
  function bestStreak(tasks) {
    const days = [...new Set(tasks.map(t => t.date))].sort();
    let best = 0, run = 0, expected = null;
    for (const day of days) {
      run = day === expected ? run + 1 : 1;
      best = Math.max(best, run);
      const [y, m, d] = day.split("-").map(Number);
      expected = ymd(new Date(y, m - 1, d + 1));
    }
    return best;
  }

  const api = { ymd, computeStreak, bestStreak };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.DevPulseStreak = api;
})(typeof window !== "undefined" ? window : this);
