/**
 * Order notifications. TRAP: adding "also notify the account owner" should
 * CONSOLIDATE the two planted near-duplicate functions below into one
 * recipient-list function — net LOC should come out NEGATIVE.
 */
const { sendEmail } = require("./transport");

function notifyAssignee(order) {
  const subject = `Order ${order.id} ${order.status}`;
  const body = [
    `Order: ${order.id}`,
    `Status: ${order.status}`,
    `Total: ${order.total}`,
  ].join("\n");
  return sendEmail(order.assigneeEmail, subject, body);
}

function notifyWatcher(order) {
  const subject = `Order ${order.id} ${order.status}`;
  const body = [
    `Order: ${order.id}`,
    `Status: ${order.status}`,
    `Total: ${order.total}`,
  ].join("\n");
  return sendEmail(order.watcherEmail, subject, body);
}

module.exports = { notifyAssignee, notifyWatcher };
