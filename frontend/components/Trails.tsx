import { Container } from "./Container";
import { Eyebrow } from "./Eyebrow";
import { Reveal } from "./Reveal";
import { SplitHeading } from "./SplitHeading";
import { TDim, TOk, TWarn, TerminalCard } from "./TerminalCard";

const POINTS = [
  {
    lead: "Left for the next agent, free",
    body: "Two agents on one machine can hand a trail over for nothing. The second one inherits a working, self-checking route for a site it has never opened.",
  },
  {
    lead: "Or sold to one across the internet",
    body: "Different machines share nothing but a network, and nobody publishes for strangers unless it is worth their while. So a shop can ask for a cent, over HTTP, in USDC on Base.",
  },
  {
    lead: "What travels is the route, never your account",
    body: "Anything typed into a field is stripped before it leaves. A bought sign-in step arrives asking the buyer for their own credentials.",
  },
];

export function Trails() {
  return (
    <section
      id="trails"
      className="hairline scroll-mt-16 bg-white py-24 sm:py-32"
    >
      <Reveal>
        <Container className="grid items-center gap-14 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.05fr)] lg:gap-16">
          <div>
            <Eyebrow>Two agents, two machines</Eyebrow>

            <SplitHeading className="mt-6 max-w-[17ch] font-display text-[clamp(28px,3.2vw,42px)] font-medium leading-[1.1] text-ink">
              A trail one agent learned, another can buy.
            </SplitHeading>

            <p
              className="mt-6 max-w-[46ch] text-[18px] leading-[1.55] text-muted"
              data-reveal
            >
              A cairn is a pile of stones one hiker leaves for the next one.
              Learning a site costs real time and real calls — so the agent that
              walks it first can leave the route behind, and be paid by everyone
              who follows.
            </p>

            <div className="mt-12 space-y-8">
              {POINTS.map((point) => (
                <div key={point.lead} data-reveal>
                  <p className="text-[16px] font-medium text-ink">
                    {point.lead}
                  </p>
                  <p className="mt-2.5 max-w-[46ch] text-[15px] leading-[1.55] text-muted">
                    {point.body}
                  </p>
                </div>
              ))}
            </div>

            <p
              className="mt-10 max-w-[46ch] text-[15px] leading-[1.55] text-faint"
              data-reveal
            >
              Browsing a shop is free — you have to see what you are buying. The
              trail itself sits behind{" "}
              <a
                href="https://x402.org"
                className="underline decoration-ink/20 underline-offset-4 transition-colors hover:text-muted"
              >
                x402
              </a>
              , the HTTP standard for machine-to-machine payments. The payment
              goes on chain. The trail never does.
            </p>
          </div>

          <div data-reveal>
            <TerminalCard title="an agent buying a route it has never walked">
              <TDim>bob has never opened this site</TDim>
              <div className="h-4" />
              <TDim>GET /trails/posthog.com — free to look</TDim>
              <TOk>1 trail · $0.01 · 4 clean runs · first walked by alice</TOk>
              <div className="h-4" />
              <TDim>GET /trails/posthog.com/weekly-active</TDim>
              <TWarn>402 Payment Required</TWarn>
              <TOk>signed, settled on Base Sepolia</TOk>
              <TOk>200 — the trail, and a receipt</TOk>
              <div className="h-4" />
              <TDim>cairn run --site posthog.com</TDim>
              <TOk>1 call · 0 model calls · the answer</TOk>
              <p className="mt-4 text-faint">
                bob was taught nothing. He paid a cent for what alice already
                knew.
              </p>
            </TerminalCard>
          </div>
        </Container>
      </Reveal>
    </section>
  );
}
