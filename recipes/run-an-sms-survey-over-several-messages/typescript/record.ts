/**
 * The recorder verify.py drives. From an empty state file it begins a survey
 * with a captured fetch, runs the same seven inbound turns the Python verifier
 * runs, tries to begin a stopped number, drives the real server with a forged
 * and a signed request, and prints all of it as JSON on stdout.
 *
 * The expected values live in verify.py, which holds this output and the Python
 * surface's behaviour to the same one set.
 */
import { createHmac } from "node:crypto";
import { mkdtempSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

type Captured = { method: string; path: string; body: unknown };
const sent: Captured[] = [];

// the store is a temporary file: the recipe's own survey-state.json is never touched
process.env["SURVEY_STATE_PATH"] = join(mkdtempSync(join(tmpdir(), "survey-")), "state.json");

// HttpClient captures globalThis.fetch when the client is built, so it is
// replaced before index.ts is imported
globalThis.fetch = (async (input: unknown, init?: RequestInit) => {
  const url = new URL(String(input));
  sent.push({
    method: init?.method ?? "GET",
    path: url.pathname,
    body: typeof init?.body === "string" ? JSON.parse(init.body) : null,
  });
  return new Response(JSON.stringify({ id: "msg-1", status: "queued" }), {
    status: 200, headers: { "content-type": "application/json" },
  });
}) as typeof fetch;

const recipe = await import("./index.js");
const [customer = "", other = ""] = process.argv.slice(2);
const from = process.env["SMS_FROM"] ?? "";

const inbound = (sender: string, body: string) => ({ from: sender, to: from, body });
const textOf = (doc: { sections: { main: unknown[] } }) => {
  const [step] = doc.sections.main as { reply?: { body: string } }[];
  return step ? step.reply?.body ?? null : null;
};

await recipe.begin(customer);

const replies: (string | null)[] = [];
for (const [who, body] of [[customer, "great"], [customer, " 4 "], [customer, "Yes"],
                           [customer, "Friendly staff"], [customer, "hello?"],
                           [other, "4"]]) {
  replies.push(textOf(recipe.handleInbound(inbound(who, body))));
}
await recipe.begin(other);
replies.push(textOf(recipe.handleInbound(inbound(other, "STOP"))));

let refusedBegin = false;
try {
  await recipe.begin(other);
} catch (error) {
  refusedBegin = error instanceof recipe.OptedOut;
}

// the real server: a forged request is refused, a signed one is answered
const server = recipe.serve(0);
await new Promise((r) => server.once("listening", r));
const address = server.address();
const port = typeof address === "object" && address ? address.port : 0;
const raw = JSON.stringify({ message: inbound(other, "4") });
const forged = await fetchReal(`http://127.0.0.1:${port}/inbound`, raw, {});
const sig = createHmac("sha1", process.env["SIGNALWIRE_SIGNING_KEY"] ?? "")
  .update(process.env["INBOUND_URL"] + raw).digest("hex");
const signedRes = await fetchReal(`http://127.0.0.1:${port}/inbound`, raw,
                                  { "X-Signalwire-Signature": sig });
server.close();

const state = JSON.parse(
  (await import("node:fs")).readFileSync(process.env["SURVEY_STATE_PATH"] ?? "", "utf-8"));
console.log(JSON.stringify({
  sent: sent.filter((c) => c.path === "/api/messaging/messages").slice(0, 1),
  replies, state, refusedBegin,
  signature: { forged: forged.status, signed: signedRes.status },
}));

// the recorder above replaced fetch; the local server needs a real one
async function fetchReal(url: string, body: string, headers: Record<string, string>) {
  const { request } = await import("node:http");
  return new Promise<{ status: number }>((resolve, reject) => {
    const req = request(url, { method: "POST",
      headers: { "content-type": "application/json", ...headers } }, (res) => {
      res.resume();
      res.on("end", () => resolve({ status: res.statusCode ?? 0 }));
    });
    req.on("error", reject);
    req.end(body);
  });
}
