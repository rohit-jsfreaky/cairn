import { Container } from "./Container";
import { Eyebrow } from "./Eyebrow";
import { Reveal } from "./Reveal";
import { SplitHeading } from "./SplitHeading";

/**
 * Everything memory holds BESIDES the route.
 *
 * A trail answers one task. These three answer the next one — the second task on a site is
 * cheaper than the first because the first paid for the map, the facts and the sign-in.
 * That is memory doing work for a job it was never recorded for, which is the part that is
 * hard to explain with a benchmark and easy to explain with three sentences.
 */
const THINGS = [
  {
    tool: "the map",
    lead: "It remembers every page it has stood on",
    body: "A new task on a known site does not start from a blank page. Cairn already has the pages it walked and the controls that were on them, so the second task on a site is cheaper than the first — and the tenth is cheaper still.",
    lines: [
      { path: "/invoices", detail: "14 controls · seen today" },
      { path: "/invoices/august", detail: "9 controls · seen today" },
      { path: "/settings/billing", detail: "11 controls · seen today" },
    ],
  },
  {
    tool: "what it learned",
    lead: "It remembers what survives a redesign",
    body: "Not steps — facts. This site sends a code to your phone. The real total is in the sidebar, not the header. That page only loads after you accept the cookie banner. When the site is rebuilt and the trail is gone, these are still true.",
    lines: [
      { path: "needs a login", detail: "signed in by hand, session kept" },
      { path: "sends a code to your phone", detail: "cannot be automated" },
      { path: "totals live in the sidebar", detail: "not the header" },
    ],
  },
  {
    tool: "who it signs in as",
    lead: "It can be several people at once",
    body: "A marketplace has a customer, a vendor and an admin, each with its own login. Cairn keeps a whole signed-in browser for each and switches between them instantly — no signing out, no test breaking the one after it. The memory of the site stays shared.",
    lines: [
      { path: "customer", detail: "signed in" },
      { path: "vendor", detail: "signed in" },
      { path: "admin", detail: "signed in · in use" },
    ],
  },
];

export function Knows() {
  return (
    <section className="hairline bg-white py-24 sm:py-32">
      <Reveal stagger={0.09}>
        <Container>
          <div className="mx-auto max-w-[1080px]">
            <Eyebrow>More than the route</Eyebrow>

            <SplitHeading className="mt-6 max-w-[19ch] font-display text-[clamp(28px,3.4vw,44px)] font-medium leading-[1.1] text-ink">
              The second task on a site is cheaper than the first.
            </SplitHeading>

            <p className="mt-6 max-w-[64ch] text-[19px] leading-[1.5] text-muted" data-reveal>
              A trail answers one task. Cairn keeps three other things, and they are what
              make the next task cheap — even a task it has never been asked before.
            </p>

            <div className="mt-16 grid gap-10 lg:grid-cols-3">
              {THINGS.map((thing) => (
                <div key={thing.tool} data-reveal>
                  <div className="well rounded-md bg-mist p-5">
                    <p className="font-mono text-[12.5px] text-moss">{thing.tool}</p>
                    <div className="mt-4 space-y-2.5">
                      {thing.lines.map((line) => (
                        <div
                          key={line.path}
                          className="surface flex items-baseline justify-between gap-3 rounded-xs bg-white px-3.5 py-2.5"
                        >
                          <span className="truncate font-mono text-[13px] text-ink">
                            {line.path}
                          </span>
                          <span className="shrink-0 text-[12px] text-faint">
                            {line.detail}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>

                  <p className="mt-6 text-[17px] font-medium leading-[1.35] text-ink">
                    {thing.lead}
                  </p>
                  <p className="mt-2.5 text-[15.5px] leading-[1.55] text-muted">
                    {thing.body}
                  </p>
                </div>
              ))}
            </div>

            <p
              className="mt-14 max-w-[68ch] text-[16px] leading-[1.55] text-faint"
              data-reveal
            >
              None of it is a recording. It is what Cairn knows about the site — and one
              command takes all of it away again.
            </p>

          </div>
        </Container>
      </Reveal>
    </section>
  );
}
