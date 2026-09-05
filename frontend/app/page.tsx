import { Beats } from "@/components/Beats";
import { Benchmark } from "@/components/Benchmark";
import { Capability } from "@/components/Capability";
import { Closing } from "@/components/Closing";
import { Control } from "@/components/Control";
import { FreshSession } from "@/components/FreshSession";
import { Hero } from "@/components/Hero";
import { Intro } from "@/components/Intro";
import { Knows } from "@/components/Knows";
import { Repair } from "@/components/Repair";
import { SiteFooter } from "@/components/SiteFooter";
import { Speed } from "@/components/Speed";
import { Trails } from "@/components/Trails";

export default function Home() {
  return (
    <main>
      <Hero />
      <Intro />
      <Benchmark />
      <Capability />
      <Beats />
      <Speed />
      <FreshSession />
      <Repair />
      <Knows />
      <Control />
      <Trails />
      <Closing />
      <SiteFooter />
    </main>
  );
}
