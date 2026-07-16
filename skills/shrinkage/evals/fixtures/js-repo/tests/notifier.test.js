const { notifyAssignee, notifyWatcher } = require("../src/notify/notifier");
const { sent } = require("../src/notify/transport");

const order = {
  id: "o-1",
  status: "shipped",
  total: 99,
  assigneeEmail: "a@x.com",
  watcherEmail: "w@x.com",
};

test("assignee gets order email", () => {
  notifyAssignee(order);
  const last = sent[sent.length - 1];
  expect(last.to).toBe("a@x.com");
  expect(last.subject).toContain("o-1");
});

test("watcher gets order email", () => {
  notifyWatcher(order);
  const last = sent[sent.length - 1];
  expect(last.to).toBe("w@x.com");
  expect(last.body).toContain("Total: 99");
});
