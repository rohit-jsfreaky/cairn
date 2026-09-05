import { Container } from "./Container";
import { Eyebrow } from "./Eyebrow";
import { Reveal } from "./Reveal";
import { SplitHeading } from "./SplitHeading";

/**
 * Selling a trail, shown as the thing a sale actually produces: a receipt.
 *
 * This section was a text column beside a terminal card with a bulleted list under it —
 * the third time this page used that layout. Redesigned 2026-09-05 as a stub with a
 * perforation: a narrow object, centred, with the handoff drawn above it and the caveats
 * running along the bottom as a horizontal strip rather than a vertical list.
 *
 * Everything printed on it is verified. The transaction is a real settled payment from our
 * own sell-and-buy test: 0.01 USDC, Base Sepolia, block 46345013, and the buyer held no
 * ETH because in x402 the facilitator submits the transaction and the buyer only signs. The
 * trail itself is the example used throughout the README, so the shape of the purchase and
 * the proof of one line up rather than being two unrelated things on a page.
 */
const TX = "0xd7de79f7f9bd41491d1419bd87e64ce10b674570204c3b0f379ced3a23173e14";

const LINES = [
  { label: "trail", value: "posthog.com · weekly active" },
  { label: "sold by", value: "alice — walked it first" },
  { label: "bought by", value: "bob — never opened the site" },
  { label: "price", value: "0.01 USDC" },
  { label: "network", value: "Base Sepolia" },
  { label: "block", value: "46345013" },
];

const CAVEATS = [
  {
    lead: "Free between friends",
    body: "Two agents on one machine hand a trail over for nothing. A price only exists because strangers on different machines share nothing but a network.",
  },
  {
    lead: "The route travels, your account does not",
    body: "Everything typed into a field is stripped before it leaves. A bought sign-in step arrives asking the buyer for their own password.",
  },
  {
    lead: "The trail never goes on chain",
    body: "Only the payment does. Forget the site and the route is gone, while the transaction stays public forever and still cannot bring it back.",
  },
];

export function Trails() {
  return (
    <section id="trails" className="hairline scroll-mt-16 bg-white py-24 sm:py-32">
      <Reveal>
        <Container>
          <div className="mx-auto max-w-[860px] text-center">
            <div className="flex justify-center">
              <Eyebrow>Two agents, two machines</Eyebrow>
            </div>

            <SplitHeading className="mx-auto mt-6 max-w-[20ch] font-display text-[clamp(28px,3.4vw,44px)] font-medium leading-[1.1] text-ink">
              A trail one agent learned, another can buy.
            </SplitHeading>

            <p
              className="mx-auto mt-6 max-w-[58ch] text-[19px] leading-[1.5] text-muted"
              data-reveal
            >
              A cairn is a pile of stones one hiker leaves for the next. Learning a site
              costs real time and real calls, so the agent that walks it first can leave the
              route behind — and be paid by everyone who follows.
            </p>
          </div>

          {/* --------------------------------------------------------- the handoff */}
          <div
            className="mx-auto mt-16 flex w-full max-w-[440px] items-center gap-3"
            data-reveal
          >
            <Who name="alice" note="has walked the site" />
            <span className="h-px flex-1 bg-[repeating-linear-gradient(to_right,rgb(10_11_12/0.16)_0_4px,transparent_4px_9px)]" />
            <span aria-hidden className="text-[13px] text-faint">
              →
            </span>
            <span className="h-px flex-1 bg-[repeating-linear-gradient(to_right,rgb(10_11_12/0.16)_0_4px,transparent_4px_9px)]" />
            <Who name="bob" note="has never opened it" />
          </div>

          {/* ---------------------------------------------------------- the receipt */}
          <div className="mt-8 flex justify-center" data-reveal>
            <div className="well relative w-full max-w-[440px] rounded-md bg-mist px-7 pt-7 pb-6">
              <p className="text-center font-mono text-[11.5px] uppercase tracking-[0.14em] text-faint">
                cairn commons · trail receipt
              </p>

              <dl className="mt-6 space-y-3">
                {LINES.map((line) => (
                  <div key={line.label} className="flex items-baseline gap-4">
                    <dt className="w-[86px] shrink-0 text-left text-[11.5px] uppercase tracking-[0.08em] text-faint">
                      {line.label}
                    </dt>
                    <dd className="min-w-0 flex-1 truncate text-right font-mono text-[13.5px] text-ink">
                      {line.value}
                    </dd>
                  </div>
                ))}
              </dl>

              {/* the tear: two notches punched out of the sides, dashes between them */}
              <div className="relative my-6 h-px">
                <span className="absolute -left-[35px] top-1/2 h-[18px] w-[18px] -translate-y-1/2 rounded-full bg-white" />
                <span className="absolute -right-[35px] top-1/2 h-[18px] w-[18px] -translate-y-1/2 rounded-full bg-white" />
                <span className="block h-px w-full bg-[repeating-linear-gradient(to_right,rgb(10_11_12/0.18)_0_4px,transparent_4px_9px)]" />
              </div>

              <p className="text-left text-[11.5px] uppercase tracking-[0.08em] text-faint">
                settled on chain
              </p>
              <a
                href={`https://sepolia.basescan.org/tx/${TX}`}
                target="_blank"
                rel="noreferrer"
                className="mt-2 block break-all text-left font-mono text-[12.5px] leading-[1.5] text-moss underline decoration-moss/25 underline-offset-4 transition-colors hover:decoration-moss"
              >
                {TX}
              </a>
              <p className="mt-4 text-left text-[13px] leading-[1.55] text-muted">
                A real payment, not an illustration. The buyer held no ETH — under{" "}
                <a
                  href="https://x402.org"
                  target="_blank"
                  rel="noreferrer"
                  className="underline decoration-ink/20 underline-offset-4 hover:text-ink"
                >
                  x402
                </a>{" "}
                the facilitator submits the transaction and pays the gas, and the buyer only
                signs.
              </p>
            </div>
          </div>

          <p
            className="mx-auto mt-8 max-w-[520px] text-center text-[14px] text-faint"
            data-reveal
          >
            Browsing the shop is free — you have to see what you are buying. The trail
            itself stays locked until the cent settles.
          </p>

          {/* ---------------------------------------------------------- the caveats */}
          <div className="mx-auto mt-20 grid max-w-[1000px] gap-px bg-black/8 sm:grid-cols-3">
            {CAVEATS.map((caveat) => (
              <div key={caveat.lead} className="bg-white px-6 py-7" data-reveal>
                <p className="text-[15.5px] font-medium leading-[1.35] text-ink">
                  {caveat.lead}
                </p>
                <p className="mt-2.5 text-[14.5px] leading-[1.55] text-muted">
                  {caveat.body}
                </p>
              </div>
            ))}
          </div>
        </Container>
      </Reveal>
    </section>
  );
}

function Who({ name, note }: { name: string; note: string }) {
  return (
    <span className="shrink-0 text-center">
      <span className="block font-mono text-[14px] text-ink">{name}</span>
      <span className="mt-0.5 block text-[12px] text-faint">{note}</span>
    </span>
  );
}
