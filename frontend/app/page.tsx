import { Beats } from "@/components/Beats";
import { Capability } from "@/components/Capability";
import { Closing } from "@/components/Closing";
import { Control } from "@/components/Control";
import { FreshSession } from "@/components/FreshSession";
import { Hero } from "@/components/Hero";
import { Intro } from "@/components/Intro";
import { Repair } from "@/components/Repair";
import { SiteFooter } from "@/components/SiteFooter";
import { Speed } from "@/components/Speed";

export default function Home() {
  return (
    <main>
      <Hero />
      <Intro />
      <Capability />
      <Beats />
      <Speed />
      <FreshSession />
      <Repair />
      <Control />
      <Closing />
      <SiteFooter />
    </main>
  );
}
