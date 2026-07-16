const sent = [];

function sendEmail(to, subject, body) {
  sent.push({ to, subject, body });
  return { queued: true, to };
}

module.exports = { sendEmail, sent };
